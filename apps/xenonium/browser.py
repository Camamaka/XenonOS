#!/usr/bin/env python3
"""Xenonium - XenonOS web browser (GTK3 + WebKitGTK 4.1)."""
import html
import os
import re
import sys
import time
from urllib.parse import parse_qs, quote, unquote, urlparse

def _vm_workarounds():
    """In virtual machines WebKit's DMABUF renderer can produce blank pages: disable it there."""
    try:
        with open("/sys/class/dmi/id/product_name") as f:
            name = f.read().lower()
        with open("/sys/class/dmi/id/sys_vendor") as f:
            name += " " + f.read().lower()
    except OSError:
        return
    if any(k in name for k in ("virtualbox", "vmware", "qemu", "kvm", "virtual machine", "innotek")):
        os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")


_vm_workarounds()

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango, WebKit2  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pages  # noqa: E402
import store  # noqa: E402
from extensions import VERSION, ExtensionManager  # noqa: E402

DEBUG = bool(os.environ.get("XENONIUM_DEBUG"))
APP_ID = "org.xenonos.Xenonium"
NEWTAB = "xenon://newtab"
SAFE_SCHEMES = {"http", "https", "file", "about", "data", "blob", "xenon", "view-source", "ws", "wss", "javascript"}

CSS = b"""
headerbar entry.xen-url { border-radius: 18px; min-height: 30px; padding-left: 10px; }
headerbar .xen-nav button { border-radius: 16px; }
notebook > header.top { padding: 0 4px; }
notebook tab { padding: 3px 6px; min-height: 22px; }
.xen-tab-close { padding: 0; min-height: 18px; min-width: 18px; border-radius: 9px; }
.xen-private headerbar { background: #2b1b3d; color: #f2e6ff; }
infobar.info { background: #0d2b3e; }
progressbar.xen-progress trough, progressbar.xen-progress progress { min-height: 3px; }
"""


def resolve_input(text, search_url):
    """Turns what was typed in the address bar into an address or a search."""
    t = text.strip()
    if not t:
        return NEWTAB
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", t) and not re.match(r"^[^/\s]+:\d+(/|$)", t):
        return t
    if " " not in t and (re.match(r"^(localhost|\d{1,3}(\.\d{1,3}){3})(:\d+)?(/.*)?$", t) or
                         re.match(r"^[^\s/]+\.[a-zA-Z]{2,}(:\d+)?(/.*)?$", t)):
        return ("http://" if t.startswith(("localhost", "127.", "192.168.", "10.")) else "https://") + t
    return search_url.replace("%s", quote(t))


def find_free_name(directory, name):
    base, ext = os.path.splitext(name)
    path, i = os.path.join(directory, name), 1
    while os.path.exists(path) or os.path.exists(path + ".part"):
        path = os.path.join(directory, f"{base} ({i}){ext}")
        i += 1
    return path


class Tab:
    def __init__(self, view):
        self.view = view
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.icon = Gtk.Image.new_from_icon_name("text-html-symbolic", Gtk.IconSize.MENU)
        self.label = Gtk.Label(label="New tab")
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_width_chars(14)
        self.label.set_max_width_chars(22)
        self.label.set_xalign(0)
        self.spinner = Gtk.Spinner()
        self.close = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        self.close.set_relief(Gtk.ReliefStyle.NONE)
        self.close.get_style_context().add_class("xen-tab-close")
        self.close.set_focus_on_click(False)
        self.box.pack_start(self.icon, False, False, 0)
        self.box.pack_start(self.spinner, False, False, 0)
        self.box.pack_start(self.label, True, True, 0)
        self.box.pack_start(self.close, False, False, 0)
        self.box.show_all()
        self.spinner.hide()


class BrowserWindow(Gtk.ApplicationWindow):
    def __init__(self, app, private=False):
        super().__init__(application=app)
        self.app = app
        self.private = private
        self.tabs = {}  # view -> Tab
        self.closed = []
        self.set_default_size(1280, 800)
        self.set_icon_name("xenonium")
        self.set_title("Xenonium" + (" - Private" if private else ""))
        if private:
            self.get_style_context().add_class("xen-private")
        self._build_ui()
        self._build_actions()
        self.connect("delete-event", self._on_delete)
        self.connect("key-press-event", self._on_key)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        self.set_titlebar(hb)
        self.headerbar = hb

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        nav.get_style_context().add_class("xen-nav")
        self.btn_back = self._tool("go-previous-symbolic", "Back (Alt+Left)", "win.back")
        self.btn_fwd = self._tool("go-next-symbolic", "Forward (Alt+Right)", "win.forward")
        self.btn_reload = self._tool("view-refresh-symbolic", "Reload (Ctrl+R)", "win.reload")
        self.btn_home = self._tool("go-home-symbolic", "Home page", "win.home")
        for b in (self.btn_back, self.btn_fwd, self.btn_reload, self.btn_home):
            nav.pack_start(b, False, False, 0)
        hb.pack_start(nav)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Search or enter address")
        self.entry.set_width_chars(60)
        self.entry.get_style_context().add_class("xen-url")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "system-search-symbolic")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "non-starred-symbolic")
        self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Bookmark this page (Ctrl+D)")
        self.entry.connect("activate", self._on_entry_activate)
        self.entry.connect("icon-press", self._on_entry_icon)
        self.entry.connect("changed", self._on_entry_changed)
        self.entry.connect("focus-in-event", lambda e, ev: (GLib.idle_add(e.select_region, 0, -1), False)[1])
        self._setup_completion()
        wrap = Gtk.Box()
        wrap.pack_start(self.entry, True, True, 0)
        hb.set_custom_title(wrap)
        wrap.set_hexpand(True)

        menu_btn = Gtk.MenuButton()
        menu_btn.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_btn.set_menu_model(self._build_menu())
        menu_btn.set_tooltip_text("Menu")
        hb.pack_end(menu_btn)
        self.ext_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        hb.pack_end(self.ext_box)
        self._build_ext_buttons()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        self.infobar = Gtk.InfoBar()
        self.infobar.set_message_type(Gtk.MessageType.INFO)
        self.infobar.set_show_close_button(True)
        self.info_label = Gtk.Label(xalign=0)
        self.infobar.get_content_area().add(self.info_label)
        self.infobar.add_button("Open", 1)
        self.infobar.add_button("Show in folder", 2)
        self.infobar.connect("response", self._on_infobar_response)
        self.infobar.set_no_show_all(True)
        self._info_path = None
        vbox.pack_start(self.infobar, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.get_style_context().add_class("xen-progress")
        self.progress.set_no_show_all(True)
        vbox.pack_start(self.progress, False, False, 0)

        self.searchbar = Gtk.SearchBar()
        sb = Gtk.Box(spacing=6)
        self.find_entry = Gtk.SearchEntry()
        self.find_entry.set_width_chars(30)
        self.find_status = Gtk.Label(label="")
        b_prev = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        b_next = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        for w in (self.find_entry, b_prev, b_next, self.find_status):
            sb.pack_start(w, False, False, 0)
        self.searchbar.add(sb)
        self.searchbar.connect_entry(self.find_entry)
        self.find_entry.connect("search-changed", self._on_find_changed)
        self.find_entry.connect("activate", lambda *_: self._find_step(True))
        self.find_entry.connect("previous-match", lambda *_: self._find_step(False))
        self.find_entry.connect("next-match", lambda *_: self._find_step(True))
        b_prev.connect("clicked", lambda *_: self._find_step(False))
        b_next.connect("clicked", lambda *_: self._find_step(True))
        self.searchbar.connect("notify::search-mode-enabled", self._on_search_mode)
        vbox.pack_start(self.searchbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.connect("switch-page", self._on_switch_page)
        self.notebook.connect("page-reordered", lambda *_: None)
        plus = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
        plus.set_relief(Gtk.ReliefStyle.NONE)
        plus.set_tooltip_text("New tab (Ctrl+T)")
        plus.connect("clicked", lambda *_: self.new_tab(NEWTAB, focus_url=True))
        plus.show()
        self.notebook.set_action_widget(plus, Gtk.PackType.END)
        vbox.pack_start(self.notebook, True, True, 0)
        vbox.show_all()
        hb.show_all()
        self.infobar.hide()
        self.progress.hide()
        self.searchbar.set_search_mode(False)

    def _tool(self, icon, tip, action):
        b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        b.set_tooltip_text(tip)
        b.set_action_name(action)
        return b

    def _build_menu(self):
        m = Gio.Menu()
        s1 = Gio.Menu()
        s1.append("New tab", "win.new-tab")
        s1.append("New window", "app.new-window")
        s1.append("New private window", "app.new-private")
        m.append_section(None, s1)
        s2 = Gio.Menu()
        s2.append("Bookmarks", "win.bookmarks-page")
        s2.append("History", "win.history")
        s2.append("Downloads", "win.downloads")
        s2.append("Extensions", "win.extensions-page")
        m.append_section(None, s2)
        s3 = Gio.Menu()
        s3.append("Zoom in", "win.zoom-in")
        s3.append("Zoom out", "win.zoom-out")
        s3.append("Reset zoom", "win.zoom-reset")
        s3.append("Full screen", "win.fullscreen")
        m.append_section(None, s3)
        s4 = Gio.Menu()
        s4.append("Find in page", "win.find")
        s4.append("Print", "win.print")
        s4.append("View source", "win.view-source")
        s4.append("Developer tools", "win.devtools")
        m.append_section(None, s4)
        s5 = Gio.Menu()
        s5.append("Settings", "win.settings")
        s5.append("About Xenonium", "win.about")
        s5.append("Quit", "app.quit")
        m.append_section(None, s5)
        return m

    def _build_ext_buttons(self):
        for c in self.ext_box.get_children():
            self.ext_box.remove(c)
        for ext in self.app.ext.extensions.values():
            if not ext.enabled or not ext.action:
                continue
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.set_tooltip_text(ext.action.get("title", ext.name))
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(ext.icon), 22, 22)
                b.set_image(Gtk.Image.new_from_pixbuf(pb))
            except (GLib.Error, TypeError):
                b.set_label(ext.name[:1])
            b.connect("clicked", lambda _b, e=ext: self.app.ext.run_command(
                self.current_view(), e.id, e.action.get("command", "toggle-panel")))
            self.ext_box.pack_start(b, False, False, 0)
        self.ext_box.show_all()

    def _setup_completion(self):
        self.comp_store = Gtk.ListStore(str, str)
        comp = Gtk.EntryCompletion()
        comp.set_model(self.comp_store)
        comp.set_text_column(0)
        comp.set_match_func(lambda *a: True)
        comp.set_inline_completion(False)
        comp.set_popup_single_match(True)
        r = Gtk.CellRendererText()
        r.set_property("foreground", "#7fa6b8")
        r.set_property("ellipsize", Pango.EllipsizeMode.END)
        comp.pack_end(r, False)
        comp.add_attribute(r, "text", 1)
        comp.connect("match-selected", self._on_completion_selected)
        self.entry.set_completion(comp)

    # ------------------------------------------------------------------ actions
    def _build_actions(self):
        def act(name, cb, accels=None):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_: cb())
            self.add_action(a)
            if accels:
                self.app.set_accels_for_action("win." + name, accels)

        act("new-tab", lambda: self.new_tab(NEWTAB, focus_url=True), ["<Primary>t"])
        act("close-tab", self.close_current_tab, ["<Primary>w"])
        act("reopen-tab", self.reopen_tab, ["<Primary><Shift>t"])
        act("focus-url", lambda: (self.entry.grab_focus()), ["<Primary>l", "F6", "<Alt>d"])
        act("reload", self._reload_or_stop, ["<Primary>r", "F5"])
        act("hard-reload", lambda: self._with_view(lambda v: v.reload_bypass_cache()), ["<Primary><Shift>r", "<Shift>F5"])
        act("back", lambda: self._with_view(lambda v: v.go_back()), ["<Alt>Left"])
        act("forward", lambda: self._with_view(lambda v: v.go_forward()), ["<Alt>Right"])
        act("home", lambda: self._with_view(lambda v: v.load_uri(self.app.settings.get("homepage") or NEWTAB)), ["<Alt>Home"])
        act("find", self._show_find, ["<Primary>f"])
        act("bookmark", self._toggle_bookmark, ["<Primary>d"])
        act("zoom-in", lambda: self._zoom(+0.1), ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"])
        act("zoom-out", lambda: self._zoom(-0.1), ["<Primary>minus", "<Primary>KP_Subtract"])
        act("zoom-reset", lambda: self._zoom(0), ["<Primary>0", "<Primary>KP_0"])
        act("next-tab", lambda: self._cycle(1), ["<Primary>Tab", "<Primary>Page_Down"])
        act("prev-tab", lambda: self._cycle(-1), ["<Primary><Shift>Tab", "<Primary>Page_Up"])
        act("fullscreen", self._toggle_fullscreen, ["F11"])
        act("devtools", lambda: self._with_view(lambda v: v.get_inspector().show()), ["F12", "<Primary><Shift>i"])
        act("view-source", self._view_source, ["<Primary>u"])
        act("print", lambda: self._with_view(lambda v: WebKit2.PrintOperation.new(v).run_dialog(self)), ["<Primary>p"])
        act("history", lambda: self.new_tab("xenon://history"), ["<Primary>h"])
        act("bookmarks-page", lambda: self.new_tab("xenon://bookmarks"), ["<Primary><Shift>o"])
        act("downloads", lambda: self.new_tab("xenon://downloads"), ["<Primary>j"])
        act("extensions-page", lambda: self.new_tab("xenon://extensions"))
        act("settings", self._show_settings)
        act("about", lambda: self.new_tab("xenon://about"))
        for i in range(1, 9):
            act(f"tab-{i}", lambda i=i: self.notebook.set_current_page(min(i, self.notebook.get_n_pages()) - 1), [f"<Alt>{i}"])
        act("tab-last", lambda: self.notebook.set_current_page(self.notebook.get_n_pages() - 1), ["<Alt>9"])

    def _on_key(self, widget, ev):
        if ev.keyval == Gdk.KEY_Escape:
            if self.searchbar.get_search_mode():
                self.searchbar.set_search_mode(False)
                return True
            v = self.current_view()
            if v and v.is_loading():
                v.stop_loading()
                return True
        return False

    # ------------------------------------------------------------------ webview
    def current_view(self):
        n = self.notebook.get_current_page()
        if n < 0:
            return None
        return self.notebook.get_nth_page(n)

    def _with_view(self, fn):
        v = self.current_view()
        if v:
            fn(v)

    def _make_view(self, related=None):
        ctx = self.app.private_ctx() if self.private else self.app.ctx
        kw = dict(web_context=ctx, user_content_manager=self.app.ext.ucm)
        if related is not None:
            kw["related_view"] = related
        view = WebKit2.WebView(**kw)
        s = view.get_settings()
        s.set_enable_developer_extras(True)
        s.set_enable_smooth_scrolling(True)
        s.set_enable_media_stream(True)
        s.set_enable_mediasource(True)
        s.set_enable_webgl(True)
        s.set_javascript_can_access_clipboard(True)
        s.set_enable_back_forward_navigation_gestures(True)
        s.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ON_DEMAND)
        s.set_user_agent_with_application_details("Xenonium", VERSION)
        s.set_media_playback_requires_user_gesture(False)
        view.connect("notify::title", self._on_title)
        view.connect("notify::uri", self._on_uri)
        view.connect("notify::estimated-load-progress", self._on_progress)
        view.connect("notify::favicon", self._on_favicon)
        view.connect("load-changed", self._on_load_changed)
        view.connect("load-failed", self._on_load_failed)
        view.connect("load-failed-with-tls-errors", self._on_tls_failed)
        view.connect("create", self._on_create)
        view.connect("decide-policy", self._on_decide_policy)
        view.connect("permission-request", self._on_permission)
        view.connect("authenticate", self._on_authenticate)
        view.connect("enter-fullscreen", self._on_enter_fs)
        view.connect("leave-fullscreen", self._on_leave_fs)
        view.connect("mouse-target-changed", self._on_hover)
        view.connect("web-process-terminated", self._on_web_process_terminated)
        if DEBUG:
            view.connect("notify::title", lambda v, _p: print("[xenonium] title:", v.get_title(), flush=True))
        fc = view.get_find_controller()
        fc.connect("counted-matches", self._on_counted)
        fc.connect("failed-to-find-text", lambda *_: self.find_status.set_text("Not found"))
        return view

    def new_tab(self, url=None, background=False, focus_url=False, view=None, related=None):
        view = view or self._make_view(related)
        tab = Tab(view)
        self.tabs[view] = tab
        tab.close.connect("clicked", lambda *_: self.close_tab(view))
        idx = self.notebook.append_page(view, tab.box)
        self.notebook.set_tab_reorderable(view, True)
        view.show()
        if not background:
            self.notebook.set_current_page(idx)
        if url:
            view.load_uri(url)
        if focus_url:
            self.entry.set_text("")
            self.entry.grab_focus()
        return view

    def close_tab(self, view):
        tab = self.tabs.pop(view, None)
        uri = view.get_uri()
        if uri and not uri.startswith("xenon://newtab"):
            self.closed.append(uri)
        n = self.notebook.page_num(view)
        if n >= 0:
            self.notebook.remove_page(n)
        view.try_close()
        if self.notebook.get_n_pages() == 0:
            self.close()

    def close_current_tab(self):
        v = self.current_view()
        if v:
            self.close_tab(v)

    def reopen_tab(self):
        if self.closed:
            self.new_tab(self.closed.pop())

    def _cycle(self, d):
        n = self.notebook.get_n_pages()
        if n:
            self.notebook.set_current_page((self.notebook.get_current_page() + d) % n)

    # ------------------------------------------------------------------ signals
    def _is_current(self, view):
        return view is self.current_view()

    def _on_title(self, view, _p):
        tab = self.tabs.get(view)
        if not tab:
            return
        title = view.get_title() or view.get_uri() or "New tab"
        if view.get_uri() == NEWTAB and not view.get_title():
            title = "New tab"
        tab.label.set_text(title)
        tab.label.set_tooltip_text(title)
        if not self.private and view.get_title():
            self.app.history.update_title(view.get_uri(), view.get_title())
        if self._is_current(view):
            self.headerbar.set_subtitle(None)
            self.set_title(f"{title} - Xenonium" + (" (Private)" if self.private else ""))

    def _on_uri(self, view, _p):
        if self._is_current(view):
            self._sync_entry(view)

    def _on_progress(self, view, _p):
        if self._is_current(view):
            self._sync_progress(view)

    def _on_favicon(self, view, _p):
        tab = self.tabs.get(view)
        if not tab:
            return
        try:
            surf = view.get_favicon()
            if surf is None:
                return
            pb = Gdk.pixbuf_get_from_surface(surf, 0, 0, surf.get_width(), surf.get_height())
            if pb:
                tab.icon.set_from_pixbuf(pb.scale_simple(16, 16, GdkPixbuf.InterpType.BILINEAR))
        except Exception:  # noqa: BLE001  (keep the default icon if the favicon cannot be fetched)
            pass

    def _on_load_changed(self, view, event):
        if DEBUG:
            print("[xenonium] load-changed", event.value_nick, view.get_uri(), flush=True)
        tab = self.tabs.get(view)
        if event == WebKit2.LoadEvent.STARTED:
            if tab:
                tab.spinner.show()
                tab.spinner.start()
                tab.icon.hide()
        elif event == WebKit2.LoadEvent.COMMITTED:
            if not self.private:
                self.app.history.add(view.get_uri(), view.get_title())
        elif event == WebKit2.LoadEvent.FINISHED:
            cmd = self.app.test_cmd
            if cmd and (view.get_uri() or "").startswith("http"):
                self.app.test_cmd = None
                ext_id, _, name = cmd.partition(":")
                GLib.timeout_add_seconds(3, lambda: (self.app.ext.run_command(view, ext_id, name), False)[1])
            if tab:
                tab.spinner.stop()
                tab.spinner.hide()
                tab.icon.show()
            if not self.private:
                self.app.history.update_title(view.get_uri(), view.get_title())
        if self._is_current(view):
            self._sync_nav(view)
            self._sync_progress(view)

    def _on_load_failed(self, view, event, uri, error):
        if error.matches(WebKit2.NetworkError.quark(), WebKit2.NetworkError.CANCELLED):
            return False
        msg = error.message
        view.load_alternate_html(
            pages.error("Page could not be loaded", msg, uri), uri, uri
        )
        return True

    def _on_tls_failed(self, view, uri, cert, errors):
        host = urlparse(uri).hostname or ""
        self.app.pending_certs[host] = cert
        extra = (f"<p><a href='xenon://tls-allow?host={quote(host)}&u={quote(uri, safe='')}'>"
                 "I understand the risk, continue anyway</a></p>")
        view.load_alternate_html(
            pages.error("Connection is not secure", "This site's certificate could not be verified. We recommend not entering any personal information.", uri, extra),
            uri, uri)
        return True

    def _on_create(self, view, nav_action):
        new = self._make_view(related=view)
        self.new_tab(view=new)
        return new

    def _on_decide_policy(self, view, decision, dtype):
        PD = WebKit2.PolicyDecisionType
        if dtype in (PD.NAVIGATION_ACTION, PD.NEW_WINDOW_ACTION):
            na = decision.get_navigation_action()
            uri = na.get_request().get_uri() or ""
            scheme = uri.split(":", 1)[0].lower()
            if scheme not in SAFE_SCHEMES:
                try:
                    Gtk.show_uri_on_window(self, uri, Gdk.CURRENT_TIME)
                except GLib.Error:
                    pass
                decision.ignore()
                return True
            if dtype == PD.NEW_WINDOW_ACTION:
                self.new_tab(uri)
                decision.ignore()
                return True
            if (na.get_navigation_type() == WebKit2.NavigationType.LINK_CLICKED
                    and (na.get_mouse_button() == 2 or (na.get_modifiers() & Gdk.ModifierType.CONTROL_MASK))):
                self.new_tab(uri, background=True)
                decision.ignore()
                return True
        elif dtype == PD.RESPONSE:
            if not decision.is_mime_type_supported():
                decision.download()
                return True
        return False

    def _on_permission(self, view, request):
        kinds = {
            WebKit2.GeolocationPermissionRequest: "access your location",
            WebKit2.NotificationPermissionRequest: "send notifications",
            WebKit2.UserMediaPermissionRequest: "access your camera / microphone",
        }
        for cls, what in kinds.items():
            if isinstance(request, cls):
                host = urlparse(view.get_uri() or "").hostname or "This site"
                d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                      buttons=Gtk.ButtonsType.NONE, text=f"{host} {what} wants to")
                d.add_button("Block", Gtk.ResponseType.REJECT)
                d.add_button("Allow", Gtk.ResponseType.ACCEPT)
                d.connect("response", lambda dlg, r, req=request: (
                    req.allow() if r == Gtk.ResponseType.ACCEPT else req.deny(), dlg.destroy()))
                d.show()
                return True
        return False

    def _on_authenticate(self, view, request):
        d = Gtk.Dialog(title="Authentication", transient_for=self, modal=True)
        d.add_button("Cancel", Gtk.ResponseType.CANCEL)
        d.add_button("Sign in", Gtk.ResponseType.OK)
        d.set_default_response(Gtk.ResponseType.OK)
        box = d.get_content_area()
        box.set_spacing(8)
        box.set_border_width(12)
        box.add(Gtk.Label(label=f"{request.get_host()} asks for a username and password", xalign=0))
        user, pw = Gtk.Entry(placeholder_text="Username"), Gtk.Entry(placeholder_text="Password")
        pw.set_visibility(False)
        pw.set_activates_default(True)
        box.add(user)
        box.add(pw)
        d.show_all()

        def done(dlg, r):
            if r == Gtk.ResponseType.OK:
                request.authenticate(WebKit2.Credential.new(user.get_text(), pw.get_text(), WebKit2.CredentialPersistence.NONE))
            else:
                request.cancel()
            dlg.destroy()
        d.connect("response", done)
        return True

    def _on_web_process_terminated(self, view, reason):
        if DEBUG:
            print("[xenonium] web process terminated:", reason.value_nick, flush=True)
        uri = view.get_uri() or NEWTAB
        view.load_alternate_html(
            pages.error("Page crashed", "This tab crashed unexpectedly."
                        if reason == WebKit2.WebProcessTerminationReason.CRASHED else "This tab used too much memory.", uri),
            uri, uri)

    def _on_enter_fs(self, view):
        self.fullscreen()
        self.notebook.set_show_tabs(False)
        self.headerbar.hide()
        return False

    def _on_leave_fs(self, view):
        self.unfullscreen()
        self.notebook.set_show_tabs(True)
        self.headerbar.show()
        return False

    def _on_hover(self, view, hit, mods):
        if hit.context_is_link():
            self.entry.set_tooltip_text(hit.get_link_uri())
        else:
            self.entry.set_tooltip_text(None)

    # ------------------------------------------------------------------ view sync
    def _on_switch_page(self, nb, page, num):
        GLib.idle_add(self._sync_all, page)

    def _sync_all(self, view):
        self._sync_entry(view)
        self._sync_nav(view)
        self._sync_progress(view)
        title = view.get_title() or "Xenonium"
        self.set_title(f"{title} - Xenonium" + (" (Private)" if self.private else ""))
        self.searchbar.set_search_mode(False)
        return False

    def _sync_entry(self, view):
        uri = view.get_uri() or ""
        if self.entry.has_focus() and self.entry.get_text() != "":
            pass
        shown = "" if uri in (NEWTAB, "about:blank", "") else uri
        self.entry.set_text(shown)
        if uri.startswith("https://"):
            icon = "channel-secure-symbolic"
        elif uri.startswith("http://"):
            icon = "channel-insecure-symbolic"
        else:
            icon = "system-search-symbolic"
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, icon)
        starred = bool(uri) and self.app.bookmarks.has(uri)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "starred-symbolic" if starred else "non-starred-symbolic")

    def _sync_nav(self, view):
        self.btn_back.set_sensitive(view.can_go_back())
        self.btn_fwd.set_sensitive(view.can_go_forward())
        icon = "process-stop-symbolic" if view.is_loading() else "view-refresh-symbolic"
        self.btn_reload.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))

    def _sync_progress(self, view):
        if view.is_loading():
            self.progress.show()
            self.progress.set_fraction(max(0.05, view.get_estimated_load_progress()))
        else:
            self.progress.hide()

    def _reload_or_stop(self):
        v = self.current_view()
        if v:
            v.stop_loading() if v.is_loading() else v.reload()

    # ------------------------------------------------------------------ address bar
    def _on_entry_activate(self, entry):
        url = resolve_input(entry.get_text(), self.app.settings.get("search_url"))
        v = self.current_view()
        if v is None:
            self.new_tab(url)
        else:
            v.load_uri(url)
            v.grab_focus()

    def _on_entry_changed(self, entry):
        if not entry.has_focus():
            return
        t = entry.get_text().strip()
        self.comp_store.clear()
        if len(t) < 2:
            return
        seen = set()
        for b in self.app.bookmarks.items:
            if t.lower() in (b["title"] + b["url"]).lower() and b["url"] not in seen:
                self.comp_store.append([b["url"], "★ " + b["title"]])
                seen.add(b["url"])
        for h in self.app.history.suggest(t):
            if h["url"] not in seen:
                self.comp_store.append([h["url"], h["title"] or ""])
                seen.add(h["url"])

    def _on_completion_selected(self, comp, model, it):
        url = model[it][0]
        self.entry.set_text(url)
        v = self.current_view()
        if v:
            v.load_uri(url)
        return True

    def _on_entry_icon(self, entry, pos, ev):
        if pos == Gtk.EntryIconPosition.SECONDARY:
            self._toggle_bookmark()

    def _toggle_bookmark(self):
        v = self.current_view()
        if not v or not v.get_uri() or v.get_uri().startswith("xenon://newtab"):
            return
        self.app.bookmarks.toggle(v.get_uri(), v.get_title())
        self._sync_entry(v)

    # ------------------------------------------------------------------ find / zoom / misc
    def _show_find(self):
        self.searchbar.set_search_mode(True)
        self.find_entry.grab_focus()

    def _on_search_mode(self, bar, _p):
        v = self.current_view()
        if v and not bar.get_search_mode():
            v.get_find_controller().search_finish()
            self.find_status.set_text("")

    def _on_find_changed(self, entry):
        v = self.current_view()
        if not v:
            return
        text = entry.get_text()
        fc = v.get_find_controller()
        if not text:
            fc.search_finish()
            self.find_status.set_text("")
            return
        fc.search(text, WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND, 1000)
        fc.count_matches(text, WebKit2.FindOptions.CASE_INSENSITIVE, 1000)

    def _find_step(self, forward):
        v = self.current_view()
        if v:
            fc = v.get_find_controller()
            fc.search_next() if forward else fc.search_previous()

    def _on_counted(self, fc, count):
        self.find_status.set_text(f"{count} results" if count else "Not found")

    def _zoom(self, delta):
        v = self.current_view()
        if not v:
            return
        z = 1.0 if delta == 0 else max(0.3, min(5.0, v.get_zoom_level() + delta))
        v.set_zoom_level(z)

    def _toggle_fullscreen(self):
        if self.get_window() and (self.get_window().get_state() & Gdk.WindowState.FULLSCREEN):
            self.unfullscreen()
        else:
            self.fullscreen()

    def _view_source(self):
        v = self.current_view()
        if v and v.get_uri() and not v.get_uri().startswith("view-source:"):
            self.new_tab("view-source:" + v.get_uri())

    def _show_settings(self):
        s = self.app.settings
        d = Gtk.Dialog(title="Xenonium settings", transient_for=self, modal=True)
        d.add_button("Close", Gtk.ResponseType.CLOSE)
        box = d.get_content_area()
        box.set_spacing(10)
        box.set_border_width(14)
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        box.add(grid)
        grid.attach(Gtk.Label(label="Home page", xalign=0), 0, 0, 1, 1)
        home = Gtk.Entry(text=s.get("homepage"), hexpand=True)
        home.connect("changed", lambda e: s.set("homepage", e.get_text().strip() or NEWTAB))
        grid.attach(home, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Search engine", xalign=0), 0, 1, 1, 1)
        engines = [("DuckDuckGo", "https://duckduckgo.com/?q=%s"), ("Google", "https://www.google.com/search?q=%s"),
                   ("Bing", "https://www.bing.com/search?q=%s"), ("Yandex", "https://yandex.com/search/?text=%s"),
                   ("Startpage", "https://www.startpage.com/do/search?q=%s")]
        combo = Gtk.ComboBoxText()
        cur = s.get("search_url")
        for i, (n, u) in enumerate(engines):
            combo.append(u, n)
        if not combo.set_active_id(cur):
            combo.append(cur, cur)
            combo.set_active_id(cur)
        combo.connect("changed", lambda c: s.set("search_url", c.get_active_id()))
        grid.attach(combo, 1, 1, 1, 1)
        sw = Gtk.Switch(active=bool(s.get("restore_session")), halign=Gtk.Align.START)
        sw.connect("notify::active", lambda w, _p: s.set("restore_session", w.get_active()))
        grid.attach(Gtk.Label(label="Restore previous tabs on startup", xalign=0), 0, 2, 1, 1)
        grid.attach(sw, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Download folder", xalign=0), 0, 3, 1, 1)
        fc = Gtk.FileChooserButton(title="Download folder", action=Gtk.FileChooserAction.SELECT_FOLDER)
        fc.set_filename(s.download_dir())
        fc.connect("file-set", lambda b: s.set("download_dir", b.get_filename()))
        grid.attach(fc, 1, 3, 1, 1)
        d.show_all()
        d.connect("response", lambda dlg, r: dlg.destroy())

    # ------------------------------------------------------------------ download bar
    def show_download(self, text, path=None):
        self.info_label.set_text(text)
        self._info_path = path
        self.infobar.show_all()
        for child in self.infobar.get_action_area().get_children():
            child.set_visible(bool(path))
        GLib.timeout_add_seconds(12, lambda: (self.infobar.hide(), False)[1])

    def _on_infobar_response(self, bar, resp):
        if resp in (1, 2) and self._info_path:
            target = self._info_path if resp == 1 else os.path.dirname(self._info_path)
            try:
                Gtk.show_uri_on_window(self, Gio.File.new_for_path(target).get_uri(), Gdk.CURRENT_TIME)
            except GLib.Error:
                pass
        bar.hide()

    def _on_delete(self, *_):
        self.app.save_session(exclude=self if len(self.app.windows_list()) > 1 else None)
        return False


class XenoniumApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.settings = store.Settings()
        self.bookmarks = store.Bookmarks()
        self.history = store.History()
        self.downloads = store.Downloads()
        self.pending_certs = {}
        self.test_cmd = None
        self.ctx = None
        self._private_ctx = None
        self.ext = None
        self._started = False

    # ---- lifecycle ----
    def do_startup(self):
        Gtk.Application.do_startup(self)
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._init_context()
        self.ext = ExtensionManager(self.settings, self._resolve_view)
        for name, cb, accel in (("new-window", lambda: self.open_window(), ["<Primary>n"]),
                                ("new-private", lambda: self.open_window(private=True), ["<Primary><Shift>n"]),
                                ("quit", self.quit_all, ["<Primary>q"])):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_, cb=cb: cb())
            self.add_action(a)
            self.set_accels_for_action("app." + name, accel)

    def _init_context(self):
        dm = WebKit2.WebsiteDataManager(base_data_directory=str(store.DATA / "web"),
                                        base_cache_directory=str(store.CACHE / "web"))
        self.ctx = WebKit2.WebContext.new_with_website_data_manager(dm)
        cm = self.ctx.get_cookie_manager()
        cm.set_persistent_storage(str(store.DATA / "cookies.sqlite"), WebKit2.CookiePersistentStorage.SQLITE)
        cm.set_accept_policy(WebKit2.CookieAcceptPolicy.NO_THIRD_PARTY)
        self.ctx.set_favicon_database_directory(str(store.CACHE / "favicons"))
        if not os.environ.get("XENONIUM_NO_SPELL"):
            # enable spell checking only if there is a valid locale and a dictionary is installed
            langs = []
            for name in GLib.get_language_names():
                code = name.split(".")[0].split("@")[0]
                if re.match(r"^[a-z]{2,3}_[A-Z]{2}$", code) and os.path.exists(f"/usr/share/hunspell/{code}.dic") and code not in langs:
                    langs.append(code)
            if os.path.exists("/usr/share/hunspell/en_US.dic") and "en_US" not in langs:
                langs.append("en_US")
            if langs:
                self.ctx.set_spell_checking_enabled(True)
                self.ctx.set_spell_checking_languages(langs)
        self._setup_context(self.ctx)

    def private_ctx(self):
        if self._private_ctx is None:
            self._private_ctx = WebKit2.WebContext.new_ephemeral()
            self._setup_context(self._private_ctx)
        return self._private_ctx

    def _setup_context(self, ctx):
        ctx.register_uri_scheme("xenon", self._on_xenon_request, None)
        sec = ctx.get_security_manager()
        sec.register_uri_scheme_as_secure("xenon")
        sec.register_uri_scheme_as_cors_enabled("xenon")
        ctx.connect("download-started", self._on_download_started)

    def do_command_line(self, cl):
        args = cl.get_arguments()[1:]
        private = "--private" in args or "--incognito" in args
        for a in args:  # dev/test: --ext-command=<extension>:<command> runs when the first http page has loaded
            if a.startswith("--ext-command="):
                self.test_cmd = a.split("=", 1)[1]
        urls = [a for a in args if not a.startswith("-")]
        norm = []
        for u in urls:
            if os.path.exists(u):
                u = Gio.File.new_for_path(os.path.abspath(u)).get_uri()
            norm.append(resolve_input(u, self.settings.get("search_url")))
        win = self.get_active_window()
        if not self._started:
            self._started = True
            win = BrowserWindow(self, private=private)
            first = norm or (self.session_urls() if not private else [])
            if not first:
                first = [self.settings.get("homepage") or NEWTAB]
            for i, u in enumerate(first):
                win.new_tab(u, background=i > 0)
            win.present()
            if first == [NEWTAB]:
                win.entry.grab_focus()
        else:
            if private or win is None:
                win = BrowserWindow(self, private=private)
            for u in norm or [NEWTAB]:
                win.new_tab(u)
            win.present()
        return 0

    def open_window(self, private=False):
        win = BrowserWindow(self, private=private)
        win.new_tab(NEWTAB, focus_url=True)
        win.present()

    def windows_list(self):
        return [w for w in self.get_windows() if isinstance(w, BrowserWindow)]

    def session_urls(self):
        return self.session_load() if self.settings.get("restore_session") else []

    def session_load(self):
        return store.Session().load()

    def save_session(self, exclude=None):
        urls = []
        for w in self.windows_list():
            if w is exclude or w.private:
                continue
            for i in range(w.notebook.get_n_pages()):
                u = w.notebook.get_nth_page(i).get_uri()
                if u and u != NEWTAB:
                    urls.append(u)
        store.Session().save(urls)

    def quit_all(self):
        self.save_session()
        for w in list(self.windows_list()):
            w.destroy()
        self.quit()

    def _resolve_view(self, href):
        """Find the tab that sent the extension message: first the tab with the same address, otherwise the active tab."""
        win = self.get_active_window()
        wins = ([win] if isinstance(win, BrowserWindow) else []) + [w for w in self.windows_list() if w is not win]
        for w in wins:
            for v in w.tabs:
                if v.get_uri() == href:
                    return v
        return win.current_view() if isinstance(win, BrowserWindow) else None

    # ---- xenon:// ----
    def _on_xenon_request(self, request, _data):
        uri = request.get_uri()
        if DEBUG:
            print("[xenonium] xenon request", uri, flush=True)
        u = urlparse(uri)
        q = parse_qs(u.query)
        page, path = u.netloc, u.path
        body, ctype = None, "text/html"
        if page == "newtab":
            body = pages.newtab(self.bookmarks.items)
        elif page == "bookmarks":
            if path == "/remove":
                self.bookmarks.remove(unquote(q.get("u", [""])[0]))
                body, ctype = "ok", "text/plain"
            else:
                body = pages.bookmarks(self.bookmarks.items)
        elif page == "history":
            if path == "/clear":
                self.history.clear()
                body, ctype = "ok", "text/plain"
            else:
                query = q.get("q", [""])[0]
                body = pages.history(self.history.recent(query=query), query)
        elif page == "downloads":
            body = pages.downloads(self.downloads.items)
        elif page == "extensions":
            if path == "/toggle":
                self.ext.toggle(q.get("id", [""])[0])
                for w in self.windows_list():
                    w._build_ext_buttons()
                body, ctype = "ok", "text/plain"
            else:
                body = pages.extensions(self.ext.list_info())
        elif page == "about":
            body = pages.about(VERSION)
        elif page == "tls-allow":
            host, target = q.get("host", [""])[0], unquote(q.get("u", [""])[0])
            cert = self.pending_certs.get(host)
            if cert:
                self.ctx.allow_tls_certificate_for_host(cert, host)
                if self._private_ctx:
                    self._private_ctx.allow_tls_certificate_for_host(cert, host)
            body = f"<meta http-equiv='refresh' content='0;url={html.escape(target, quote=True)}'>"
        else:
            body = pages.error("Page not found", "This xenon:// address is not defined.", uri)
        data = body.encode("utf-8")
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(data))
        request.finish(stream, len(data), ctype)

    # ---- downloads ----
    def _on_download_started(self, ctx, download):
        download.connect("decide-destination", self._on_decide_destination)
        download.connect("finished", self._on_download_finished)
        download.connect("failed", self._on_download_failed)

    def _on_decide_destination(self, download, suggested):
        name = os.path.basename(suggested or "") or "download"
        path = find_free_name(self.settings.download_dir(), name)
        download.set_destination(Gio.File.new_for_path(path).get_uri())
        download._xen_item = self.downloads.add(os.path.basename(path), path)
        download._xen_path = path
        return True

    def _on_download_finished(self, download):
        item = getattr(download, "_xen_item", None)
        if item:
            item["status"] = "completed"
        win = self.get_active_window()
        if isinstance(win, BrowserWindow) and item:
            win.show_download(f"Downloaded: {item['name']}", download._xen_path)

    def _on_download_failed(self, download, error):
        item = getattr(download, "_xen_item", None)
        if item:
            item["status"] = "failed"
        win = self.get_active_window()
        if isinstance(win, BrowserWindow):
            win.show_download(f"Download failed: {error.message}")


def main():
    GLib.set_prgname("xenonium")
    GLib.set_application_name("Xenonium")
    return XenoniumApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
