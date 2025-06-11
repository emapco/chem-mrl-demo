.PHONY: demo
demo:
	docker compose down || true
	docker compose up -d redis
# run locally so gradio share link functionality works
	CUDA_VISIBLE_DEVICES="0" .venv/bin/python src/app.py

# hf spaces free-tier build process times-out when creating the redis index
# thus we precompute index and deploy the redis dump
.PHONY: deploy_spaces_deployment clean gen_new_embed_index copy_changes
deploy_spaces_deployment: clean gen_new_embed_index copy_changes
# add to hf repo for automated deployment
	cd spaces-deployment && git add . && \
	git commit -m "push new db or demo version" && \
	git push origin main

clean:
	docker compose down || true
	sudo rm redis_data/dump.rdb || true

gen_new_embed_index:
	docker compose up -d redis
#	workaround to kill background process
	CUDA_VISIBLE_DEVICES="0" .venv/bin/python src/app.py & \
	APP_PID=$$! && \
	sleep 420 && \
	kill $$APP_PID || true
	docker compose down

CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)
copy_changes:
	cp -r src/ spaces-deployment
	cp requirements.txt spaces-deployment
	cp HF.Dockerfile spaces-deployment/Dockerfile
	sudo chown ${CURRENT_UID}:${CURRENT_UID} redis_data/dump.rdb
	cp redis_data/dump.rdb spaces-deployment
