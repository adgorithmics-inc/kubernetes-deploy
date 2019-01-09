# kubernetes-deploy

A script to deploy projects to kubernetes. Designed to run as a kubernetes job.

## Setup
1. Give all of your deployements the same PROJECT label as well as a fitting TIER label. Every deployment (and cronjob) with the PROJECT label will be updated in the deployment. The TIER label will determine the order in which to scale down, update, scale up deployments in the case of a cold database migration. Deployments can use different images, but they must all use the same TAG. See `Features` and `Optional` env variables below for more details.

## Features
-   Migration Job - If you would like to trigger database migrations, setup a command with on one of your deployment images that can be used to run the database migration process. Provide this deployment name as APP_MIGRATOR_SOURCE env variable as well as pass the command and args via APP_MIGRATOR_COMMAND and APP_MIGRATOR_ARGS env variables. You will also need to define the DATABASE_* env variables to perform the necessary backup to Google Storage. If the `migration` option is set to `1` (hot migration - no scale down), or `2` (cold migration - scale down and up deployments) then the deployment script will first backup the database, scale down deployments (if cold migration), fetch the APP_MIGRATOR_SOURCE deployment and update the image tag, command and args, run the migration, update all other deployment images, scale back up deployments (if cold migration).
-   Trello list cleanup - If you pass the necessary trello and mailgun env variables (with TRELLO_SEND_NOTIFICATION flag is True) the deployment script will collect all cards in the trello list, send out a notification email with their details, and archive the cards.
-   Cronjob support - If you give cronjobs the same PROJECT label, they will also be updated in the final stage of the deployment.

## Environment Variables

### Required

-   SLACK_TOKEN - For slack notifications
-   PROJECT - Matches the `project` label on the deployments

### Required if performing migrations (`migration` option set above 0)
-   DATABASE_INSTANCE_NAME - Cloud SQL instance name
-   DATABASE_NAME - Cloud SQL database name
-   DATABASE_BACKUP_BUCKET - GS URI (gs://bucket/directory/etc) database backup location (will append `/PROJECT`)
-   APP_MIGRATOR_SOURCE - The name of the deployment to use as the base configuration for migration jobs

### Required if TRELLO_SEND_NOTIFICATION flag is True

-   TRELLO_KEY - Trello api key
-   TRELLO_TOKEN - Trello api token
-   TRELLO_LIST_ID - Target trello list for release notification generation
-   MAILGUN_DOMAIN - Mailgun domain
-   MAILGUN_KEY - Mailgun api key
-   MAILGUN_TO - Recipients for release notification email

### Optional (with defaults for development cinnamon deployment)

-   GOOGLE_APPLICATION_CREDENTIALS - Path to gcloud authentication json key file. Not needed if you have local gcloud auth initialized
-   DEBUG [`False`] - Will authorize kubeApi with local gcloud when `True`
-   DISABLED [`False`] - Exits process without deploying when `True`
-   APP_ENV [`development`] - App environment (production, development) to construct slack notification
-   HOSTNAME [`localhost`] - Host running this process (provided by Kubernetes)
-   NAMESPACE [`default`] - Pod namespace
-   SLACK_CHANNEL [`dev-null`] - Target channel for slack notifications
-   TIERS [`frontend,scheduler,worker,gateway,apiserver`] - Comma separated list of deployments (in scale down order)
-   TRELLO_SEND_NOTIFICATION [`False`] - Cleanup trello list and send release notification via email
-   APP_MIGRATOR_COMMAND = [`npm`] - A comma separated list of commands to on the migration job container
-   APP_MIGRATOR_ARGS = [`run,--prefix,/app,migration:run`] - A comma separated list of args to set on the migration job container

## Required Arguments

-   -t, --tag - The new monolith image tag to roll out (`dev-20.02.18-36b17ee`)
-   -m, --migration - The migration level: 0=None, 1=Hot, 2=Cold

## Running Locally

Just add all of the necessary env variables and run `deploy.py` and pass the tag and migration options.

-   `pip install -r requirements.txt`
-   `SLACK_TOKEN=<token> PROJECT=<your project> DEBUG=True python deploy.py --tag=<image tag> --migration=<migration level (0, 1, 2)>`
