#!/bin/bash
set -e

# Takes image build tag from script argument or generates from date and short sha
TAG_ARG=$1
BUILD_TAG=${TAG_ARG:-$(utils/get_build_tag.sh)}
BASE_IMAGE=$GCLOUD_PROJECT/kubernetes-deploy

if [ "${BOOTLEG}" = 'true' ]; then
    random=$(
        head /dev/urandom | tr -dc A-Za-z0-9 | head -c 13
        echo ''
    )
    prefix="bootleg-$random-"
    TAG=$BASE_IMAGE:$prefix$BUILD_TAG
    docker build . --tag=$TAG
    docker push "$TAG"
    echo "BOOTLEG IMAGE PUSHED: $TAG"
else
    LATEST_TAG=$BASE_IMAGE:latest
    TAG=$BASE_IMAGE:$BUILD_TAG
    docker build . --tag=$TAG --tag=$LATEST_TAG
    docker push "$TAG"
    docker push $LATEST_TAG
    echo "IMAGE PUSHED: $TAG"
fi
