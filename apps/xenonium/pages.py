"""Xenonium: xenon:// internal pages and error pages (generates HTML). Theme: element Xenon (Xe, 54)."""
import html
import time
from urllib.parse import quote

CSS = """
:root{color-scheme:dark light;--bg:#0b0720;--bg2:#1a0f45;--fg:#f1ecff;--mut:#a79ccf;--acc:#6ee7ff;--vio:#9b6bff;--card:#140c36;--line:#3a2a78}
@media (prefers-color-scheme:light){:root{--bg:#f6f3ff;--bg2:#e3dcff;--fg:#1a0f45;--mut:#5d5390;--acc:#0a6f8a;--vio:#6a3df0;--card:#fff;--line:#cdc2f5}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;font-family:'Ubuntu','Noto Sans',system-ui,sans-serif;color:var(--fg);
background:radial-gradient(ellipse at 50% 30%,var(--bg2),var(--bg) 70%) fixed}
a{color:var(--acc);text-decoration:none}
.wrap{max-width:860px;margin:0 auto;padding:40px 24px}
h1{font-size:28px;margin:0 0 20px;letter-spacing:2px}
.row{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid var(--line);border-radius:10px;
background:var(--card);margin-bottom:8px}
.row .t{flex:1;min-width:0}.row .t b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .t small{color:var(--mut);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btn{border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:8px;padding:5px 12px;cursor:pointer}
.btn:hover{background:var(--line)}
.mut{color:var(--mut)}
input.s{width:100%;padding:12px 16px;border-radius:24px;border:2px solid var(--vio);background:var(--card);color:var(--fg);font-size:16px;outline:none;margin-bottom:18px}
.tile{display:inline-block;width:104px;height:104px;border-radius:12px;border:3px solid var(--vio);background:linear-gradient(135deg,var(--bg2),var(--bg));
position:relative;user-select:none;cursor:pointer}
.tile .n{position:absolute;left:9px;top:6px;font-size:14px;font-weight:700;color:var(--acc)}
.tile .m{position:absolute;right:8px;top:8px;font-size:9px;color:var(--mut)}
.tile .x{position:absolute;left:0;right:0;top:26px;text-align:center;font-size:48px;font-weight:700}
.tile .nm{position:absolute;left:0;right:0;bottom:8px;text-align:center;font-size:12px;letter-spacing:2px;color:var(--acc)}
.credits{margin-top:18px;padding:10px 18px;border-radius:12px;background:rgba(155,107,255,.22);font-weight:700;display:none}
"""

TILE = ("<div class='tile' id='xetile' title='Xe · element 54'><span class='n'>54</span><span class='m'>131.293</span>"
        "<span class='x'>Xe</span><span class='nm'>Xenon</span></div>"
        "<div class='credits' id='credits'>Founders: DTA &amp; CMK<br>Designer: EHA</div>")
TILE_JS = ("<script>(function(){var c=0,t=null,el=document.getElementById('xetile');"
           "el.addEventListener('click',function(){c++;clearTimeout(t);t=setTimeout(function(){c=0},600);"
           "if(c>=3){c=0;var d=document.getElementById('credits');d.style.display=d.style.display==='block'?'none':'block';}});})();</script>")


def _page(title, body, extra_head=""):
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>{extra_head}</head><body>{body}</body></html>"
    )


def newtab(bookmarks):
    tiles = []
    for b in bookmarks[:12]:
        host = html.escape(b["title"][:22])
        letter = html.escape((b["title"] or "?")[:1].upper())
        tiles.append(
            f"<a class='site' href='{html.escape(b['url'], quote=True)}'><span class='ic'>{letter}</span><span>{host}</span></a>"
        )
    if not tiles:
        tiles.append("<span class='mut'>Bookmarks you add (Ctrl+D) appear here</span>")
    extra = """<style>
    .hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
    h1.big{font-size:min(9vw,76px);letter-spacing:.22em;margin:14px 0 0;color:var(--fg);font-weight:700;padding-left:.22em}
    h1.big span{color:var(--vio)}
    p.sub{margin:6px 0 34px;letter-spacing:.3em;color:var(--acc);font-size:13px;text-transform:uppercase}
    form{width:min(600px,90vw)}
    .tiles{margin-top:34px;display:flex;flex-wrap:wrap;gap:14px;justify-content:center;max-width:760px}
    .site{width:104px;display:flex;flex-direction:column;align-items:center;gap:8px;padding:14px 6px;border-radius:14px;
    border:1px solid transparent;color:var(--fg);font-size:13px;text-align:center}
    .site:hover{background:var(--card);border-color:var(--line)}
    .ic{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:22px;
    font-weight:700;color:#0b0720;background:linear-gradient(135deg,#6ee7ff,#9b6bff)}
    .foot{position:fixed;bottom:14px;left:0;right:0;text-align:center;font-size:12px;color:var(--mut)}
    </style>"""
    body = (
        f"<div class='hero'>{TILE}<h1 class='big'>XENON<span>IUM</span></h1><p class='sub'>XenonOS web browser</p>"
        "<form action='https://duckduckgo.com/' method='get'>"
        "<input class='s' name='q' placeholder='Search or enter address…' autofocus autocomplete='off'></form>"
        f"<div class='tiles'>{''.join(tiles)}</div></div>"
        "<div class='foot'><a href='xenon://bookmarks'>Bookmarks</a> &middot; <a href='xenon://history'>History</a>"
        " &middot; <a href='xenon://downloads'>Downloads</a> &middot; <a href='xenon://extensions'>Extensions</a></div>"
        + TILE_JS
    )
    return _page("New tab", body, extra)


def bookmarks(items):
    rows = []
    for b in items:
        u = html.escape(b["url"], quote=True)
        rows.append(
            f"<div class='row'><div class='t'><b><a href='{u}'>{html.escape(b['title'])}</a></b><small>{html.escape(b['url'])}</small></div>"
            f"<button class='btn' onclick=\"fetch('xenon://bookmarks/remove?u={quote(b['url'], safe='')}')"
            f".then(()=>location.reload())\">Delete</button></div>"
        )
    body = "<div class='wrap'><h1>Bookmarks</h1>" + ("".join(rows) or "<p class='mut'>No bookmarks yet.</p>") + "</div>"
    return _page("Bookmarks", body)


def history(entries, query=""):
    rows = []
    for e in entries:
        t = time.strftime("%Y-%m-%d %H:%M", time.localtime(e["ts"]))
        u = html.escape(e["url"], quote=True)
        rows.append(
            f"<div class='row'><div class='t'><b><a href='{u}'>{html.escape(e['title'] or e['url'])}</a></b>"
            f"<small>{html.escape(e['url'])}</small></div><span class='mut'>{t}</span></div>"
        )
    body = (
        "<div class='wrap'><h1>History</h1>"
        f"<form method='get' action='xenon://history'><input class='s' name='q' value='{html.escape(query, quote=True)}' placeholder='Search history…'></form>"
        "<p><button class='btn' onclick=\"if(confirm('Clear all history?'))fetch('xenon://history/clear').then(()=>location.reload())\">Clear history</button></p>"
        + ("".join(rows) or "<p class='mut'>No entries.</p>")
        + "</div>"
    )
    return _page("History", body)


def downloads(items):
    rows = []
    for d in items:
        rows.append(
            f"<div class='row'><div class='t'><b>{html.escape(d['name'])}</b><small>{html.escape(d['path'])}</small></div>"
            f"<span class='mut'>{html.escape(d['status'])}</span></div>"
        )
    body = "<div class='wrap'><h1>Downloads</h1>" + ("".join(rows) or "<p class='mut'>No downloads in this session.</p>") + "</div>"
    return _page("Downloads", body)


def extensions(exts):
    rows = []
    for e in exts:
        state = "On" if e["enabled"] else "Off"
        btn = "Turn off" if e["enabled"] else "Turn on"
        rows.append(
            f"<div class='row'><div class='t'><b>{html.escape(e['name'])} <span class='mut'>v{html.escape(e['version'])}</span></b>"
            f"<small>{html.escape(e['description'])}</small></div><span class='mut'>{state}</span>"
            f"<button class='btn' onclick=\"fetch('xenon://extensions/toggle?id={quote(e['id'])}').then(()=>location.reload())\">{btn}</button></div>"
        )
    body = (
        "<div class='wrap'><h1>Extensions</h1>" + ("".join(rows) or "<p class='mut'>No extensions installed.</p>")
        + "<p class='mut'>Changes apply to open tabs after a reload. "
        "To add your own extension, put it in ~/.local/share/xenonium/extensions/&lt;name&gt;/ with a manifest.json.</p></div>"
    )
    return _page("Extensions", body)


def error(title, message, uri="", extra_html=""):
    body = (
        "<div class='wrap' style='padding-top:14vh;text-align:center'>"
        f"<h1 style='color:var(--acc)'>{html.escape(title)}</h1>"
        f"<p>{html.escape(message)}</p>"
        f"<p class='mut'>{html.escape(uri)}</p>"
        f"{extra_html}"
        "<p><button class='btn' onclick='location.reload()'>Try again</button></p></div>"
    )
    return _page(title, body)


def about(version):
    body = (
        "<div class='wrap' style='text-align:center;padding-top:10vh'>"
        f"{TILE}"
        "<h1 style='color:var(--fg);font-size:44px;letter-spacing:.2em;margin-top:18px'>XENON<span style='color:var(--vio)'>IUM</span></h1>"
        f"<p>Version {html.escape(version)} &middot; the XenonOS web browser</p>"
        "<p class='mut'>Built on WebKitGTK. Includes bookmarks, history, tabs, downloads and extension support (XenonTranslate included).</p>"
        "</div>" + TILE_JS
    )
    return _page("About Xenonium", body)
