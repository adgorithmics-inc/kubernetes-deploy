import os

# -------- ENV --------
#  Debug will authorize kube api with local gcloud auth when True
DEBUG = os.getenv("DEBUG", False) in ["true", "True"]
DISABLED = os.getenv("DISABLED", False) in ["true", "True"]
# Determines the slack notification info
APP_ENV = os.getenv("APP_ENV", "development")

# -------- Project, Pod, Cluster --------
PROJECT = os.getenv("PROJECT", "cinnamon")
HOST_NAME = os.getenv("HOSTNAME", "localhost")
NAMESPACE = os.getenv("NAMESPACE", "default")

# -------- Slack --------
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "dev-null")

# -------- Database backup --------
DATABASE_INSTANCE_NAME = os.getenv("DATABASE_INSTANCE_NAME", "dev-sql")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cinnamon")
DATABASE_BACKUP_BUCKET = f"{os.getenv('DATABASE_BACKUP_BUCKET', 'gs://developers-adgo-io/backups/postgresql')}/{DATABASE_NAME}"

# -------- Migrate job --------
APP_MIGRATOR_SOURCE = os.getenv("APP_MIGRATOR_SOURCE", "gql-server-private")
# comma separated list
APP_MIGRATOR_COMMAND = os.getenv("APP_MIGRATOR_COMMAND", "npm").split(",")
# comma separated list
APP_MIGRATOR_ARGS = os.getenv(
    "APP_MIGRATOR_ARGS", "run,--prefix,/app,migration:run"
).split(",")

# -------- Deployment Tiers --------
# comma separated listed in scale down order
TIERS = os.getenv("TIERS", "frontend,scheduler,worker,gateway,apiserver").split(",")
# frontend - public facing frontend
# scheduler - service scheduler
# worker - service queue workers
# gateway - public facing api gateway
# apiserver - service apiserver / internal gateway
