"""Read-only vCenter collection: per-resource-pool VM capacity, memory and CPU."""
import datetime, os
from pyVmomi import vim

GB = 1024 ** 3


def _vm(vm):
    try:
        s, hw, q = vm.storage, vm.config.hardware, vm.summary.quickStats
        comm = sum(u.committed for u in s.perDatastoreUsage) / GB
        unc = sum(u.uncommitted for u in s.perDatastoreUsage) / GB
        return dict(vm=vm.name, on=str(vm.runtime.powerState) == "poweredOn", tpl=bool(vm.config.template),
                    used_gb=comm, prov_gb=comm + unc, mem_gb=hw.memoryMB / 1024, vcpu=hw.numCPU,
                    mem_act_gb=(q.hostMemoryUsage or 0) / 1024, cpu_mhz=(q.overallCpuUsage or 0))
    except Exception:
        return None


def collect(target=None):
    from pyVim.connect import Disconnect
    from vmware_aiops.config import load_config
    from vmware_aiops.connection import ConnectionManager
    path = os.environ.get("VMWARE_AIOPS_CONFIG")
    si = ConnectionManager(load_config(path and __import__("pathlib").Path(path))).connect(target)
    try:
        c = si.RetrieveContent()
        pools = []
        v = c.viewManager.CreateContainerView(c.rootFolder, [vim.ResourcePool], True)
        for rp in v.view:
            if isinstance(rp.parent, vim.ClusterComputeResource):
                continue  # hidden cluster root pool
            pools.append(dict(name=rp.name, vms=[x for x in map(_vm, rp.vm) if x]))
        v.Destroy()
        root = []
        v = c.viewManager.CreateContainerView(c.rootFolder, [vim.ClusterComputeResource], True)
        for cl in v.view:
            root += [x for x in map(_vm, cl.resourcePool.vm) if x]
        v.Destroy()
        return dict(collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    source=si._stub.host if hasattr(si, "_stub") else "", pools=pools, root_vms=root)
    finally:
        Disconnect(si)
