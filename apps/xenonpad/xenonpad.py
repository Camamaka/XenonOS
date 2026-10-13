#!/usr/bin/env python3
"""XenonPad - XenonOS text editor (GTK4 + libadwaita).

Tabs, find/replace, go to line, word wrap, zoom, auto-indent,
unsaved-changes protection, crash-recovery copies, opening by drag and drop.
"""
import os
import sys
import re
import json
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango  # noqa: E402

APP_ID = "org.xenonos.XenonPad"
VERSION = "1.0"
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "xenonpad")
RECOVER = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "xenonpad", "recovery")
os.makedirs(CONFIG, exist_ok=True)
os.makedirs(RECOVER, exist_ok=True)

CSS = b"""
textview.xenonpad { padding: 6px 4px; }
.xp-status { font-size: 0.85em; padding: 3px 12px; }
.xp-status label { opacity: 0.8; }
searchbar entry { min-width: 220px; }
.xp-found { background: alpha(#00e5ff, 0.35); }
"""


def load_prefs():
    try:
        with open(os.path.join(CONFIG, "prefs.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_prefs(p):
    try:
        with open(os.path.join(CONFIG, "prefs.json"), "w", encoding="utf-8") as f:
            json.dump(p, f)
    except OSError:
        pass


class Doc:
    """The document of a tab."""

    def __init__(self, page, view, buf, file=None):
        self.page, self.view, self.buf, self.file = page, view, buf, file
        self.modified = False
        self.encoding = "UTF-8"
        self.newline = "\n"
        self.recover_path = os.path.join(RECOVER, f"{int(time.time()*1000)}-{id(self) & 0xffff}.txt")

    @property
    def name(self):
        return os.path.basename(self.file.get_path()) if self.file and self.file.get_path() else "Untitled"


class XenonPadWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, default_width=980, default_height=680, title="XenonPad")
        self.app = app
        self.docs = {}  # AdwTabPage -> Doc
        self.prefs = app.prefs
        self._closing = False
        self.zoom = float(self.prefs.get("zoom", 1.0))
        self.wrap = bool(self.prefs.get("wrap", True))
        self._css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._apply_font()
        self._build()
        self._actions()
        GLib.timeout_add_seconds(20, self._write_recovery)
        self.connect("close-request", self._on_close_request)

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.toast = Adw.ToastOverlay()
        tv = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="XenonPad", subtitle="")
        header.set_title_widget(self.title_widget)
        btn_open = Gtk.Button(icon_name="document-open-symbolic", tooltip_text="Open (Ctrl+O)", action_name="win.open")
        btn_new = Gtk.Button(icon_name="tab-new-symbolic", tooltip_text="New tab (Ctrl+T)", action_name="win.new")
        header.pack_start(btn_open)
        header.pack_start(btn_new)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=self._menu(), tooltip_text="Menu")
        header.pack_end(menu_btn)
        btn_save = Gtk.Button(label="Save", tooltip_text="Save (Ctrl+S)", action_name="win.save")
        btn_save.add_css_class("suggested-action")
        header.pack_end(btn_save)
        btn_find = Gtk.ToggleButton(icon_name="edit-find-symbolic", tooltip_text="Find / replace (Ctrl+F)")
        header.pack_end(btn_find)
        tv.add_top_bar(header)

        self.tabview = Adw.TabView()
        self.tabview.connect("notify::selected-page", self._on_page_changed)
        self.tabview.connect("close-page", self._on_close_page)
        self.tabview.connect("page-detached", self._on_page_detached)
        tabbar = Adw.TabBar(view=self.tabview, autohide=False)
        tv.add_top_bar(tabbar)

        # find / replace bar
        self.searchbar = Gtk.SearchBar()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row1 = Gtk.Box(spacing=6)
        self.find_entry = Gtk.SearchEntry(placeholder_text="Find", hexpand=True)
        self.find_info = Gtk.Label(label="", xalign=0)
        self.find_info.add_css_class("dim-label")
        b_prev = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Previous (Shift+Enter)")
        b_next = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Next (Enter)")
        self.case_btn = Gtk.ToggleButton(label="Aa", tooltip_text="Match case")
        self.regex_btn = Gtk.ToggleButton(label=".*", tooltip_text="Regular expression")
        for w in (self.find_entry, b_prev, b_next, self.case_btn, self.regex_btn, self.find_info):
            row1.append(w)
        row2 = Gtk.Box(spacing=6)
        self.repl_entry = Gtk.Entry(placeholder_text="Replace", hexpand=True)
        b_rep = Gtk.Button(label="Replace")
        b_all = Gtk.Button(label="Replace all")
        for w in (self.repl_entry, b_rep, b_all):
            row2.append(w)
        box.append(row1)
        box.append(row2)
        self.searchbar.set_child(box)
        self.searchbar.connect_entry(self.find_entry)
        self.searchbar.set_key_capture_widget(self)
        btn_find.bind_property("active", self.searchbar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL)
        self.find_entry.connect("search-changed", lambda *_: self._find(True, from_start=True))
        self.find_entry.connect("activate", lambda *_: self._find(True))
        self.find_entry.connect("next-match", lambda *_: self._find(True))
        self.find_entry.connect("previous-match", lambda *_: self._find(False))
        b_next.connect("clicked", lambda *_: self._find(True))
        b_prev.connect("clicked", lambda *_: self._find(False))
        self.case_btn.connect("toggled", lambda *_: self._find(True, from_start=True))
        self.regex_btn.connect("toggled", lambda *_: self._find(True, from_start=True))
        b_rep.connect("clicked", lambda *_: self._replace_one())
        b_all.connect("clicked", lambda *_: self._replace_all())
        self.btn_find = btn_find

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self.searchbar)
        self.tabview.set_vexpand(True)
        content.append(self.tabview)

        # status bar
        status = Gtk.Box(spacing=18)
        status.add_css_class("xp-status")
        self.lbl_pos = Gtk.Label(label="Ln 1, Col 1")
        self.lbl_stats = Gtk.Label(label="0 characters")
        self.lbl_enc = Gtk.Label(label="UTF-8")
        self.lbl_zoom = Gtk.Label(label="100%")
        spacer = Gtk.Box(hexpand=True)
        for w in (self.lbl_pos, self.lbl_stats, spacer, self.lbl_enc, self.lbl_zoom):
            status.append(w)
        content.append(status)
        tv.set_content(content)
        self.toast.set_child(tv)
        self.set_content(self.toast)

        # drag and drop
        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.tabview.add_controller(drop)

    def _menu(self):
        m = Gio.Menu()
        s1 = Gio.Menu()
        s1.append("New window", "app.new-window")
        s1.append("Save as…", "win.save-as")
        s1.append("Reload", "win.reload")
        m.append_section(None, s1)
        s2 = Gio.Menu()
        s2.append("Go to line…", "win.goto")
        s2.append("Word wrap", "win.wrap")
        s2.append("Zoom in", "win.zoom-in")
        s2.append("Zoom out", "win.zoom-out")
        s2.append("Reset zoom", "win.zoom-reset")
        m.append_section(None, s2)
        s3 = Gio.Menu()
        s3.append("Sort selected lines", "win.sort")
        s3.append("Convert to uppercase", "win.upper")
        s3.append("Convert to lowercase", "win.lower")
        m.append_section(None, s3)
        s4 = Gio.Menu()
        s4.append("About XenonPad", "app.about")
        s4.append("Quit", "app.quit")
        m.append_section(None, s4)
        return m

    def _actions(self):
        def act(name, cb, accels=None, state=None):
            a = Gio.SimpleAction.new_stateful(name, None, GLib.Variant.new_boolean(state)) if state is not None else Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *args: cb(*args))
            self.add_action(a)
            if accels:
                self.app.set_accels_for_action("win." + name, accels)
            return a

        act("new", lambda *_: self.new_tab(), ["<Primary>t", "<Primary>n"])
        act("open", lambda *_: self.open_dialog(), ["<Primary>o"])
        act("save", lambda *_: self.save_current(), ["<Primary>s"])
        act("save-as", lambda *_: self.save_current(as_new=True), ["<Primary><Shift>s"])
        act("reload", lambda *_: self.reload_current())
        act("close", lambda *_: self.tabview.close_page(self.tabview.get_selected_page()) if self.tabview.get_selected_page() else None, ["<Primary>w"])
        act("find", lambda *_: self._toggle_find(), ["<Primary>f", "<Primary>h"])
        act("goto", lambda *_: self.goto_dialog(), ["<Primary>l", "<Primary>g"])
        self.wrap_action = act("wrap", self._toggle_wrap, ["<Alt>z"], state=self.wrap)
        act("zoom-in", lambda *_: self._set_zoom(self.zoom + 0.1), ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"])
        act("zoom-out", lambda *_: self._set_zoom(self.zoom - 0.1), ["<Primary>minus", "<Primary>KP_Subtract"])
        act("zoom-reset", lambda *_: self._set_zoom(1.0), ["<Primary>0"])
        act("sort", lambda *_: self._transform_lines(lambda ls: sorted(ls, key=str.lower)))
        act("upper", lambda *_: self._transform_sel(str.upper), ["<Primary><Shift>u"])
        act("lower", lambda *_: self._transform_sel(str.lower), ["<Primary><Shift>l"])
        act("next-tab", lambda *_: self.tabview.select_next_page(), ["<Primary>Page_Down", "<Primary>Tab"])
        act("prev-tab", lambda *_: self.tabview.select_previous_page(), ["<Primary>Page_Up", "<Primary><Shift>Tab"])
        act("escape", lambda *_: self.searchbar.set_search_mode(False), ["Escape"])

    # ------------------------------------------------------------------ font / zoom
    def _apply_font(self):
        size = max(6, round(11 * self.zoom, 1))
        self._css.load_from_data(
            (CSS.decode() + f"\ntextview.xenonpad {{ font-family: 'Ubuntu Mono','DejaVu Sans Mono',monospace; font-size: {size}pt; }}").encode()
        )

    def _set_zoom(self, z):
        self.zoom = max(0.5, min(4.0, round(z, 2)))
        self.prefs["zoom"] = self.zoom
        save_prefs(self.prefs)
        self._apply_font()
        self.lbl_zoom.set_text(f"{round(self.zoom*100)}%")

    def _toggle_wrap(self, action, _param):
        self.wrap = not self.wrap
        action.set_state(GLib.Variant.new_boolean(self.wrap))
        self.prefs["wrap"] = self.wrap
        save_prefs(self.prefs)
        for d in self.docs.values():
            d.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR if self.wrap else Gtk.WrapMode.NONE)

    # ------------------------------------------------------------------ tabs / documents
    def current(self):
        page = self.tabview.get_selected_page()
        return self.docs.get(page) if page else None

    def new_tab(self, file=None, text="", select=True):
        buf = Gtk.TextBuffer()
        view = Gtk.TextView(buffer=buf, monospace=True, top_margin=6, bottom_margin=6, left_margin=10, right_margin=10)
        view.add_css_class("xenonpad")
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR if self.wrap else Gtk.WrapMode.NONE)
        view.set_accepts_tab(True)
        view.set_pixels_above_lines(1)
        sw = Gtk.ScrolledWindow(child=view, hexpand=True, vexpand=True)
        page = self.tabview.append(sw)
        doc = Doc(page, view, buf, file)
        self.docs[page] = doc
        tag = buf.create_tag("xp-found", background="#00e5ff55")
        buf.begin_irreversible_action()
        buf.set_text(text)
        buf.end_irreversible_action()
        buf.set_modified(False)
        buf.place_cursor(buf.get_start_iter())
        buf.connect("changed", lambda *_: self._on_changed(doc))
        buf.connect("notify::cursor-position", lambda *_: self._update_status())
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key, doc)
        view.add_controller(key)
        self._refresh_title(doc)
        if select:
            self.tabview.set_selected_page(page)
            view.grab_focus()
        return doc

    def _on_changed(self, doc):
        if not doc.modified:
            doc.modified = True
            self._refresh_title(doc)
        self._update_status()

    def _refresh_title(self, doc):
        doc.page.set_title(("• " if doc.modified else "") + doc.name)
        doc.page.set_tooltip(doc.file.get_path() if doc.file and doc.file.get_path() else "Unsaved document")
        doc.page.set_needs_attention(False)
        if doc.page == self.tabview.get_selected_page():
            self._update_window_title()

    def _update_window_title(self):
        d = self.current()
        if d:
            self.title_widget.set_title(("• " if d.modified else "") + d.name)
            self.title_widget.set_subtitle(os.path.dirname(d.file.get_path()) if d.file and d.file.get_path() else "")
            self.lbl_enc.set_text(d.encoding)

    def _on_page_changed(self, *_):
        self._update_window_title()
        self._update_status()

    def _update_status(self):
        d = self.current()
        if not d:
            return
        it = d.buf.get_iter_at_mark(d.buf.get_insert())
        self.lbl_pos.set_text(f"Ln {it.get_line() + 1}, Col {it.get_line_offset() + 1}")
        n = d.buf.get_char_count()
        text = d.buf.get_text(d.buf.get_start_iter(), d.buf.get_end_iter(), False)
        words = len(text.split())
        self.lbl_stats.set_text(f"{words} words, {n} characters")

    def _on_key(self, ctrl, keyval, keycode, state, doc):
        buf = doc.buf
        # auto-indent
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not (state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK)):
            it = buf.get_iter_at_mark(buf.get_insert())
            ls = it.copy()
            ls.set_line_offset(0)
            line = buf.get_text(ls, it, False)
            indent = re.match(r"[ \t]*", line).group(0)
            if indent or line.rstrip().endswith((":", "{", "(", "[")):
                extra = "    " if line.rstrip().endswith((":", "{", "(", "[")) else ""
                buf.begin_user_action()
                buf.insert_at_cursor("\n" + indent + extra)
                buf.end_user_action()
                doc.view.scroll_mark_onscreen(buf.get_insert())
                return True
        # Shift+Tab: decrease indent; Tab on a multi-line selection: increase indent
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            if buf.get_has_selection():
                s, e = buf.get_selection_bounds()
                if s.get_line() != e.get_line():
                    self._indent_lines(doc, s.get_line(), e.get_line() - (1 if e.starts_line() else 0), keyval == Gdk.KEY_ISO_Left_Tab)
                    return True
            elif keyval == Gdk.KEY_ISO_Left_Tab:
                it = buf.get_iter_at_mark(buf.get_insert())
                self._indent_lines(doc, it.get_line(), it.get_line(), True)
                return True
        return False

    def _indent_lines(self, doc, l1, l2, dedent):
        buf = doc.buf
        buf.begin_user_action()
        for ln in range(l1, l2 + 1):
            ok, it = buf.get_iter_at_line(ln)
            if not ok:
                continue
            if dedent:
                end = it.copy()
                n = 0
                while n < 4 and end.get_char() == " ":
                    end.forward_char()
                    n += 1
                if n == 0 and end.get_char() == "\t":
                    end.forward_char()
                buf.delete(it, end)
            else:
                buf.insert(it, "    ")
        buf.end_user_action()

    # ------------------------------------------------------------------ file operations
    def open_dialog(self):
        dlg = Gtk.FileDialog(title="Open file")
        dlg.open_multiple(self, None, self._on_open_done)

    def _on_open_done(self, dlg, res):
        try:
            files = dlg.open_multiple_finish(res)
        except GLib.Error:
            return
        for i in range(files.get_n_items()):
            self.open_file(files.get_item(i))

    def open_file(self, gfile):
        for d in self.docs.values():
            if d.file and d.file.equal(gfile):
                self.tabview.set_selected_page(d.page)
                return d
        try:
            ok, data, _etag = gfile.load_contents(None)
        except GLib.Error as e:
            self._toast(f"Could not open: {e.message}")
            return None
        text, enc = self._decode(data)
        nl = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n")
        cur = self.current()
        reuse = cur if cur and not cur.file and not cur.modified and cur.buf.get_char_count() == 0 else None
        if reuse:
            reuse.file = gfile
            reuse.buf.begin_irreversible_action()
            reuse.buf.set_text(text)
            reuse.buf.end_irreversible_action()
            doc = reuse
        else:
            doc = self.new_tab(gfile, text)
        doc.file, doc.encoding, doc.newline = gfile, enc, nl
        doc.modified = False
        doc.buf.set_modified(False)
        doc.buf.place_cursor(doc.buf.get_start_iter())
        self._refresh_title(doc)
        return doc

    @staticmethod
    def _decode(data):
        raw = bytes(data)
        if raw.startswith(b"\xef\xbb\xbf"):
            return raw[3:].decode("utf-8", "replace"), "UTF-8 (BOM)"
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                return raw.decode(enc), enc.upper().replace("CP1254", "Windows-1254").replace("LATIN-1", "ISO-8859-1")
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", "replace"), "UTF-8"

    def save_current(self, as_new=False, then=None):
        d = self.current()
        if not d:
            return
        self.save_doc(d, as_new, then)

    def save_doc(self, d, as_new=False, then=None, on_cancel=None):
        if d.file is None or as_new:
            dlg = Gtk.FileDialog(title="Save as", initial_name=d.name if d.file else "untitled.txt")
            dlg.save(self, None, lambda dg, res: self._on_save_done(dg, res, d, then, on_cancel))
        else:
            self._write(d, d.file, then, on_cancel)

    def _on_save_done(self, dlg, res, d, then, on_cancel=None):
        try:
            f = dlg.save_finish(res)
        except GLib.Error:
            if on_cancel:
                on_cancel()
            return
        self._write(d, f, then, on_cancel)

    def _write(self, d, gfile, then=None, on_cancel=None):
        text = d.buf.get_text(d.buf.get_start_iter(), d.buf.get_end_iter(), False)
        if d.newline == "\r\n":
            text = text.replace("\n", "\r\n")
        try:
            gfile.replace_contents(text.encode("utf-8"), None, True, Gio.FileCreateFlags.NONE, None)
        except GLib.Error as e:
            self._toast(f"Could not save: {e.message}")
            if on_cancel:
                on_cancel()
            return
        d.file, d.modified, d.encoding = gfile, False, "UTF-8"
        d.buf.set_modified(False)
        self._refresh_title(d)
        self._remove_recovery(d)
        self._toast(f"Saved: {d.name}")
        if then:
            then()

    def reload_current(self):
        d = self.current()
        if not d or not d.file:
            return
        try:
            _ok, data, _e = d.file.load_contents(None)
        except GLib.Error as e:
            self._toast(f"Could not load: {e.message}")
            return
        text, enc = self._decode(data)
        d.buf.set_text(text.replace("\r\n", "\n"))
        d.modified = False
        d.buf.set_modified(False)
        self._refresh_title(d)

    def _toast(self, text):
        self.toast.add_toast(Adw.Toast(title=text, timeout=3))

    def _on_drop(self, target, value, x, y):
        for f in value.get_files():
            self.open_file(f)
        return True

    # ------------------------------------------------------------------ close protection
    def _on_close_page(self, tabview, page):
        d = self.docs.get(page)
        if d and d.modified and (d.buf.get_char_count() > 0 or d.file):
            self._ask_save(d, lambda: tabview.close_page_finish(page, True),
                           lambda: tabview.close_page_finish(page, False))
            return True
        tabview.close_page_finish(page, True)
        return True

    def _on_page_detached(self, tabview, page, _pos):
        d = self.docs.pop(page, None)
        if d:
            self._remove_recovery(d)
        if tabview.get_n_pages() == 0 and not self._closing:
            GLib.idle_add(self._after_last_closed)

    def _after_last_closed(self):
        if self.tabview.get_n_pages() == 0:
            self.new_tab()
        return False

    def _ask_save(self, d, proceed, cancel=None):
        dlg = Adw.AlertDialog(heading=f"Save changes to '{d.name}'?", body="If you don't save, your changes will be lost.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("discard", "Don't save")
        dlg.add_response("save", "Save")
        dlg.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("save")
        dlg.set_close_response("cancel")

        def resp(dg, r):
            if r == "save":
                self.save_doc(d, then=proceed, on_cancel=cancel)
            elif r == "discard":
                d.modified = False
                proceed()
            elif cancel:
                cancel()
        dlg.connect("response", resp)
        dlg.present(self)

    def _on_close_request(self, *_):
        unsaved = [d for d in self.docs.values() if d.modified and (d.buf.get_char_count() > 0 or d.file)]
        if not unsaved:
            self._closing = True
            self._cleanup()
            return False
        d = unsaved[0]
        self.tabview.set_selected_page(d.page)
        self._ask_save(d, lambda: (setattr(d, "modified", False), self.close()))
        return True

    def _cleanup(self):
        for d in self.docs.values():
            self._remove_recovery(d)

    # ------------------------------------------------------------------ recovery copies
    def _write_recovery(self):
        for d in self.docs.values():
            if d.modified and d.buf.get_char_count() > 0:
                try:
                    text = d.buf.get_text(d.buf.get_start_iter(), d.buf.get_end_iter(), False)
                    with open(d.recover_path, "w", encoding="utf-8") as f:
                        f.write(text)
                except OSError:
                    pass
        return True

    def _remove_recovery(self, d):
        try:
            os.remove(d.recover_path)
        except OSError:
            pass

    # ------------------------------------------------------------------ find / replace
    def _toggle_find(self):
        on = not self.searchbar.get_search_mode()
        self.searchbar.set_search_mode(on)
        if on:
            d = self.current()
            if d and d.buf.get_has_selection():
                s, e = d.buf.get_selection_bounds()
                t = d.buf.get_text(s, e, False)
                if "\n" not in t:
                    self.find_entry.set_text(t)
            self.find_entry.grab_focus()
            self.find_entry.select_region(0, -1)

    def _pattern(self):
        text = self.find_entry.get_text()
        if not text:
            return None
        flags = 0 if self.case_btn.get_active() else re.IGNORECASE
        try:
            return re.compile(text if self.regex_btn.get_active() else re.escape(text), flags | re.MULTILINE)
        except re.error:
            return None

    def _find(self, forward, from_start=False):
        d = self.current()
        if not d:
            return
        pat = self._pattern()
        buf = d.buf
        buf.remove_tag_by_name("xp-found", buf.get_start_iter(), buf.get_end_iter())
        if not pat:
            self.find_info.set_text("")
            return
        full = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        matches = list(pat.finditer(full))
        self.find_info.set_text(f"{len(matches)} results" if matches else "Not found")
        if not matches:
            return
        for m in matches[:2000]:
            buf.apply_tag_by_name("xp-found", buf.get_iter_at_offset(m.start()), buf.get_iter_at_offset(m.end()))
        sel_s, sel_e = (buf.get_selection_bounds() or (buf.get_iter_at_mark(buf.get_insert()),) * 2)
        pos = 0 if from_start else (sel_e.get_offset() if forward else sel_s.get_offset())
        if from_start:
            pos = buf.get_iter_at_mark(buf.get_insert()).get_offset()
            pos = min(pos, sel_s.get_offset())
        if forward:
            pick = next((m for m in matches if m.start() >= pos), matches[0])
        else:
            pick = next((m for m in reversed(matches) if m.end() <= pos), matches[-1])
        s, e = buf.get_iter_at_offset(pick.start()), buf.get_iter_at_offset(pick.end())
        buf.select_range(s, e)
        d.view.scroll_to_iter(s, 0.2, False, 0, 0)

    def _replace_one(self):
        d = self.current()
        pat = self._pattern()
        if not d or not pat or not d.buf.get_has_selection():
            self._find(True)
            return
        s, e = d.buf.get_selection_bounds()
        sel = d.buf.get_text(s, e, False)
        m = pat.fullmatch(sel)
        if m:
            repl = m.expand(self.repl_entry.get_text()) if self.regex_btn.get_active() else self.repl_entry.get_text()
            d.buf.begin_user_action()
            d.buf.delete(s, e)
            d.buf.insert_at_cursor(repl)
            d.buf.end_user_action()
        self._find(True)

    def _replace_all(self):
        d = self.current()
        pat = self._pattern()
        if not d or not pat:
            return
        buf = d.buf
        full = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        rep = self.repl_entry.get_text()
        new, n = pat.subn(rep if self.regex_btn.get_active() else rep.replace("\\", "\\\\"), full)
        if n:
            buf.begin_user_action()
            buf.set_text(new)
            buf.end_user_action()
        self.find_info.set_text(f"{n} replacements made")

    # ------------------------------------------------------------------ go to line / transformations
    def goto_dialog(self):
        d = self.current()
        if not d:
            return
        dlg = Adw.AlertDialog(heading="Go to line", body=f"1 - {d.buf.get_line_count()}")
        entry = Gtk.Entry(placeholder_text="Line number", input_purpose=Gtk.InputPurpose.DIGITS, activates_default=True)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("go", "Go")
        dlg.set_default_response("go")
        dlg.set_response_appearance("go", Adw.ResponseAppearance.SUGGESTED)

        def resp(dg, r):
            if r == "go" and entry.get_text().strip().isdigit():
                ln = max(1, min(int(entry.get_text()), d.buf.get_line_count())) - 1
                ok, it = d.buf.get_iter_at_line(ln)
                d.buf.place_cursor(it)
                d.view.scroll_to_iter(it, 0.2, True, 0, 0.5)
                d.view.grab_focus()
        dlg.connect("response", resp)
        dlg.present(self)
        entry.grab_focus()

    def _transform_sel(self, fn):
        d = self.current()
        if not d or not d.buf.get_has_selection():
            return
        s, e = d.buf.get_selection_bounds()
        t = fn(d.buf.get_text(s, e, False))
        d.buf.begin_user_action()
        d.buf.delete(s, e)
        d.buf.insert_at_cursor(t)
        d.buf.end_user_action()

    def _transform_lines(self, fn):
        d = self.current()
        if not d or not d.buf.get_has_selection():
            self._toast("Select a few lines first")
            return
        s, e = d.buf.get_selection_bounds()
        s.set_line_offset(0)
        if not e.starts_line():
            e.forward_to_line_end()
        lines = d.buf.get_text(s, e, False).split("\n")
        out = "\n".join(fn(lines))
        d.buf.begin_user_action()
        d.buf.delete(s, e)
        d.buf.insert_at_cursor(out)
        d.buf.end_user_action()


class XenonPadApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.prefs = load_prefs()

    def do_startup(self):
        Adw.Application.do_startup(self)
        for name, cb, accel in (("new-window", lambda *_: self._new_window(), ["<Primary><Shift>n"]),
                                ("about", lambda *_: self._about(), None),
                                ("quit", lambda *_: self._quit(), ["<Primary>q"])):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accel:
                self.set_accels_for_action("app." + name, accel)

    def _new_window(self):
        w = XenonPadWindow(self)
        w.new_tab()
        w.present()
        return w

    def do_activate(self):
        win = self.get_active_window() or self._new_window()
        if not win.docs:
            win.new_tab()
        win.present()

    def do_open(self, files, n_files, hint):
        win = self.get_active_window() or XenonPadWindow(self)
        for f in files:
            win.open_file(f)
        if not win.docs:
            win.new_tab()
        win.present()

    def _about(self):
        dlg = Adw.AboutDialog(application_name="XenonPad", application_icon="xenonpad", version=VERSION,
                              developer_name="XenonOS", comments="XenonOS text editor",
                              license_type=Gtk.License.GPL_3_0)
        dlg.present(self.get_active_window())

    def _quit(self):
        for w in list(self.get_windows()):
            w.close()


def main():
    GLib.set_prgname("xenonpad")
    GLib.set_application_name("XenonPad")
    return XenonPadApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
