# kubernetes-deploy-monolith
A script to deploy monolith to kubernetes. Designed to run as a kubernetes job.

## Required Environment Variables
* $GOOGLE_APPLICATION_CREDENTIALS - Path to gcloud authentication json key file
* $SLACK_TOKEN - For slack notifications
* $APP_ENV - App environment (production, development)
* $HOSTNAME - Host running this process (provided by Kubernetes)
* DATABASE_INSTANCE_NAME - Cloud SQL instance name
* DATABASE_NAME - Database name
* DATABASE_BACKUP_BUCKET - GS bucket URI (gs://...)

## Required Arguments
* -i, --image - The new monolith image to roll out
* -m, --migration - The migration level: 0=None, 1=Hot, 2=Cold
