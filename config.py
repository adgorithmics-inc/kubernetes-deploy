import os

DISABLED = os.getenv("DISABLED", False) in ["true", "True"]
APP_ENV = os.getenv("APP_ENV")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
DATABASE_INSTANCE_NAME = os.getenv("DATABASE_INSTANCE_NAME")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_BACKUP_BUCKET = os.getenv("DATABASE_BACKUP_BUCKET")
HOST_NAME = os.getenv("HOSTNAME")
NAMESPACE = "default"
DEPLOYMENT_GROUP = "monolith"
