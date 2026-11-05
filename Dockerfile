# Layered on the vmware-aiops image so pyVmomi and vmware_aiops are already present.
# Bump BASE_VERSION (Dependabot does this) to pick up a new upstream release.
ARG BASE_VERSION=2.4.2
FROM ghcr.io/bplein/vmware-aiops:${BASE_VERSION}
WORKDIR /app
COPY collector/ collector/
COPY config/dashboard.yaml /config/dashboard.yaml
ENV DASHBOARD_CONFIG=/config/dashboard.yaml \
    VMWARE_AIOPS_CONFIG=/root/.vmware-aiops/config.yaml \
    DATA_DIR=/data \
    PORT=8080
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/healthz'%os.environ.get('PORT','8080'))"
ENTRYPOINT ["python", "-m", "collector"]
