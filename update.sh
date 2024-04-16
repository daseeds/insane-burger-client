#! /bin/sh

git reset --hard
git pull
docker compose up --build -d