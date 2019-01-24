# kubernetes-deploy-monolith
A script to deploy monolith to kubernetes. Designed to run as a kubernetes job.

## Required Environment Variables
* $GOOGLE_APPLICATION_CREDENTIALS - Path to gcloud authentication json key file
* $SLACK_TOKEN - For slack notifications
* $GCLOUD_CLUSTER_NAME - The production or development cluster name (prod-cluster, dev-cluster)
* $HOSTNAME - Host running this process (provided by Kubernetes)

## Required Arguments
* -i, --image - The new monolith image to roll out
* -m, --migration - The migration level: 0=None, 1=Hot, 2=Cold
