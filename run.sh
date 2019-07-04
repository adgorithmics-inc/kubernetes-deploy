#!/bin/bash
set -e

gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
python deploy.py "$@"
