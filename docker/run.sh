#!/bin/bash

IMAGE="aipyapp/aipy:latest"
DOCKER="docker run -v $(pwd)/aipy.toml:/app/aipy.toml -v $(pwd)/work:/app/work"

mkdir -p work

if [ "$1" = "--ttyd" ]; then
    ${DOCKER} -d --name aipy-ttyd -p 8080:80 $IMAGE --ttyd
else
    ${DOCKER} -it --rm --name aipy $IMAGE
fi
