import os

SLACK_TOKEN = os.getenv('SLACK_TOKEN')
CLUSTER_NAME = os.getenv('GCLOUD_CLUSTER_NAME')
HOST_NAME = os.getenv('HOSTNAME')
NAMESPACE = 'default'
DEPLOYMENT_GROUP = 'monolith'
