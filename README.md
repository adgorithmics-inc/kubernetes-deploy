# kubernetes-deploy-monolith

A script to deploy monolith to kubernetes. Designed to run as a kubernetes job.

## Environment Variables

### Required

-   SLACK_TOKEN - For slack notifications

### Optional (with defaults for development cinnamon deployment)

-   GOOGLE_APPLICATION_CREDENTIALS - Path to gcloud authentication json key file. Not needed if you have local gcloud auth initialized
-   DEBUG [`False`] - Will authorize kubeApi with local gcloud when `True`
-   DISABLED [`False`] - Exits process without deploying when `True`
-   APP_ENV [`development`] - App environment (production, development) to construct slack notification
-   PROJECT [`cinnamon`] - Matches the `project` label on the deployments (cinnamon, monolith, services)
-   HOSTNAME [`localhost`] - Host running this process (provided by Kubernetes)
-   NAMESPACE [`default`] - Pod namespace
-   SLACK_CHANNEL [`dev-null`] - Target channel for slack notifications
-   DATABASE_INSTANCE_NAME [`dev-sql`] - Cloud SQL instance name
-   DATABASE_NAME [`cinnamon`] - Cloud SQL database name
-   DATABASE_BACKUP_BUCKET [`gs://developers-adgo-io/backups/postgresql`] - GS database backup location (will append `/PROJECT`)
-   APP_MIGRATOR_SOURCE [`gql-server-private`] - The name of the deployment to use as the base configuration for migration jobs
-   TIERS [`frontend,scheduler,worker,gateway,apiserver`] - Comma separated list of deployments (in scale down order)

## Required Arguments

-   -t, --tag - The new monolith image tag to roll out (`dev-20.02.18-36b17ee`)
-   -m, --migration - The migration level: 0=None, 1=Hot, 2=Cold

## Running Locally

The config defaults have all the necessary defaults to launch cinnamon on the dev cluster. Just add a few necessary env variables.

-   `pip install -r requirements.txt`
-   `SLACK_TOKEN=<token> DEBUG=True python deploy.py --tag=<image tag> --migration=<migration level (0, 1, 2)>`
