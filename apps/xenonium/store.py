"""Xenonium: kalici veri (yer imleri, gecmis, ayarlar, oturum)."""
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "xenonium"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "xenonium"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "xenonium"

for _d in (DATA, CONFIG, CACHE, CONFIG / "extensions"):
    _d.mkdir(parents=True, exist_ok=True)

DEFAULTS = {
    "homepage": "xenon://newtab",
    "search_url": "https://duckduckgo.com/?q=%s",
    "restore_session": True,
    "download_dir": "",
    "disabled_extensions": [],
}


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Settings:
    def __init__(self):
        self.path = CONFIG / "settings.json"
        self.data = dict(DEFAULTS)
        self.data.update(_read_json(self.path, {}))

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        _write_json(self.path, self.data)

    def download_dir(self):
        d = self.get("download_dir")
        if d and os.path.isdir(d):
            return d
        for cand in (os.environ.get("XDG_DOWNLOAD_DIR"), str(HOME / "Downloads"), str(HOME)):
            if cand and os.path.isdir(cand):
                return cand
        return str(HOME)


class Bookmarks:
    def __init__(self):
        self.path = DATA / "bookmarks.json"
        self.items = _read_json(self.path, [])

    def _save(self):
        _write_json(self.path, self.items)

    def has(self, url):
        return any(b["url"] == url for b in self.items)

    def add(self, url, title):
        if not self.has(url):
            self.items.append({"url": url, "title": title or url, "added": int(time.time())})
            self._save()

    def remove(self, url):
        self.items = [b for b in self.items if b["url"] != url]
        self._save()

    def toggle(self, url, title):
        if self.has(url):
            self.remove(url)
            return False
        self.add(url, title)
        return True


class History:
    def __init__(self):
        self.path = DATA / "history.sqlite"
        self._lock = threading.Lock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY, url TEXT, title TEXT, ts INTEGER)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_ts ON visits(ts)")
        self.db.commit()

    def add(self, url, title):
        if not url or url.startswith(("xenon:", "about:", "data:", "view-source:")):
            return
        with self._lock:
            last = self.db.execute("SELECT id, url FROM visits ORDER BY id DESC LIMIT 1").fetchone()
            if last and last[1] == url:
                self.db.execute("UPDATE visits SET title=?, ts=? WHERE id=?", (title or url, int(time.time()), last[0]))
            else:
                self.db.execute("INSERT INTO visits(url,title,ts) VALUES(?,?,?)", (url, title or url, int(time.time())))
            self.db.commit()

    def update_title(self, url, title):
        if not url or not title:
            return
        with self._lock:
            self.db.execute(
                "UPDATE visits SET title=? WHERE id=(SELECT id FROM visits WHERE url=? ORDER BY id DESC LIMIT 1)",
                (title, url),
            )
            self.db.commit()

    def recent(self, limit=300, query=""):
        with self._lock:
            if query:
                q = f"%{query}%"
                rows = self.db.execute(
                    "SELECT url,title,ts FROM visits WHERE url LIKE ? OR title LIKE ? ORDER BY id DESC LIMIT ?",
                    (q, q, limit),
                ).fetchall()
            else:
                rows = self.db.execute("SELECT url,title,ts FROM visits ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"url": r[0], "title": r[1], "ts": r[2]} for r in rows]

    def suggest(self, text, limit=6):
        """Adres cubugu onerileri: en cok ziyaret edilenler."""
        q = f"%{text}%"
        with self._lock:
            rows = self.db.execute(
                "SELECT url, MAX(title), COUNT(*) c FROM visits WHERE url LIKE ? OR title LIKE ? "
                "GROUP BY url ORDER BY c DESC, MAX(ts) DESC LIMIT ?",
                (q, q, limit),
            ).fetchall()
        return [{"url": r[0], "title": r[1]} for r in rows]

    def clear(self):
        with self._lock:
            self.db.execute("DELETE FROM visits")
            self.db.commit()


class Session:
    def __init__(self):
        self.path = DATA / "session.json"

    def load(self):
        data = _read_json(self.path, [])
        return [u for u in data if isinstance(u, str)]

    def save(self, urls):
        _write_json(self.path, [u for u in urls if u and not u.startswith("view-source:")])


class Downloads:
    """Oturum boyunca indirme listesi (xenon://downloads sayfasi icin)."""

    def __init__(self):
        self.items = []  # {name, path, status, size}

    def add(self, name, path):
        item = {"name": name, "path": path, "status": "downloading", "ts": int(time.time())}
        self.items.insert(0, item)
        return item


class ExtStorage:
    def __init__(self, ext_id):
        self.path = CONFIG / "extensions" / f"{ext_id}.json"
        self.data = _read_json(self.path, {})

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        _write_json(self.path, self.data)
