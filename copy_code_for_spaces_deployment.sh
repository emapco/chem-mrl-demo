#!/bin/bash

cp -r src/ spaces-deployment
cp requirements.txt spaces-deployment/requirements.txt
sudo cp redis_data/dump.rdb spaces-deployment/
sudo chown manny:manny spaces-deployment/dump.rdb