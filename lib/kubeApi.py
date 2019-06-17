import logging
import time
from kubernetes import client, config
from typing import List

log = logging.getLogger(__name__)
config.load_incluster_config()
TIMEOUT_SECONDS = 300
POLL_WAIT = 15
NOT_FOUND = 404
APP_MIGRATOR = "app-migrator"


class KubeApi:
    """
    Wrapper for kubernetes client
    """

    def __init__(self, namespace: str):
        self.client = client
        self.appsV1Api = client.AppsV1Api()
        self.coreV1Api = client.CoreV1Api()
        self.batchV1Api = client.BatchV1Api()
        self.namespace = namespace

    def get_deployments(self, label_selector: str) -> List[dict]:
        log.debug(f"Getting deployments: label_selector={label_selector}")
        deployments = []
        response = self.appsV1Api.list_namespaced_deployment(
            self.namespace, label_selector=label_selector
        )

        for deployment in response.items:
            deployments.append(
                {
                    "name": deployment.metadata.name,
                    "image": deployment.spec.template.spec.containers[0].image,
                    "replicas": deployment.status.replicas,
                }
            )
        log.debug(
            f"Finished getting deployments: label_selector={label_selector} deployments={deployments}"
        )
        return deployments

    def update_deployment(
        self, deployment: str, update: dict, verify_update: bool = True
    ):
        log.debug(f"Updating deployment: deployment={deployment} update={update}")
        self.appsV1Api.patch_namespaced_deployment_scale(
            deployment, self.namespace, update
        )
        if verify_update:
            self.verify_deployment_update(deployment)
        log.debug(
            f"Finished updating deployment: deployment={deployment} update={update}"
        )

    def set_deployment_replicas(self, deployment: str, replicas: int):
        update = {"spec": {"replicas": replicas}}
        self.update_deployment(deployment, update)

    def set_deployment_image(
        self, deployment: str, image: int, verify_update: bool = False
    ):
        update = {"spec": {"template": {"spec": {"containers[0]": {"image": image}}}}}
        self.update_deployment(deployment, update, verify_update)

    def verify_deployment_update(self, deployment: str):
        self.verify_pod_updates_complete(deployment)
        self.verify_pod_terminations_complete(deployment)

    def verify_pod_updates_complete(self, deployment: str):
        log.debug(f"Verifying pod updates complete: deployment={deployment}")
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while time.time() < timeout_time and still_updating:
            log.debug(f"Checking deployment replica status: deployment={deployment}")
            result = self.appsV1Api.read_namespaced_deployment(
                deployment, self.namespace
            )
            status = result.status
            desired_replicas = status.replicas
            all_pods_updated = desired_replicas == status.updated_replicas
            all_pods_available = desired_replicas == status.available_replicas
            no_pods_unavailable = status.unavailable_replicas is None
            still_updating = not (
                all_pods_updated and all_pods_available and no_pods_unavailable
            )
            if still_updating:
                time.sleep(1)

        if still_updating:
            raise Exception(
                f"Deployment Update Timeout Exceeded: deployment={deployment}"
            )
        log.debug(f"Pod updates completed: deployment={deployment}")

    def verify_pod_terminations_complete(self, deployment: str):
        log.debug(f"Verifying pod terminations complete: deployment={deployment}")
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while time.time() < timeout_time and still_updating:
            log.debug(f"Checking deployment pod status: deployment={deployment}")
            result = self.coreV1Api.list_namespaced_pod(
                self.namespace, label_selector=f"app={deployment}"
            )
            still_updating = not all(
                pod.metadata.deletion_timestamp is None for pod in result.items
            )
            if still_updating:
                time.sleep(POLL_WAIT)

        if still_updating:
            raise Exception(
                f"Pod Termination Timeout Exceeded: deployment={deployment}"
            )
        log.debug(f"Pod terminations complete: deployment={deployment}")

    def verify_job_not_in_progress(self, job: str):
        log.debug(f"Verifying jobs not in progress: job={job}")
        result = self.coreV1Api.list_namespaced_pod(
            self.namepsace,
            label_selector=f"app={job}",
            field_selector="status.phase!=Succeeded,status.phase!=Failed",
        )
        if len(result.items) > 0:
            raise Exception(
                f"Unable to perform migration. {job} job already in progress"
            )
        log.debug(f"Verified job not in progress: job={job}")

    def delete_job(self, job: str):
        log.debug(f"Deleting job: job={job}")
        try:
            self.batchV1Api.delete_namespaced_job(
                job, self.namespace, body=client.V1DeleteOptions()
            )
        except client.rest.ApiException as e:
            if e.code != NOT_FOUND:
                raise Exception(f"Error deleting job: error={str(e)}")
            log.debug(f"Unable to delete job that doesn't exist: job={job}")
        log.debug(f"Job deleted successfully: job={job}")

    def generate_app_migrator_job(self, image: str, source: str):
        log.debug(f"Generating app-migrator job: image={image} source={source}")
        deployment = self.appsV1Api.read_namespaced_deployment(source, self.namespace)
        metadata = client.V1ObjectMeta(
            labels={"app": APP_MIGRATOR}, name=APP_MIGRATOR, namespace=self.namespace
        )
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=deployment.spec.template.spec, metadata=metadata
                )
            ),
        )
        job.spec.template.spec.containers[0].image = image
        job.spec.template.spec.restart_policy = "Never"
        job.spec.template.spec.containers[0].command = [
            "/opt/adgo-app/manage.py",
            "migrate",
            "--no-input",
        ]
        self.batchV1Api.create_namespaced_job(self.namespace, job)
        log.debug(
            f"Generation of app-migrator job complete: image={image} source={source}"
        )

    def verify_job_complete(self, job):
        log.debug(f"Verifying job completion: job={job}")
        timeout_time = time.time() + TIMEOUT_SECONDS
        active = True
        succeeded = 0
        while time.time() < timeout_time and active:
            log.debug(f"Checking job status: job={job}")
            result = self.batchV1Api.read_namespaced_job(job, self.namespace)
            active = result.status.active == 1
            succeeded = result.status.succeeded
            if active:
                time.sleep(POLL_WAIT)

        if active:
            raise Exception(f"Job Termination Timeout Exceeded: job={job}")
        if succeeded == 0:
            raise Exception(f"Job Failed: job={job}")
        log.debug(f"Job completed successfully: job={job}")

    def run_migration(self, image: str, source: str):
        log.debug(f"Begin running migration: image={image} source={source}")
        self.verify_job_not_in_progress(APP_MIGRATOR)
        self.delete_job(APP_MIGRATOR)
        self.generate_app_migrator_job(image, source)
        self.verify_job_complete(APP_MIGRATOR)
        log.debug(f"Completed migration: image={image} source={source}")
