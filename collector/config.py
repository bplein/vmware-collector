"""Hot-reloading dashboard config. A bad edit keeps the last good config and records the error."""
import os, threading, yaml

DEFAULTS = {"site": {"eyebrow": "vCenter", "title": "Dashboard"},
            "collect": {"interval_seconds": 900, "mhz_per_core": 2900},
            "store": {"type": "file", "keep_snapshots": 96},
            "pages": []}


def _merge(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def validate(cfg):
    from .widgets import WIDGETS
    ids = set()
    for p in cfg["pages"]:
        if "id" not in p or "title" not in p:
            raise ValueError("every page needs id and title")
        if p["id"] in ids:
            raise ValueError(f"duplicate page id {p['id']!r}")
        ids.add(p["id"])
        for w in p.get("widgets", []):
            if w.get("type") not in WIDGETS:
                raise ValueError(f"page {p['id']}: unknown widget type {w.get('type')!r} (known: {', '.join(sorted(WIDGETS))})")
            WIDGETS[w["type"]].check(w)
    if not cfg["pages"]:
        raise ValueError("config has no pages")


class Config:
    def __init__(self, path):
        self.path, self._mtime, self._lock = path, None, threading.Lock()
        self.cfg, self.error = _merge(DEFAULTS, {}), None
        self.get()

    def get(self):
        """Return the current config, reloading when the file changed (follows ConfigMap symlink swaps)."""
        with self._lock:
            try:
                m = os.stat(self.path).st_mtime
                if m != self._mtime:
                    with open(self.path, encoding="utf-8") as f:
                        new = _merge(DEFAULTS, yaml.safe_load(f) or {})
                    validate(new)
                    self.cfg, self.error, self._mtime = new, None, m
            except Exception as e:  # keep last good config
                self.error = f"{type(e).__name__}: {e}"
                try:
                    self._mtime = os.stat(self.path).st_mtime
                except OSError:
                    pass
            return self.cfg
