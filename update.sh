#! /bin/sh

cd /home/cjean/insane-burger-client
git reset --hard
git pull
docker compose up --build -d