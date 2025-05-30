.PHONY: demo
demo:
	docker compose down || true
	docker compose up -d redis
	CUDA_VISIBLE_DEVICES="0" .venv/bin/python src/app.py

spaces:
	docker compose down || true
	docker compose up -d spaces

clear:
	sudo rm redis_data/dump.rdb || true

deploy_spaces_deployment: clear
	make demo &
	sleep 45
	docker compose down
# copy new data and code
	cp -r src/ spaces-deployment
	cp requirements.txt spaces-deployment/requirements.txt
	sudo cp redis_data/dump.rdb spaces-deployment/
	sudo chown manny:manny spaces-deployment/dump.rdb
# add to origin repo for automated deployment
	git add .
	git commit -m "push new db or demo version"
	git push origin main
