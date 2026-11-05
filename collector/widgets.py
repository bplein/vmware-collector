"""Widget registry. Add a widget: subclass Widget, set `type`, decorate with @register.
A widget gets (cfg, ctx) and returns an HTML fragment. ctx has .snapshot, .store, .site, .mhz."""
import html

WIDGETS = {}
esc = html.escape


def register(cls):
    WIDGETS[cls.type] = cls
    return cls


# metric key -> (label, formatter). cpu_busy is derived from live MHz.
def _cap(gb): return f"{gb/1024:.1f} TB" if gb >= 1024 else f"{gb:.0f} GB"
METRICS = {
    "prov_gb": ("Provisioned", _cap), "used_gb": ("Used", _cap), "mem_gb": ("Memory", _cap),
    "mem_act_gb": ("Mem used", _cap), "vcpu": ("vCPU", lambda v: f"{int(v)}"),
    "cpu_busy": ("CPU busy", lambda v: f"{v:.1f}"), "vms": ("VMs", lambda v: f"{int(v)}"),
}


def pool_rows(ctx):
    """One row per pool with powered-on VMs, summing the metrics."""
    rows = []
    for p in ctx.snapshot.get("pools", []):
        v = [x for x in p["vms"] if x["on"]]
        if v:
            s = lambda k: sum(x[k] for x in v)
            rows.append(dict(name=p["name"], vms=len(v), prov_gb=s("prov_gb"), used_gb=s("used_gb"), mem_gb=s("mem_gb"),
                             mem_act_gb=s("mem_act_gb"), vcpu=s("vcpu"), cpu_busy=s("cpu_mhz") / ctx.mhz))
    return rows


class Widget:
    type = ""
    @staticmethod
    def check(cfg): pass
    @staticmethod
    def render(cfg, ctx): raise NotImplementedError


def _need_metric(cfg, *keys):
    for k in keys:
        if cfg.get(k) and cfg[k] not in METRICS:
            raise ValueError(f"unknown metric {cfg[k]!r}; known: {', '.join(METRICS)}")


@register
class StatStrip(Widget):
    type = "stat_strip"

    @staticmethod
    def render(cfg, ctx):
        rows = pool_rows(ctx)
        t = lambda k: sum(r[k] for r in rows)
        all_stats = {
            "vms": ("Powered-on VMs", f'{t("vms")} <small>in {len(rows)} pools</small>'),
            "capacity": ("Capacity", f'{_cap(t("used_gb"))} <small>of {_cap(t("prov_gb"))}</small>'),
            "memory": ("Memory", f'{_cap(t("mem_act_gb"))} <small>of {_cap(t("mem_gb"))}</small>'),
            "cpu": ("CPU", f'{t("cpu_busy"):.0f} <small>of {int(t("vcpu"))} vCPU busy</small>'),
        }
        want = cfg.get("stats") or list(all_stats)
        return '<div class="stats">' + "".join(
            f'<div class="stat"><span>{a}</span><strong>{b}</strong></div>' for a, b in (all_stats[k] for k in want if k in all_stats)) + "</div>"


@register
class RankedPools(Widget):
    type = "ranked_pools"

    @staticmethod
    def check(cfg):
        if "metric" not in cfg:
            raise ValueError("ranked_pools needs a metric")
        _need_metric(cfg, "metric", "overlay")

    @staticmethod
    def render(cfg, ctx):
        m, ov, n = cfg["metric"], cfg.get("overlay"), int(cfg.get("top", 5))
        fmt = METRICS[m][1]
        top = sorted(pool_rows(ctx), key=lambda r: -r[m])[:n]
        mx = (top[0][m] if top else 0) or 1
        items = []
        for i, r in enumerate(top, 1):
            inner = f'<div class="fill base" style="width:{r[m]/mx*100:.1f}%"></div>'
            val = fmt(r[m])
            if ov:
                inner += f'<div class="fill act" style="width:{min(r[ov]/mx, 1)*100:.1f}%"></div>'
                val += f'<small>{METRICS[ov][1](r[ov])} {esc(METRICS[ov][0].lower())}</small>'
            items.append(f'<li class="row"><span class="rk">{i}</span><span class="who"><b>{esc(r["name"])}</b>'
                         f'<small>{r["vms"]} VMs on</small></span><div class="track" aria-hidden="true">{inner}</div>'
                         f'<span class="val">{val}</span></li>')
        sub = f'<p class="sub">{esc(cfg["sub"])}</p>' if cfg.get("sub") else ""
        return (f'<section class="card"><h2>{esc(cfg.get("title", METRICS[m][0]))}</h2>{sub}'
                f'<ol class="rank">{"".join(items) or "<li class=sub>No powered-on VMs</li>"}</ol></section>')


@register
class PoolTable(Widget):
    type = "pool_table"

    @staticmethod
    def check(cfg):
        for c in cfg.get("columns", []):
            _need_metric({"c": c}, "c")
        _need_metric(cfg, "sort")

    @staticmethod
    def render(cfg, ctx):
        cols = cfg.get("columns") or ["vms", "prov_gb", "used_gb"]
        rows = sorted(pool_rows(ctx), key=lambda r: -r[cfg.get("sort", cols[0])])
        head = "<th>Pool</th>" + "".join(f"<th>{esc(METRICS[c][0])}</th>" for c in cols)
        body = "".join(f"<tr><td>{esc(r['name'])}</td>" + "".join(f"<td>{METRICS[c][1](r[c])}</td>" for c in cols) + "</tr>" for r in rows)
        return f'<section class="card wide"><h2>{esc(cfg.get("title", "Pools"))}</h2><div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>'
