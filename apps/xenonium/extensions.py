"""Xenonium eklenti sistemi.

Her eklenti bir klasordur:  manifest.json + (content.js, content.css, icon.svg ...)
Icerik betikleri sayfadan YALITILMIS bir JavaScript dunyasinda calisir ("xenon-ext-<id>"):
sayfanin betikleri eklentinin degiskenlerine / xenon API'sine erisemez.

manifest.json:
{
  "id": "xenontranslate", "name": "...", "version": "1.0", "description": "...",
  "icon": "icon.svg",
  "content_scripts": [{"matches": ["http://*/*", "https://*/*"], "js": ["content.js"], "css": ["content.css"],
                       "run_at": "document_end"}],
  "permissions": {"hosts": ["translate.googleapis.com"]},
  "browser_action": {"title": "Sayfayi cevir", "command": "toggle-panel"}
}

Eklenti JS API'si (yalnizca eklentinin kendi dunyasinda):
  xenon.fetch(url, {method, headers, body})  -> {status, text}   (yalnizca manifestteki hosts icin)
  xenon.storage.get(key, varsayilan) / xenon.storage.set(key, deger)
  xenon.info()                               -> {locale, version}
  xenon.onCommand((ad, arguman) => ...)      (arac cubugu dugmesi vb. bu komutlari tetikler)
"""
import json
import locale
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import gi

gi.require_version("WebKit2", "4.1")
from gi.repository import GLib, WebKit2  # noqa: E402

from store import DATA, ExtStorage  # noqa: E402

VERSION = "1.0"
HERE = Path(__file__).resolve().parent
SYSTEM_DIRS = [Path("/usr/share/xenonium/extensions"), HERE / "extensions"]
USER_DIR = DATA / "extensions"
USER_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 2 * 1024 * 1024
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Xenonium/" + VERSION

API_JS = r"""
(function(){
  if (window.xenon) return;
  var H = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers["xenonext___ID__"];
  var seq = 0, pend = {}, cmds = [];
  window.__xenonResolve = function(id, ok, payload){
    var p = pend[id]; if (!p) return; delete pend[id];
    if (ok) p.res(payload); else p.rej(new Error(String(payload)));
  };
  window.__xenonCommand = function(name, arg){
    cmds.forEach(function(f){ try { f(name, arg); } catch(e) { console.error(e); } });
  };
  function call(method, args){
    return new Promise(function(res, rej){
      var id = ++seq; pend[id] = {res: res, rej: rej};
      H.postMessage(JSON.stringify({id: id, method: method, args: args || {}, href: location.href}));
    });
  }
  window.xenon = {
    id: "__ID__",
    fetch: function(url, opts){ return call("fetch", Object.assign({url: url}, opts || {})); },
    storage: {
      get: function(k, d){ return call("storage.get", {key: k}).then(function(v){ return (v === null || v === undefined) ? d : v; }); },
      set: function(k, v){ return call("storage.set", {key: k, value: v}); }
    },
    info: function(){ return call("info"); },
    onCommand: function(f){ cmds.push(f); }
  };
})();
"""


class Extension:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path / "manifest.json", "r", encoding="utf-8") as f:
            m = json.load(f)
        self.manifest = m
        self.id = m.get("id") or self.path.name
        self.name = m.get("name", self.id)
        self.version = str(m.get("version", "0"))
        self.description = m.get("description", "")
        self.icon = (self.path / m["icon"]) if m.get("icon") else None
        self.hosts = list(m.get("permissions", {}).get("hosts", []))
        self.content_scripts = m.get("content_scripts", [])
        self.action = m.get("browser_action")
        self.world = f"xenon-ext-{self.id}"
        self.handler = f"xenonext_{self.id}"
        self.enabled = True
        self.storage = ExtStorage(self.id)

    def host_allowed(self, url):
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            return False
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    def read(self, rel):
        try:
            return (self.path / rel).read_text(encoding="utf-8")
        except OSError:
            return ""


class ExtensionManager:
    def __init__(self, settings, resolve_view):
        """resolve_view(href) -> mesaji gonderen WebView (veya None)"""
        self.settings = settings
        self.resolve_view = resolve_view
        self.extensions = {}
        self.ucm = WebKit2.UserContentManager()
        self.load()
        self._connect_handlers()
        self.apply_scripts()

    # ---- yukleme ----
    def load(self):
        self.extensions.clear()
        disabled = set(self.settings.get("disabled_extensions") or [])
        for base in SYSTEM_DIRS + [USER_DIR]:  # sonraki ayni id'yi ezer (kullanici > sistem)
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if (d / "manifest.json").is_file():
                    try:
                        ext = Extension(d)
                    except (OSError, ValueError, KeyError) as e:
                        print(f"[xenonium] could not load extension {d}: {e}")
                        continue
                    ext.enabled = ext.id not in disabled
                    self.extensions[ext.id] = ext

    def _connect_handlers(self):
        for ext in self.extensions.values():
            self.ucm.register_script_message_handler_in_world(ext.handler, ext.world)
            self.ucm.connect(f"script-message-received::{ext.handler}", self._on_message, ext)

    def apply_scripts(self):
        self.ucm.remove_all_scripts()
        self.ucm.remove_all_style_sheets()
        if os.environ.get("XENONIUM_NO_EXT"):
            return
        F = WebKit2.UserContentInjectedFrames.TOP_FRAME
        for ext in self.extensions.values():
            if not ext.enabled:
                continue
            for cs in ext.content_scripts:
                allow = cs.get("matches") or ["http://*/*", "https://*/*"]
                allow = [p for p in allow if p != "<all_urls>"] or ["http://*/*", "https://*/*"]
                t_end = cs.get("run_at", "document_end") != "document_start"
                skip = set((os.environ.get("XENONIUM_SKIP") or "").split(","))
                if "api" not in skip:
                    self.ucm.add_script(
                        WebKit2.UserScript.new_for_world(
                            API_JS.replace("__ID__", ext.id), F, WebKit2.UserScriptInjectionTime.START, ext.world, allow, None
                        )
                    )
                for js in ([] if "content" in skip else cs.get("js", [])):
                    self.ucm.add_script(
                        WebKit2.UserScript.new_for_world(
                            ext.read(js), F,
                            WebKit2.UserScriptInjectionTime.END if t_end else WebKit2.UserScriptInjectionTime.START,
                            ext.world, allow, None,
                        )
                    )
                for css in cs.get("css", []):
                    self.ucm.add_style_sheet(
                        WebKit2.UserStyleSheet.new_for_world(
                            ext.read(css), F, WebKit2.UserStyleLevel.USER, ext.world, allow, None
                        )
                    )

    def toggle(self, ext_id):
        ext = self.extensions.get(ext_id)
        if not ext:
            return
        ext.enabled = not ext.enabled
        disabled = set(self.settings.get("disabled_extensions") or [])
        (disabled.discard if ext.enabled else disabled.add)(ext.id)
        self.settings.set("disabled_extensions", sorted(disabled))
        self.apply_scripts()

    def list_info(self):
        return [
            {"id": e.id, "name": e.name, "version": e.version, "description": e.description, "enabled": e.enabled}
            for e in self.extensions.values()
        ]

    # ---- komut gonderme (arac cubugu dugmesi) ----
    def run_command(self, view, ext_id, name, arg=None):
        ext = self.extensions.get(ext_id)
        if not ext or not ext.enabled or view is None:
            return
        js = f"window.__xenonCommand && window.__xenonCommand({json.dumps(name)}, {json.dumps(arg)});"
        view.evaluate_javascript(js, -1, ext.world, None, None, None)

    # ---- eklentiden gelen mesajlar ----
    def _reply(self, ext, href, mid, ok, payload):
        view = self.resolve_view(href)
        if os.environ.get("XENONIUM_DEBUG"):
            print(f"[xenonium] ext reply id={mid} ok={ok} view={'yes' if view else 'NONE'} payload={str(payload)[:80]!r}", flush=True)
        if view is None:
            return
        js = f"window.__xenonResolve({mid}, {'true' if ok else 'false'}, {json.dumps(payload)});"
        view.evaluate_javascript(js, -1, ext.world, None, None, None)

    def _on_message(self, ucm, value, ext):
        if os.environ.get("XENONIUM_DEBUG"):
            print(f"[xenonium] raw ext message from {ext.id}: {type(value).__name__}", flush=True)
        try:
            jsv = value.get_js_value() if hasattr(value, "get_js_value") else value
            msg = json.loads(jsv.to_string())
            mid, method, args, href = msg["id"], msg["method"], msg.get("args", {}), msg.get("href", "")
        except (ValueError, KeyError, AttributeError):
            return
        if os.environ.get("XENONIUM_DEBUG"):
            print(f"[xenonium] ext msg {ext.id} id={mid} {method} {str(args)[:100]!r}", flush=True)
        if not ext.enabled:
            return
        try:
            if method == "storage.get":
                self._reply(ext, href, mid, True, ext.storage.get(args.get("key")))
            elif method == "storage.set":
                ext.storage.set(args.get("key"), args.get("value"))
                self._reply(ext, href, mid, True, True)
            elif method == "info":
                self._reply(ext, href, mid, True, {"locale": (locale.getlocale()[0] or "en_US"), "version": VERSION})
            elif method == "fetch":
                self._do_fetch(ext, href, mid, args)
            else:
                self._reply(ext, href, mid, False, f"unknown method: {method}")
        except Exception as e:  # noqa: BLE001  (eklentiye hata olarak don)
            self._reply(ext, href, mid, False, str(e))

    def _do_fetch(self, ext, href, mid, args):
        url = str(args.get("url", ""))
        if urlparse(url).scheme not in ("http", "https") or not ext.host_allowed(url):
            self._reply(ext, href, mid, False, "access to this address is not permitted (manifest permissions.hosts)")
            return
        method = str(args.get("method", "GET")).upper()
        headers = {"User-Agent": UA}
        headers.update({str(k): str(v) for k, v in (args.get("headers") or {}).items()})
        body = args.get("body")
        data = body.encode("utf-8") if isinstance(body, str) else None

        def work():
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=15) as r:
                    raw = r.read(MAX_BYTES + 1)
                    status = r.status
                if len(raw) > MAX_BYTES:
                    raise ValueError("response is too large")
                res = (True, {"status": status, "text": raw.decode("utf-8", "replace")})
            except urllib.error.HTTPError as e:
                res = (True, {"status": e.code, "text": e.read(MAX_BYTES).decode("utf-8", "replace")})
            except Exception as e:  # noqa: BLE001
                res = (False, str(e))
            GLib.idle_add(self._reply, ext, href, mid, res[0], res[1])

        threading.Thread(target=work, daemon=True).start()
