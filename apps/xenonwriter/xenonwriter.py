#!/usr/bin/env python3
"""XenonWriter - XenonOS kelime islemcisi (GTK3 + WebKitGTK 4.1, gercek zengin metin duzenleme).

Bicimlendirme (kalin/italik/altini cizili/ustu cizili, yazi tipi + boyut, renk, vurgu, hizalama, listeler,
basliklar, alinti, kod), baglanti, resim, tablo, yatay cizgi, bul, yakinlastirma, A4 sayfa gorunumu,
HTML / metin olarak kaydetme, PDF'e aktarma, yazdirma.
"""
import json
import os
import re
import sys
import html as htmllib


def _vm_workarounds():
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
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2  # noqa: E402

APP_ID = "org.xenonos.XenonWriter"
VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = bool(os.environ.get("XENONWRITER_DEBUG"))

CSS = b"""
.xw-toolbar { padding: 4px 8px; border-bottom: 1px solid alpha(currentColor, 0.15); }
.xw-toolbar button, .xw-toolbar togglebutton { min-height: 28px; min-width: 28px; padding: 2px 6px; }
.xw-status { padding: 3px 14px; font-size: 0.85em; border-top: 1px solid alpha(currentColor, 0.15); }
.xw-sep { margin: 4px 6px; }
"""

STYLES = [("p", "Normal"), ("h1", "Heading 1"), ("h2", "Heading 2"), ("h3", "Heading 3"),
          ("blockquote", "Quote"), ("pre", "Code")]
SIZES = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36", "48", "72"]
DEFAULT_FONTS = ["Liberation Serif", "Liberation Sans", "DejaVu Serif", "DejaVu Sans", "Ubuntu", "Noto Serif", "Noto Sans",
                 "Ubuntu Mono", "DejaVu Sans Mono"]

DOC_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="generator" content="XenonWriter {ver}">
<style>
body{{font-family:'Liberation Serif','DejaVu Serif',serif;font-size:12pt;line-height:1.5;color:#111;max-width:794px;margin:0 auto;padding:40px}}
p{{margin:0 0 .6em}} h1{{font-size:24pt}} h2{{font-size:18pt}} h3{{font-size:14pt}}
blockquote{{margin:.8em 0;padding:.2em 1em;border-left:4px solid #00a6c0;color:#445;background:#f3fafc}}
pre{{background:#f2f4f6;border-radius:6px;padding:10px 14px;font:11pt monospace;white-space:pre-wrap}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #9aa7b0;padding:6px 8px}} img{{max-width:100%}}
</style></head><body>
<div id="xenonwriter-page">{body}</div>
</body></html>
"""


def plain_to_html(text):
    paras = re.split(r"\n{2,}", text.replace("\r\n", "\n").strip("\n"))
    out = []
    for p in paras:
        lines = [htmllib.escape(l) for l in p.split("\n")]
        out.append("<p>" + "<br>".join(lines) + "</p>")
    return "".join(out) or "<p><br></p>"


def extract_body(doc):
    """Acilan .html dosyasindan duzenlenecek govdeyi al."""
    m = re.search(r'<div id="xenonwriter-page">(.*)</div>\s*</body>', doc, re.S | re.I)
    if m:
        return m.group(1)
    m = re.search(r"<body[^>]*>(.*)</body>", doc, re.S | re.I)
    body = m.group(1) if m else doc
    return re.sub(r"<script.*?</script>", "", body, flags=re.S | re.I)


class WriterWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.file = None
        self.modified = False
        self.ready = False
        self.pending_html = None
        self._updating = False
        self.set_default_size(1100, 820)
        self.set_icon_name("xenonwriter")
        self._build()
        self._actions()
        self._refresh_title()
        self.connect("delete-event", self._on_delete)

    # ------------------------------------------------------------------ arayuz
    def _tb(self, icon, tip, cb=None, toggle=False, label=None):
        b = Gtk.ToggleButton() if toggle else Gtk.Button()
        if label:
            b.set_label(label)
        else:
            b.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        b.set_tooltip_text(tip)
        b.set_focus_on_click(False)
        if cb:
            b.connect("toggled" if toggle else "clicked", cb)
        return b

    def _build(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        self.set_titlebar(hb)
        self.hb = hb
        left = Gtk.Box(spacing=4)
        left.pack_start(self._tb("document-new-symbolic", "New (Ctrl+N)", lambda *_: self.app.new_window()), False, False, 0)
        left.pack_start(self._tb("document-open-symbolic", "Open (Ctrl+O)", lambda *_: self.open_dialog()), False, False, 0)
        hb.pack_start(left)
        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        save.set_tooltip_text("Save (Ctrl+S)")
        save.connect("clicked", lambda *_: self.save())
        hb.pack_end(save)
        mb = Gtk.MenuButton()
        mb.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        mb.set_menu_model(self._menu())
        hb.pack_end(mb)
        hb.pack_end(self._tb("edit-find-symbolic", "Find (Ctrl+F)", lambda *_: self._show_find()))

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # ---- arac cubugu (iki satir) ----
        tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tb.get_style_context().add_class("xw-toolbar")
        r1 = Gtk.Box(spacing=4)
        r2 = Gtk.Box(spacing=4)
        tb.pack_start(r1, False, False, 0)
        tb.pack_start(r2, False, False, 0)
        vbox.pack_start(tb, False, False, 0)

        r1.pack_start(self._tb("edit-undo-symbolic", "Undo (Ctrl+Z)", lambda *_: self.cmd("undo")), False, False, 0)
        r1.pack_start(self._tb("edit-redo-symbolic", "Redo (Ctrl+Y)", lambda *_: self.cmd("redo")), False, False, 0)
        r1.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)

        self.style_combo = Gtk.ComboBoxText()
        for tag, name in STYLES:
            self.style_combo.append(tag, name)
        self.style_combo.set_active_id("p")
        self.style_combo.set_tooltip_text("Paragraph style")
        self.style_combo.connect("changed", self._on_style)
        r1.pack_start(self.style_combo, False, False, 0)

        self.font_combo = Gtk.ComboBoxText.new_with_entry()
        fams = sorted({f.get_name() for f in self.get_pango_context().list_families()}, key=str.lower)
        for f in DEFAULT_FONTS + [x for x in fams if x not in DEFAULT_FONTS]:
            self.font_combo.append_text(f)
        self.font_combo.get_child().set_width_chars(16)
        self.font_combo.set_tooltip_text("Font")
        self.font_combo.get_child().connect("activate", self._on_font_entry)
        self.font_combo.connect("changed", self._on_font_changed)
        r1.pack_start(self.font_combo, False, False, 0)

        self.size_combo = Gtk.ComboBoxText.new_with_entry()
        for s in SIZES:
            self.size_combo.append_text(s)
        self.size_combo.get_child().set_width_chars(4)
        self.size_combo.set_tooltip_text("Font size (pt)")
        self.size_combo.get_child().connect("activate", self._on_size_entry)
        self.size_combo.connect("changed", self._on_size_changed)
        r1.pack_start(self.size_combo, False, False, 0)

        r1.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)
        self.t_bold = self._tb("format-text-bold-symbolic", "Bold (Ctrl+B)", lambda b: self._toggle("bold", b), True)
        self.t_italic = self._tb("format-text-italic-symbolic", "Italic (Ctrl+I)", lambda b: self._toggle("italic", b), True)
        self.t_under = self._tb("format-text-underline-symbolic", "Underline (Ctrl+U)", lambda b: self._toggle("underline", b), True)
        self.t_strike = self._tb("format-text-strikethrough-symbolic", "Strikethrough", lambda b: self._toggle("strikeThrough", b), True)
        for w in (self.t_bold, self.t_italic, self.t_under, self.t_strike):
            r1.pack_start(w, False, False, 0)
        r1.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)

        self.color_btn = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(0.07, 0.07, 0.07, 1))
        self.color_btn.set_title("Text color")
        self.color_btn.set_tooltip_text("Text color")
        self.color_btn.connect("color-set", lambda b: self.js(f"xw.color({json.dumps(self._hex(b))})"))
        self.hl_btn = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(1, 0.95, 0.3, 1))
        self.hl_btn.set_title("Highlight color")
        self.hl_btn.set_tooltip_text("Highlight color")
        self.hl_btn.connect("color-set", lambda b: self.js(f"xw.highlight({json.dumps(self._hex(b))})"))
        r1.pack_start(self.color_btn, False, False, 0)
        r1.pack_start(self.hl_btn, False, False, 0)

        self.t_left = self._tb("format-justify-left-symbolic", "Align left", lambda b: self._align("justifyLeft", b), True)
        self.t_center = self._tb("format-justify-center-symbolic", "Center", lambda b: self._align("justifyCenter", b), True)
        self.t_right = self._tb("format-justify-right-symbolic", "Align right", lambda b: self._align("justifyRight", b), True)
        self.t_full = self._tb("format-justify-fill-symbolic", "Justify", lambda b: self._align("justifyFull", b), True)
        for w in (self.t_left, self.t_center, self.t_right, self.t_full):
            r2.pack_start(w, False, False, 0)
        r2.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)
        self.t_ul = self._tb(None, "Bulleted list", lambda b: self._toggle("insertUnorderedList", b), True, label="• ≡")
        self.t_ol = self._tb(None, "Numbered list", lambda b: self._toggle("insertOrderedList", b), True, label="1. ≡")
        r2.pack_start(self.t_ul, False, False, 0)
        r2.pack_start(self.t_ol, False, False, 0)
        r2.pack_start(self._tb("format-indent-less-symbolic", "Decrease indent", lambda *_: self.cmd("outdent")), False, False, 0)
        r2.pack_start(self._tb("format-indent-more-symbolic", "Increase indent", lambda *_: self.cmd("indent")), False, False, 0)
        r2.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)
        r2.pack_start(self._tb("insert-link-symbolic", "Insert link (Ctrl+K)", lambda *_: self.link_dialog()), False, False, 0)
        r2.pack_start(self._tb("insert-image-symbolic", "Insert image", lambda *_: self.image_dialog()), False, False, 0)
        r2.pack_start(self._tb("view-grid-symbolic", "Insert table", lambda *_: self.table_dialog()), False, False, 0)
        r2.pack_start(self._tb("list-remove-symbolic", "Horizontal line", lambda *_: self.js("xw.hr()")), False, False, 0)
        r2.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 6)
        r2.pack_start(self._tb("edit-clear-all-symbolic", "Clear formatting", lambda *_: self.js("xw.clear()")), False, False, 0)

        # ---- bul cubugu ----
        self.searchbar = Gtk.SearchBar()
        sb = Gtk.Box(spacing=6)
        self.find_entry = Gtk.SearchEntry()
        self.find_entry.set_width_chars(28)
        self.find_info = Gtk.Label(label="")
        b_prev = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        b_next = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        for w in (self.find_entry, b_prev, b_next, self.find_info):
            sb.pack_start(w, False, False, 0)
        self.searchbar.add(sb)
        self.searchbar.connect_entry(self.find_entry)
        self.find_entry.connect("search-changed", self._on_find_changed)
        self.find_entry.connect("activate", lambda *_: self._find_step(True))
        b_next.connect("clicked", lambda *_: self._find_step(True))
        b_prev.connect("clicked", lambda *_: self._find_step(False))
        vbox.pack_start(self.searchbar, False, False, 0)

        # ---- web gorunumu ----
        ucm = WebKit2.UserContentManager()
        ucm.register_script_message_handler("xw")
        ucm.connect("script-message-received::xw", self._on_message)
        self.view = WebKit2.WebView(user_content_manager=ucm)
        s = self.view.get_settings()
        s.set_enable_developer_extras(DEBUG)
        s.set_enable_javascript(True)
        s.set_enable_smooth_scrolling(True)
        s.set_enable_back_forward_navigation_gestures(False)
        self.view.connect("decide-policy", self._on_policy)
        self.view.connect("context-menu", lambda *_: False)
        self.view.connect("web-process-terminated", self._on_crash)
        with open(os.path.join(HERE, "editor.html"), "r", encoding="utf-8") as f:
            self.view.load_html(f.read(), "file:///xenonwriter/")
        vbox.pack_start(self.view, True, True, 0)

        # ---- durum cubugu ----
        st = Gtk.Box(spacing=18)
        st.get_style_context().add_class("xw-status")
        self.lbl_words = Gtk.Label(label="0 words", xalign=0)
        self.lbl_state = Gtk.Label(label="", xalign=0)
        zoom_out = self._tb("zoom-out-symbolic", "Zoom out", lambda *_: self._zoom(-0.1))
        zoom_in = self._tb("zoom-in-symbolic", "Zoom in", lambda *_: self._zoom(+0.1))
        self.lbl_zoom = Gtk.Label(label="%100")
        st.pack_start(self.lbl_words, False, False, 0)
        st.pack_start(self.lbl_state, True, True, 0)
        for w in (zoom_out, self.lbl_zoom, zoom_in):
            st.pack_end(w, False, False, 0)
        vbox.pack_start(st, False, False, 0)
        vbox.show_all()
        self.hb.show_all()
        self.searchbar.set_search_mode(False)

    def _menu(self):
        m = Gio.Menu()
        s1 = Gio.Menu()
        s1.append("New window", "app.new-window")
        s1.append("Save as…", "win.save-as")
        s1.append("Export as PDF…", "win.export-pdf")
        s1.append("Print…", "win.print")
        m.append_section(None, s1)
        s2 = Gio.Menu()
        s2.append("Select all", "win.select-all")
        s2.append("Zoom in", "win.zoom-in")
        s2.append("Zoom out", "win.zoom-out")
        s2.append("Reset zoom", "win.zoom-reset")
        m.append_section(None, s2)
        s3 = Gio.Menu()
        s3.append("About XenonWriter", "app.about")
        s3.append("Quit", "app.quit")
        m.append_section(None, s3)
        return m

    def _actions(self):
        def act(name, cb, accels=None):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_: cb())
            self.add_action(a)
            if accels:
                self.app.set_accels_for_action("win." + name, accels)

        act("save", self.save, ["<Primary>s"])
        act("save-as", lambda: self.save(as_new=True), ["<Primary><Shift>s"])
        act("open", self.open_dialog, ["<Primary>o"])
        act("new", self.app.new_window, ["<Primary>n"])
        act("export-pdf", self.export_pdf, ["<Primary>e"])
        act("print", self.print_doc, ["<Primary>p"])
        act("find", self._show_find, ["<Primary>f"])
        act("link", self.link_dialog, ["<Primary>k"])
        act("select-all", lambda: self.cmd("selectAll"))
        act("zoom-in", lambda: self._zoom(+0.1), ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"])
        act("zoom-out", lambda: self._zoom(-0.1), ["<Primary>minus", "<Primary>KP_Subtract"])
        act("zoom-reset", lambda: self._zoom(0), ["<Primary>0"])
        act("close", self.close, ["<Primary>w"])

    # ------------------------------------------------------------------ JS koprusu
    def js(self, code, cb=None):
        if cb is None:
            self.view.evaluate_javascript(code, -1, None, None, None, None)
        else:
            def done(view, res):
                try:
                    cb(view.evaluate_javascript_finish(res).to_string())
                except GLib.Error as e:
                    if DEBUG:
                        print("js error:", e.message)
            self.view.evaluate_javascript(code, -1, None, None, None, done)

    def cmd(self, name, value=None):
        self.js(f"xw.cmd({json.dumps(name)}{',' + json.dumps(value) if value is not None else ''})")

    def _on_message(self, ucm, value):
        jsv = value.get_js_value() if hasattr(value, "get_js_value") else value
        try:
            m = json.loads(jsv.to_string())
        except (ValueError, AttributeError):
            return
        t = m.get("t")
        if t == "ready":
            self.ready = True
            if self.pending_html is not None:
                self.set_html(self.pending_html)
                self.pending_html = None
            self.js("xw.focus()")
        elif t == "mod":
            if not self.modified:
                self.modified = True
                self._refresh_title()
        elif t == "stats":
            self.lbl_words.set_text(f"{m['words']} words, {m['chars']} characters")
        elif t == "state":
            self._apply_state(m)

    def _apply_state(self, m):
        self._updating = True
        for btn, key in ((self.t_bold, "bold"), (self.t_italic, "italic"), (self.t_under, "underline"),
                         (self.t_strike, "strike"), (self.t_ul, "ul"), (self.t_ol, "ol"),
                         (self.t_left, "left"), (self.t_center, "center"), (self.t_right, "right"), (self.t_full, "full")):
            btn.set_active(bool(m.get(key)))
        block = m.get("block", "p")
        self.style_combo.set_active_id(block if block in dict(STYLES) else "p")
        font = m.get("font", "")
        if font:
            self.font_combo.get_child().set_text(font)
        size = m.get("size")
        if size:
            self.size_combo.get_child().set_text(str(int(size)) if float(size).is_integer() else str(size))
        self._updating = False

    def set_html(self, body):
        if not self.ready:
            self.pending_html = body
            return
        self.js(f"xw.setHTML({json.dumps(body)})")

    # ------------------------------------------------------------------ arac cubugu olaylari
    @staticmethod
    def _hex(btn):
        c = btn.get_rgba()
        return "#%02x%02x%02x" % (round(c.red * 255), round(c.green * 255), round(c.blue * 255))

    def _toggle(self, cmd, btn):
        if self._updating:
            return
        self.cmd(cmd)

    def _align(self, cmd, btn):
        if self._updating or not btn.get_active():
            return
        self.cmd(cmd)

    def _on_style(self, combo):
        if self._updating:
            return
        tag = combo.get_active_id()
        if tag:
            self.js(f"xw.block({json.dumps(tag)})")

    def _on_font_changed(self, combo):
        if self._updating or combo.get_active() < 0:
            return
        self.js(f"xw.fontName({json.dumps(combo.get_active_text())})")

    def _on_font_entry(self, entry):
        if not self._updating and entry.get_text().strip():
            self.js(f"xw.fontName({json.dumps(entry.get_text().strip())})")

    def _on_size_changed(self, combo):
        if self._updating or combo.get_active() < 0:
            return
        self.js(f"xw.fontSize({json.dumps(float(combo.get_active_text()))})")

    def _on_size_entry(self, entry):
        if self._updating:
            return
        try:
            v = float(entry.get_text().replace(",", "."))
        except ValueError:
            return
        if 1 <= v <= 400:
            self.js(f"xw.fontSize({v})")

    # ------------------------------------------------------------------ iletisim kutulari
    def link_dialog(self):
        def got(sel):
            d = Gtk.Dialog(title="Link", transient_for=self, modal=True)
            d.add_button("Remove link", 2)
            d.add_button("Cancel", Gtk.ResponseType.CANCEL)
            d.add_button("OK", Gtk.ResponseType.OK)
            d.set_default_response(Gtk.ResponseType.OK)
            box = d.get_content_area()
            box.set_border_width(14)
            box.set_spacing(8)
            box.add(Gtk.Label(label=f"Selected text: {sel[:40]}" if sel else "Select some text first", xalign=0))
            e = Gtk.Entry(text="https://", activates_default=True)
            box.add(e)
            d.show_all()
            r = d.run()
            url = e.get_text().strip()
            d.destroy()
            if r == Gtk.ResponseType.OK and url:
                self.js(f"xw.link({json.dumps(url)})")
            elif r == 2:
                self.js("xw.link('')")
        self.js("xw.selectedText()", got)

    def image_dialog(self):
        dlg = Gtk.FileChooserNative.new("Insert image", self, Gtk.FileChooserAction.OPEN, "Add", "Cancel")
        flt = Gtk.FileFilter()
        flt.set_name("Images")
        for p in ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg", "*.bmp"):
            flt.add_pattern(p)
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            path = dlg.get_filename()
            try:
                import base64
                import mimetypes
                mt = mimetypes.guess_type(path)[0] or "image/png"
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                self.js(f"xw.image({json.dumps(f'data:{mt};base64,{data}')})")
            except OSError as e:
                self._error(f"Could not insert image: {e}")

    def table_dialog(self):
        d = Gtk.Dialog(title="Insert table", transient_for=self, modal=True)
        d.add_button("Cancel", Gtk.ResponseType.CANCEL)
        d.add_button("Add", Gtk.ResponseType.OK)
        g = Gtk.Grid(column_spacing=10, row_spacing=8, margin=14)
        d.get_content_area().add(g)
        rows = Gtk.SpinButton.new_with_range(1, 50, 1)
        cols = Gtk.SpinButton.new_with_range(1, 12, 1)
        rows.set_value(3)
        cols.set_value(3)
        g.attach(Gtk.Label(label="Rows", xalign=0), 0, 0, 1, 1)
        g.attach(rows, 1, 0, 1, 1)
        g.attach(Gtk.Label(label="Columns", xalign=0), 0, 1, 1, 1)
        g.attach(cols, 1, 1, 1, 1)
        d.show_all()
        if d.run() == Gtk.ResponseType.OK:
            self.js(f"xw.table({rows.get_value_as_int()},{cols.get_value_as_int()})")
        d.destroy()

    def _error(self, text):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.CLOSE, text=text)
        d.run()
        d.destroy()

    # ------------------------------------------------------------------ bul / yakinlastir
    def _show_find(self):
        self.searchbar.set_search_mode(True)
        self.find_entry.grab_focus()

    def _on_find_changed(self, entry):
        fc = self.view.get_find_controller()
        t = entry.get_text()
        if not t:
            fc.search_finish()
            self.find_info.set_text("")
            return
        fc.search(t, WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND, 1000)
        fc.connect("counted-matches", lambda f, n: self.find_info.set_text(f"{n} results" if n else "Not found"))
        fc.count_matches(t, WebKit2.FindOptions.CASE_INSENSITIVE, 1000)

    def _find_step(self, forward):
        fc = self.view.get_find_controller()
        fc.search_next() if forward else fc.search_previous()

    def _zoom(self, delta):
        z = 1.0 if delta == 0 else max(0.4, min(3.0, round(self.view.get_zoom_level() + delta, 2)))
        self.view.set_zoom_level(z)
        self.lbl_zoom.set_text(f"%{round(z * 100)}")

    # ------------------------------------------------------------------ dosya islemleri
    @property
    def name(self):
        return os.path.basename(self.file) if self.file else "Untitled document"

    def _refresh_title(self):
        self.hb.set_title(("• " if self.modified else "") + self.name)
        self.hb.set_subtitle(os.path.dirname(self.file) if self.file else "XenonWriter")
        self.set_title(("• " if self.modified else "") + self.name + " - XenonWriter")

    def open_dialog(self):
        if self.modified and not self._confirm_discard():
            return
        dlg = Gtk.FileChooserNative.new("Open document", self, Gtk.FileChooserAction.OPEN, "Open", "Cancel")
        f1 = Gtk.FileFilter()
        f1.set_name("Documents (html, txt, md)")
        for p in ("*.html", "*.htm", "*.txt", "*.md"):
            f1.add_pattern(p)
        dlg.add_filter(f1)
        f2 = Gtk.FileFilter()
        f2.set_name("All files")
        f2.add_pattern("*")
        dlg.add_filter(f2)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            self.open_path(dlg.get_filename())

    def open_path(self, path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            self._error(f"Could not open: {e}")
            return
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        body = extract_body(text) if path.lower().endswith((".html", ".htm")) else plain_to_html(text)
        self.file = path
        self.set_html(body)
        self.modified = False
        self._refresh_title()

    def _confirm_discard(self):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.NONE, text=f"Save changes to '{self.name}'?")
        d.format_secondary_text("If you don't save, your changes will be lost.")
        d.add_button("Cancel", Gtk.ResponseType.CANCEL)
        d.add_button("Don't save", Gtk.ResponseType.REJECT)
        d.add_button("Save", Gtk.ResponseType.ACCEPT)
        r = d.run()
        d.destroy()
        if r == Gtk.ResponseType.ACCEPT:
            self.save()
            return not self.modified
        return r == Gtk.ResponseType.REJECT

    def save(self, as_new=False, after=None):
        path = self.file
        if path is None or as_new:
            dlg = Gtk.FileChooserNative.new("Save", self, Gtk.FileChooserAction.SAVE, "Save", "Cancel")
            dlg.set_do_overwrite_confirmation(True)
            dlg.set_current_name((os.path.splitext(self.name)[0] if self.file else "document") + ".html")
            f1 = Gtk.FileFilter()
            f1.set_name("Web page (*.html)")
            f1.add_pattern("*.html")
            f2 = Gtk.FileFilter()
            f2.set_name("Plain text (*.txt)")
            f2.add_pattern("*.txt")
            dlg.add_filter(f1)
            dlg.add_filter(f2)
            if dlg.run() != Gtk.ResponseType.ACCEPT:
                return
            path = dlg.get_filename()
            if not os.path.splitext(path)[1]:
                path += ".txt" if dlg.get_filter() is f2 else ".html"

        self.save_to(path, after)

    def save_to(self, path, after=None):
        def write(content):
            try:
                if path.lower().endswith(".txt"):
                    data = content
                else:
                    data = DOC_TMPL.format(title=htmllib.escape(os.path.splitext(os.path.basename(path))[0]), ver=VERSION, body=content)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(data)
                os.replace(tmp, path)
            except OSError as e:
                self._error(f"Could not save: {e}")
                return
            self.file = path
            self.modified = False
            self._refresh_title()
            self.lbl_state.set_text(f"Saved: {os.path.basename(path)}")
            GLib.timeout_add_seconds(4, lambda: (self.lbl_state.set_text(""), False)[1])
            if after:
                after()

        if path.lower().endswith(".txt"):
            self.js("xw.getText()", write)
        else:
            self.js("xw.getHTML()", write)

    def export_pdf(self):
        dlg = Gtk.FileChooserNative.new("Export as PDF", self, Gtk.FileChooserAction.SAVE, "Export", "Cancel")
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(os.path.splitext(self.name)[0] + ".pdf")
        if dlg.run() != Gtk.ResponseType.ACCEPT:
            return
        path = dlg.get_filename()
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.export_pdf_to(path)

    def export_pdf_to(self, path, done=None):
        op = WebKit2.PrintOperation.new(self.view)
        ps = Gtk.PrintSettings()
        ps.set_printer("Print to File")
        ps.set(Gtk.PRINT_SETTINGS_OUTPUT_FILE_FORMAT, "pdf")
        ps.set(Gtk.PRINT_SETTINGS_OUTPUT_URI, Gio.File.new_for_path(path).get_uri())
        op.set_print_settings(ps)
        setup = Gtk.PageSetup()
        setup.set_paper_size(Gtk.PaperSize.new(Gtk.PAPER_NAME_A4))
        op.set_page_setup(setup)
        finished = []

        def ok(*_):
            if finished:
                return
            finished.append(1)
            self.lbl_state.set_text(f"PDF created: {os.path.basename(path)}")
            if done:
                done(True)

        def fail(o, e):
            if DEBUG:
                print("pdf hatasi:", e.message, flush=True)
            if done:
                done(False)
            else:
                self._error(f"Could not create PDF: {e.message}")
        op.connect("finished", ok)
        op.connect("failed", fail)
        op.print_()

    def print_doc(self):
        WebKit2.PrintOperation.new(self.view).run_dialog(self)

    # ------------------------------------------------------------------ yonlendirme / kapanis
    def _on_policy(self, view, decision, dtype):
        PD = WebKit2.PolicyDecisionType
        if dtype in (PD.NAVIGATION_ACTION, PD.NEW_WINDOW_ACTION):
            uri = decision.get_navigation_action().get_request().get_uri() or ""
            if uri.startswith(("http://", "https://", "mailto:")):
                try:
                    Gtk.show_uri_on_window(self, uri, Gdk.CURRENT_TIME)
                except GLib.Error:
                    pass
                decision.ignore()
                return True
        return False

    def _on_crash(self, view, reason):
        self._error("The editor crashed unexpectedly. Save your document and reopen it.")

    def _on_delete(self, *_):
        if self.modified:
            return not self._confirm_discard()
        return False


class XenonWriterApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        for name, cb, accel in (("new-window", lambda *_: self.new_window(), None),
                                ("about", lambda *_: self._about(), None),
                                ("quit", lambda *_: self._quit(), ["<Primary>q"])):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accel:
                self.set_accels_for_action("app." + name, accel)

    def new_window(self):
        w = WriterWindow(self)
        w.show_all()
        w.present()
        return w

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            self.new_window()
        else:
            win.present()

    def do_open(self, files, n_files, hint):
        for f in files:
            w = self.new_window()
            w.open_path(f.get_path())

    def _about(self):
        d = Gtk.AboutDialog(transient_for=self.get_active_window(), modal=True, program_name="XenonWriter",
                            version=VERSION, comments="XenonOS word processor", logo_icon_name="xenonwriter",
                            license_type=Gtk.License.GPL_3_0)
        d.run()
        d.destroy()

    def _quit(self):
        for w in list(self.get_windows()):
            w.close()


def main():
    GLib.set_prgname("xenonwriter")
    GLib.set_application_name("XenonWriter")
    return XenonWriterApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
