REGISTRY ?= ghcr.io/bplein/vmware-collector
VERSION  := $(shell cat VERSION)
PLATFORM ?= linux/amd64
.PHONY: build push release test
test:
	python -m unittest discover -s tests
build:
	docker build --provenance=false --sbom=false --platform $(PLATFORM) -t $(REGISTRY):$(VERSION) -t $(REGISTRY):latest .
push:
	docker push $(REGISTRY):$(VERSION)
	docker push $(REGISTRY):latest
release: test build push
