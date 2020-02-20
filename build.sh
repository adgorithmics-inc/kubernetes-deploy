#!/usr/bin/env sh
set -e

# Takes image build tag from script argument or generates from date and short sha
TAG_ARG=$1
BUILD_TAG=${TAG_ARG:-$(utils/get_build_tag.sh)}
BASE_IMAGE=gcr.io/sonic-wavelet-124006/kubernetes-deploy

TAG=$BASE_IMAGE:$BUILD_TAG
LATEST_TAG=$BASE_IMAGE:latest

docker build . --tag=$TAG --tag=$LATEST_TAG
docker push $TAG
docker push $LATEST_TAG

echo "IMAGE PUSHED $TAG"
