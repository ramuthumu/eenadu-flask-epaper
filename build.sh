#!/bin/bash

version="latest"

docker buildx build --platform=linux/amd64 -t ramuthumu/eenadu-epaper:$version .
docker buildx build --platform=linux/arm64 -t ramuthumu/eenadu-epaper:$version .

docker push ramuthumu/eenadu-epaper:$version
