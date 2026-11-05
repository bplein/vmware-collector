import html, json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .widgets import WIDGETS, esc

CSS = """:root{--bg:#fff5e3;--card:#fffdf9;--fg:#2d2a27;--muted:#73716f;--faint:#9e9b98;--border:#e7e3dc;--track:#efe9dd;--primary:#ff7023;--base:#8fa596;--act:#5a6359;--err:#da4d72;--shadow:0 2px 8px rgba(45,42,39,.08);--radius:8px}
@media (prefers-color-scheme:dark){:root{--bg:#1d1b19;--card:#262321;--fg:#f2ece2;--muted:#a8a29a;--faint:#7f7a73;--border:#3a3631;--track:#312e2a;--base:#6f8577;--act:#b7cbbd;--shadow:0 2px 8px rgba(0,0,0,.35);color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,system-ui,sans-serif;line-height:1.5;padding:32px max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left))}
.wrap{max-width:1080px;margin:0 auto;display:flex;flex-direction:column;gap:24px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--primary);font-weight:600}
h1{font-size:clamp(26px,4vw,36px);line-height:1.15;margin:0;font-weight:700}.lede{margin:4px 0 0;color:var(--muted);max-width:65ch;font-size:15px}
nav{display:flex;gap:6px;flex-wrap:wrap}nav a{padding:6px 12px;border-radius:var(--radius);color:var(--muted);text-decoration:none;font-size:14px;border:1px solid transparent}
nav a.on{background:var(--card);border-color:var(--border);color:var(--fg);font-weight:600}nav a:hover{color:var(--primary)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:12px 16px;display:flex;flex-direction:column;gap:2px;min-width:0}
.stat span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}.stat strong{font-size:21px;font-weight:600;font-variant-numeric:tabular-nums}.stat small{font-size:13px;color:var(--muted);font-weight:500}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:16px}.wide{grid-column:1/-1}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px;display:flex;flex-direction:column;gap:12px;min-width:0}
.card h2{margin:0;font-size:17px;font-weight:600}.sub{margin:0;color:var(--muted);font-size:13px}
.rank{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.row{display:grid;grid-template-columns:20px minmax(0,9.5rem) minmax(0,1fr) minmax(5rem,auto);align-items:center;gap:10px}
.rk{font-size:13px;color:var(--faint)}.who{display:flex;flex-direction:column;min-width:0}.who b{font-size:14px;overflow-wrap:anywhere}.who small,.val small{font-size:12px;color:var(--muted);font-weight:400}
.track{position:relative;height:12px;background:var(--track);border-radius:6px;overflow:hidden}.fill{position:absolute;inset:0 auto 0 0;border-radius:6px}.fill.base{background:var(--base)}.fill.act{background:var(--act)}
.val{text-align:right;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;display:flex;flex-direction:column}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}th,td{text-align:right;padding:6px 10px;border-bottom:1px solid var(--border)}th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.banner{background:var(--card);border:1px solid var(--err);border-left-width:4px;border-radius:var(--radius);padding:10px 14px;font-size:14px}
footer{font-size:12.5px;color:var(--muted)}
@media (max-width:520px){.row{grid-template-columns:20px minmax(0,1fr) auto}.track{grid-column:2/4;grid-row:2}}"""


class Ctx:
    def __init__(self, snapshot, store, site, mhz):
        self.snapshot, self.store, self.site, self.mhz = snapshot, store, site, mhz


def render_page(cfg, cfg_error, page_id, snapshot, store, collect_error):
    pages = cfg["pages"]
    page = next((p for p in pages if p["id"] == page_id), pages[0])
    site = cfg["site"]
    nav = "".join(f'<a href="/p/{esc(p["id"])}" class="{"on" if p is page else ""}">{esc(p["title"])}</a>' for p in pages)
    banners = ""
    if cfg_error:
        banners += f'<div class="banner">Config error, showing the last good config: {esc(cfg_error)}</div>'
    if collect_error:
        banners += f'<div class="banner">Last collection failed: {esc(collect_error)}</div>'
    if snapshot is None:
        body = '<div class="banner" style="border-color:var(--primary)">No data yet. The first collection is running.</div>'
        stamp = ""
    else:
        ctx = Ctx(snapshot, store, site, cfg["collect"]["mhz_per_core"])
        parts, grid = [], []
        for w in page.get("widgets", []):
            try:
                h = WIDGETS[w["type"]].render(w, ctx)
            except Exception as e:
                h = f'<div class="banner">Widget {esc(w["type"])} failed: {esc(str(e))}</div>'
            if w["type"] == "stat_strip":
                parts.append(h)
            else:
                grid.append(h)
        body = "".join(parts) + f'<div class="grid">{"".join(grid)}</div>'
        stamp = f'Collected {esc(snapshot["collected_at"])}'
    lede = f'<p class="lede">{esc(page["lede"])}</p>' if page.get("lede") else ""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(page["title"])} · {esc(site["title"])}</title><meta http-equiv="refresh" content="60">'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">'
            f'<style>{CSS}</style></head><body><div class="wrap"><header><span class="eyebrow">{esc(site["eyebrow"])}</span>'
            f'<h1>{esc(page["title"])}</h1>{lede}</header><nav>{nav}</nav>{banners}{body}<footer>{stamp}</footer></div></body></html>')


def serve(port, config, store, state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, ctype, data):
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/healthz":
                return self._send(200, "text/plain", b"ok")
            if path == "/api/snapshot":
                return self._send(200, "application/json", json.dumps(store.latest() or {}).encode())
            cfg = config.get()
            pid = path[3:] if path.startswith("/p/") else None
            if path not in ("/", "") and pid is None:
                return self._send(404, "text/plain", b"not found")
            page = render_page(cfg, config.error, pid, store.latest(), store, state.get("error"))
            self._send(200, "text/html; charset=utf-8", page.encode())
    ThreadingHTTPServer(("", port), H).serve_forever()
