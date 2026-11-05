import argparse, json, logging, os, threading, time
from .config import Config
from .store import make_store
from .web import serve

log = logging.getLogger("collector")


def collect_loop(config, store, state, demo):
    while True:
        cfg = config.get()
        try:
            if demo:
                snap = json.load(open(demo))
            else:
                from .vsphere import collect
                snap = collect()
            store.save(snap)
            state["error"] = None
            log.info("collected %d pools", len(snap.get("pools", [])))
        except Exception as e:
            state["error"] = f"{type(e).__name__}: {e}"
            log.error("collection failed: %s", state["error"])
        time.sleep(int(cfg["collect"]["interval_seconds"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="collect one snapshot and exit")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config(os.environ.get("DASHBOARD_CONFIG", "/config/dashboard.yaml"))
    store = make_store(config.get()["store"], os.environ.get("DATA_DIR", "/data"))
    state, demo = {}, os.environ.get("COLLECTOR_DEMO_SNAPSHOT")  # demo: replay a saved snapshot, no vCenter
    if a.once:
        from .vsphere import collect
        store.save(json.load(open(demo)) if demo else collect())
        return
    threading.Thread(target=collect_loop, args=(config, store, state, demo), daemon=True).start()
    log.info("serving on :%s", os.environ.get("PORT", "8080"))
    serve(int(os.environ.get("PORT", "8080")), config, store, state)


if __name__ == "__main__":
    main()
