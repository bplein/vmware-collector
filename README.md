# vmware-collector

Resource-pool usage dashboard for vCenter. A single container reads vCenter on an interval, aggregates
capacity, memory and CPU per resource pool for powered-on VMs, and serves a small web UI. Read-only against
vCenter. Pages are defined in a hot-reloading YAML file.

This project builds on the upstream [VMware-AIops](https://github.com/vmware-skills/VMware-AIops) package
(installed from PyPI as `vmware-aiops`), which provides the vCenter connection and target config loading.

## Prerequisites

- A vCenter to point at, with a read-only account.
- Docker (Compose path) or a Kubernetes/OpenShift cluster (deploy path).
- Python 3.12+ with `pyyaml` only if you want to run the demo or tests directly on your host.

## Demo, no vCenter needed

Replays a saved snapshot instead of collecting:

```sh
pip install pyyaml
COLLECTOR_DEMO_SNAPSHOT=tests/sample_snapshot.json \
DASHBOARD_CONFIG=config/dashboard.yaml \
DATA_DIR=$(mktemp -d) \
python -m collector
```

Open http://localhost:8080.

## Point it at a real vCenter

### Docker Compose

```sh
cp aiops/config.example.yaml aiops/config.yaml   # set the target host and read-only username
cp .env.example .env                             # set the password
docker compose up -d                             # http://localhost:8080
```

This uses the published image. Add `--build` to build from this checkout instead.

The only secret is the vCenter password, and it is never in the config file. The upstream package reads it
from the environment as `VMWARE_<TARGET>_PASSWORD`, where `<TARGET>` is the target `name` from
`aiops/config.yaml`, uppercased with non-alphanumeric characters replaced by underscores: target `cna-lab`
means `VMWARE_CNA_LAB_PASSWORD`. If you rename the target, change both.

### Kubernetes or OpenShift

```sh
kubectl create namespace vmware-collector
kubectl -n vmware-collector create secret generic vcenter \
  --from-literal=VMWARE_CNA_LAB_PASSWORD='...'
kubectl apply -f deploy/k8s/vmware-collector.yaml
```

The manifest defines a single-replica StatefulSet (1 Gi PVC for snapshots), ConfigMaps for the dashboard
pages and the aiops targets, a Service, and an OpenShift Route (edge TLS). The container runs non-root with
a read-only root filesystem, all capabilities dropped and no service-account token. The image is public on
ghcr.io, so no pull secret is needed.

Notes:

- The Route host is hardcoded to one lab's ingress domain. Edit it for your cluster or delete it. On plain
  Kubernetes use an Ingress or `kubectl port-forward svc/vmware-collector 8080:80`.
- The pod sets `VMWARE_AIOPS_CONFIG=/aiops/config.yaml`. The image default lives under `/root`, which an
  arbitrary UID (OpenShift SCC) cannot read, so the config is mounted at a UID-neutral path.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VMWARE_<TARGET>_PASSWORD` | none | vCenter password. The only secret. |
| `VMWARE_AIOPS_CONFIG` | `/root/.vmware-aiops/config.yaml` (`/aiops/config.yaml` on k8s) | Upstream package config: target host, username, port, SSL verification |
| `DASHBOARD_CONFIG` | `/config/dashboard.yaml` | Dashboard pages, hot-reloaded |
| `DATA_DIR` | `/data` | Snapshot JSON files are written to `$DATA_DIR/snapshots` |
| `PORT` | `8080` | Web UI port |
| `COLLECTOR_DEMO_SNAPSHOT` | none | Path to a snapshot JSON to replay instead of collecting |

HTTP endpoints: `/` dashboard pages, `/healthz` health check, `/api/snapshot` latest snapshot as JSON.

## Dashboard pages

`config/dashboard.yaml` (mounted read-only; the `dashboard` ConfigMap in Kubernetes) defines the pages and
widgets. Edits apply with no restart: on the next page load with a Compose bind mount, within about a minute
on Kubernetes while the ConfigMap propagates. A bad edit keeps the last good config and shows an error
banner. Collection interval and snapshot retention also live in this file (`collect`, `store`).

- Widgets: `stat_strip` (`stats`), `ranked_pools` (`metric`, `overlay`, `top`), `pool_table` (`columns`, `sort`).
- Metrics: `prov_gb` `used_gb` `mem_gb` `mem_act_gb` `vcpu` `cpu_busy` `vms`.
- Store: `file` only today. Snapshots are kept in `$DATA_DIR/snapshots`, newest plus `latest.json`, trimmed
  to `keep_snapshots`.

## Extend

- **New widget:** subclass `Widget` with `@register` in `collector/widgets.py`; it is then usable as
  `type: <name>`.
- **Database / time series:** subclass `Store` in `collector/store.py`, implement `save` and `series`, add
  it to `STORES`, set `store.type` in the config. Widgets receive the store as `ctx.store`.
- **Other data sources:** `collector/vsphere.py` returns a plain dict snapshot; add collectors beside it.

## Development

```sh
make test     # unit tests, no vCenter needed
make build    # docker build (PLATFORM defaults to linux/amd64)
make push     # docker push
make release  # test + build + push
```

Pushes to `main` (or tags `v*`) run GitHub Actions (`.github/workflows/docker-ghcr.yml`), which builds
`linux/amd64` and pushes `ghcr.io/bplein/vmware-collector:{<VERSION>, latest, sha-<git sha>}`. The package
is public, so pulls need no auth.

## Upgrading

`VERSION` is this image's version. The upstream package is pinned by `AIOPS_VERSION` in the Dockerfile.
Bump it by hand to pick up a new `vmware-aiops` release.
