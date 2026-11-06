# vmware-collector

Resource-pool usage dashboard for vCenter, built on the [vmware-aiops](https://github.com/vmware-skills/VMware-AIops) package
(installed from PyPI into `python:3.12-slim`). Read-only against vCenter.

## Run

Docker Compose:
```
cp .env.example .env                                  # set the vCenter password
cp aiops/config.example.yaml aiops/config.yaml        # set host and user
docker compose up -d                                  # http://localhost:8080
```
Kubernetes: see the header of `deploy/k8s/vmware-collector.yaml` (StatefulSet, ConfigMaps, Secret, Service).

## Configure pages

`config/dashboard.yaml` (the `dashboard` ConfigMap in Kubernetes) defines pages and widgets. Edit it and the page updates
within about a minute, no restart. A bad edit keeps the last good config and shows an error banner.

Widgets: `stat_strip`, `ranked_pools` (metric, overlay, top), `pool_table` (columns, sort).
Metrics: `prov_gb used_gb mem_gb mem_act_gb vcpu cpu_busy vms`.

## Extend

- **New widget:** add a class with `@register` in `collector/widgets.py`; it is then usable as `type: <name>`.
- **Database / time series:** subclass `Store` in `collector/store.py`, implement `save` and `series`, add it to `STORES`,
  set `store.type` in the config. Widgets receive the store as `ctx.store`.
- **Other data sources:** `collector/vsphere.py` returns a plain dict snapshot; add collectors beside it.

## Versions

`VERSION` is this image's version. The upstream package is pinned by `AIOPS_VERSION` in the Dockerfile. Bump it by hand to
upgrade.

Pushes to `main` (or tags `v*`) run GitHub Actions (`.github/workflows/docker-ghcr.yml`), which builds `linux/amd64` and
pushes `ghcr.io/bplein/vmware-collector:{latest,<VERSION>,sha-<git sha>}`. The package is public, so pulls need no auth.
Local build/push also works with `make build` / `make push` / `make release` (REGISTRY defaults to GHCR; override if needed).

Test locally with no vCenter: `COLLECTOR_DEMO_SNAPSHOT=tests/sample_snapshot.json DASHBOARD_CONFIG=config/dashboard.yaml DATA_DIR=/tmp/d python -m collector`
