#!/usr/bin/env python3
"""Translates application UI strings (Python string constants) from Turkish to English.

  python3 translate_ui.py report <files...>   -> candidate strings + suggested translation table (translate_map.json)
  python3 translate_ui.py apply  <files...>   -> applies translate_map.json (the hand-corrected version) to the sources

Translation service: translate.googleapis.com (gtx). The result must be reviewed by hand.
"""
import ast
import json
import re
import sys
import time
import urllib.parse
import urllib.request

MAP = "translate_map.json"
SKIP_EXACT = {
    "Print to File", "pdf", "UTF-8", "Gtk", "Adw", "WebKit2", "xenon", "XenonPad", "XenonWriter", "Xenonium",
    "XenonOS", "DuckDuckGo", "Google", "Bing", "Yandex", "Startpage", "GPL", "Windows-1254", "ISO-8859-1",
}


def candidates(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    doc_ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                    and isinstance(b[0].value.value, str):
                doc_ids.add(id(b[0].value))
    out = {}
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)) or id(n) in doc_ids:
            continue
        s = n.value
        if s in SKIP_EXACT or len(s.strip()) < 2 or not re.search(r"[A-Za-z]", s):
            continue
        if re.search(r"[<>{}]|://|^[a-z_.\-/:0-9]+$|^%|^#|^\.|\\x|^[A-Z_]+$|@|\.desktop|\.json|\.py|\.png|\.svg", s):
            continue
        if "\n" in s and len(s) > 120:
            continue
        # count it as UI text unless it is a single lowercase word (code identifier)
        if " " not in s and s[0].islower():
            continue
        out[s] = out.get(s, 0) + 1
    return out


def gtx(text):
    q = urllib.parse.urlencode({"client": "gtx", "sl": "tr", "tl": "en", "dt": "t", "q": text})
    req = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + q,
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode())
    return "".join(x[0] for x in d[0])


def report(files):
    allc = {}
    for f in files:
        for s, c in candidates(f).items():
            allc[s] = allc.get(s, 0) + c
    result = {}
    for i, s in enumerate(sorted(allc)):
        try:
            t = gtx(s)
        except Exception as e:  # noqa: BLE001
            t = s
            print("HATA", s, e, file=sys.stderr)
        # preserve leading/trailing whitespace and line endings
        lead = re.match(r"^\s*", s).group(0)
        trail = re.search(r"\s*$", s).group(0)
        t = lead + t.strip() + trail
        # approximately preserve capitalization and punctuation
        if s.rstrip().endswith(":") and not t.rstrip().endswith(":"):
            t = t.rstrip() + ":" + trail
        result[s] = t
        time.sleep(0.08)
    json.dump(result, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{len(result)} metin -> {MAP}")


def apply(files):
    m = json.load(open(MAP, encoding="utf-8"))
    for path in files:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        lines = src.split("\n")
        # replace by line/column, from the end to the start
        repl = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in m and m[n.value] != n.value:
                if n.end_lineno != n.lineno:
                    continue
                repl.append((n.lineno - 1, n.col_offset, n.end_col_offset, n.value))
        repl.sort(key=lambda r: (r[0], r[1]), reverse=True)
        done = 0
        # ast column offsets are in UTF-8 BYTES: process lines as bytes
        blines = [l.encode("utf-8") for l in lines]
        for ln, c0, c1, val in repl:
            seg = blines[ln][c0:c1].decode("utf-8")
            if not (seg.startswith('"') or seg.startswith("'")):
                # f-string part: the slice can only be the constant part; replace the unquoted part directly
                if seg == val or seg == val.replace("\n", "\\n"):
                    new = m[val].replace("\\", "\\\\").replace("\n", "\\n").encode("utf-8")
                    blines[ln] = blines[ln][:c0] + new + blines[ln][c1:]
                    done += 1
                continue
            q = seg[0]
            new = m[val].replace("\\", "\\\\").replace(q, "\\" + q).replace("\n", "\\n")
            blines[ln] = blines[ln][:c0] + (q + new + q).encode("utf-8") + blines[ln][c1:]
            done += 1
        text = "\n".join(b.decode("utf-8") for b in blines)
        ast.parse(text)          # syntax check: if broken, DO NOT WRITE the file
        open(path, "w", encoding="utf-8").write(text)
        print(f"{path}: {done} metin degistirildi")


if __name__ == "__main__":
    mode, files = sys.argv[1], sys.argv[2:]
    {"report": report, "apply": apply}[mode](files)
