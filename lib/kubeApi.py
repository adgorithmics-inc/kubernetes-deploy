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
APP_MIGRATOR_SCRIPT = 'run-migrate.sh'


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
        log.debug("Getting deployments: label_selector={}".format(label_selector))
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
            "Finished getting deployments: label_selector={} deployments={}".format(
                label_selector, deployments
            )
        )
        return deployments

    def update_deployment(
        self, deployment: client.V1Deployment, verify_update: bool = True
    ):
        name = deployment.metadata.name
        log.debug(
            "Updating deployment: deployment={} update={}".format(name, deployment)
        )
        deployment = self.appsV1Api.patch_namespaced_deployment(
            name, self.namespace, deployment
        )
        if verify_update:
            self.verify_deployment_update(deployment)
        log.debug(
            "Finished updating deployment: deployment={} update={}".format(
                name, deployment
            )
        )

    def set_deployment_replicas(
        self, name: str, replicas: int, verify_update: bool = False
    ):
        deployment = self.appsV1Api.read_namespaced_deployment(name, self.namespace)
        deployment.spec.replicas = replicas
        self.update_deployment(deployment, verify_update)

    def set_deployment_image(self, name: str, image: int, verify_update: bool = False):
        deployment = self.appsV1Api.read_namespaced_deployment(name, self.namespace)
        deployment.spec.template.spec.containers[0].image = image
        self.update_deployment(deployment, verify_update)

    def verify_deployment_update(self, deployment: str):
        self.verify_pod_updates_complete(deployment)
        self.verify_pod_terminations_complete(deployment)

    def verify_pod_updates_complete(self, deployment: str):
        log.debug("Verifying pod updates complete: deployment={}".format(deployment))
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while time.time() < timeout_time and still_updating:
            log.debug(
                "Checking deployment replica status: deployment={}".format(deployment)
            )
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
                "Deployment Update Timeout Exceeded: deployment={}".format(deployment)
            )
        log.debug("Pod updates completed: deployment={}".format(deployment))

    def verify_pod_terminations_complete(self, deployment: str):
        log.debug(
            "Verifying pod terminations complete: deployment={}".format(deployment)
        )
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while time.time() < timeout_time and still_updating:
            log.debug(
                "Checking deployment pod status: deployment={}".format(deployment)
            )
            result = self.coreV1Api.list_namespaced_pod(
                self.namespace, label_selector="app={}".format(deployment)
            )
            still_updating = not all(
                pod.metadata.deletion_timestamp is None for pod in result.items
            )
            if still_updating:
                time.sleep(POLL_WAIT)

        if still_updating:
            raise Exception(
                "Pod Termination Timeout Exceeded: deployment={}".format(deployment)
            )
        log.debug("Pod terminations complete: deployment={}".format(deployment))

    def verify_job_not_in_progress(self, job: str):
        log.debug("Verifying jobs not in progress: job={}".format(job))
        result = self.coreV1Api.list_namespaced_pod(
            self.namespace,
            label_selector="app={}".format(job),
            field_selector="status.phase!=Succeeded,status.phase!=Failed",
        )
        if len(result.items) > 0:
            raise Exception(
                "Unable to perform migration. {} job already in progress".format(job)
            )
        log.debug("Verified job not in progress: job={}".format(job))

    def delete_job(self, job: str):
        log.debug("Deleting job: job={}".format(job))
        try:
            self.batchV1Api.delete_namespaced_job(
                job, self.namespace, body=client.V1DeleteOptions()
            )
        except client.rest.ApiException as e:
            if e.status != NOT_FOUND:
                raise Exception("Error deleting job: error={}".format(str(e)))
            log.debug("Unable to delete job that doesn't exist: job={}".format(job))
            return
        log.debug("Job deleted successfully: job={}".format(job))

    def generate_app_migrator_job(self, image: str, source: str):
        log.debug(
            "Generating app-migrator job: image={} source={}".format(image, source)
        )
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
        envs = job.spec.template.spec.containers[0].env
        new_command = ([env for env in envs if env.name == 'COMMAND'] or [None])[0]
        if new_command is None:
            envs.append(client.V1EnvVar(name='COMMAND', value=APP_MIGRATOR_SCRIPT))
        else:
            new_command.value = APP_MIGRATOR_SCRIPT
        self.batchV1Api.create_namespaced_job(self.namespace, job)
        log.debug(
            "Generation of app-migrator job complete: image={} source={}".format(
                image, source
            )
        )

    def verify_job_complete(self, job):
        log.debug("Verifying job completion: job={}".format(job))
        timeout_time = time.time() + TIMEOUT_SECONDS
        active = True
        succeeded = 0
        while time.time() < timeout_time and active:
            log.debug("Checking job status: job={}".format(job))
            result = self.batchV1Api.read_namespaced_job(job, self.namespace)
            active = result.status.active == 1
            succeeded = result.status.succeeded
            if active:
                time.sleep(POLL_WAIT)

        if active:
            raise Exception("Job Termination Timeout Exceeded: job={}".format(job))
        if succeeded == 0:
            raise Exception("Job Failed: job={}".format(job))
        log.debug("Job completed successfully: job={}".format(job))

    def run_migration(self, image: str, source: str):
        log.debug("Begin running migration: image={} source={}".format(image, source))
        self.verify_job_not_in_progress(APP_MIGRATOR)
        self.delete_job(APP_MIGRATOR)
        self.verify_pod_terminations_complete(APP_MIGRATOR)
        self.generate_app_migrator_job(image, source)
        self.verify_job_complete(APP_MIGRATOR)
        log.debug("Completed migration: image={} source={}".format(image, source))
