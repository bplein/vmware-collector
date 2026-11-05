"""Snapshot storage. FileStore today; add a time-series backend by subclassing Store and registering it."""
import json, os, time


class Store:
    """Interface. `series` is reserved for time-series widgets (needs a database backend)."""
    def save(self, snapshot): raise NotImplementedError
    def latest(self): raise NotImplementedError
    def series(self, metric, since=None, **filters):
        raise NotImplementedError("this store has no time-series support; configure a database store")


class FileStore(Store):
    def __init__(self, cfg, data_dir):
        self.dir = os.path.join(data_dir, "snapshots")
        self.keep = int(cfg.get("keep_snapshots", 96))
        os.makedirs(self.dir, exist_ok=True)

    def save(self, snapshot):
        name = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        for target in (f"{name}.json", "latest.json"):
            tmp = os.path.join(self.dir, target + ".tmp")
            with open(tmp, "w") as f:
                json.dump(snapshot, f)
            os.replace(tmp, os.path.join(self.dir, target))
        old = sorted(f for f in os.listdir(self.dir) if f.endswith("Z.json"))[:-self.keep]
        for f in old:
            os.remove(os.path.join(self.dir, f))

    def latest(self):
        try:
            with open(os.path.join(self.dir, "latest.json")) as f:
                return json.load(f)
        except FileNotFoundError:
            return None


STORES = {"file": FileStore}


def make_store(cfg, data_dir):
    t = cfg.get("type", "file")
    if t not in STORES:
        raise ValueError(f"unknown store type {t!r}; known: {', '.join(STORES)}")
    return STORES[t](cfg, data_dir)
