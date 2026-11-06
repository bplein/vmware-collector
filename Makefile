REGISTRY ?= ghcr.io/bplein/vmware-collector
VERSION  := $(shell cat VERSION)
PLATFORM ?= linux/amd64

# Release flow: bump VERSION, `make sync-manifests`, commit, `git tag v<VERSION>`, push.
# Images build in GitHub Actions on push; local docker build/push stays available for
# quick iteration but isn't the release path.
.PHONY: build push release test sync-manifests
test:
	python -m unittest discover -s tests
build:
	docker build --provenance=false --sbom=false --platform $(PLATFORM) -t $(REGISTRY):$(VERSION) -t $(REGISTRY):latest .
push:
	docker push $(REGISTRY):$(VERSION)
	docker push $(REGISTRY):latest
release: test build push
sync-manifests:
	sed -i '' -E "s|$(REGISTRY):[^\" ]+|$(REGISTRY):$(VERSION)|g" deploy/k8s/vmware-collector.yaml
	@echo "pinned at $(VERSION)"
