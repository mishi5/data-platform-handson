PROJECT_ID   := data-platform-handson-1223
REGION       := asia-northeast1
IMAGE        := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/news-collector/news-collector:latest
SERVICE_NAME := news-collector

.PHONY: deploy build push update

deploy: build push update

build:
	docker build --platform linux/amd64 \
	  -t $(IMAGE) \
	  collector

push:
	docker push $(IMAGE)

update:
	gcloud run services update $(SERVICE_NAME) \
	  --image=$(IMAGE) \
	  --region=$(REGION) \
	  --project=$(PROJECT_ID)
