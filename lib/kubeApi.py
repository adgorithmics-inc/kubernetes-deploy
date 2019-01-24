import logging
import time
from kubernetes import client, config
from typing import List

log = logging.getLogger(__name__)
config.load_incluster_config()
TIMEOUT_SECONDS = 180


class KubeApi:
    """
    Wrapper for kubernetes client
    """

    def __init__(self, namespace: str):
        self.appsV1Api = client.AppsV1Api()
        self.coreV1Api = client.CoreV1Api()
        self.namespace = namespace

    def get_deployments(self, label_selector: str) -> List[dict]:
        log.debug('Getting deployments: label_selector={}'.format(label_selector))
        deployments = []
        response = self.appsV1Api.list_namespaced_deployment(self.namespace, label_selector=label_selector)

        for deployment in response.items:
            deployments.append({
                'name': deployment.metadata.name,
                'image': deployment.spec.template.spec.containers[0].image,
                'replicas': deployment.status.replicas,
            })
        log.debug('Finished getting deployments: label_selector={}'.format(label_selector))
        return deployments

    def update_deployment(self, deployment: str, update: dict):
        log.debug('Updating deployment: deployment={} update={}'.format(deployment, update))
        self.appsV1Api.patch_namespaced_deployment_scale(deployment, self.namespace, update)
        self.verify_deployment_update(deployment)
        log.debug('Finished updating deployment: deployment={} update={}'.format(deployment, update))

    def set_deployment_replicas(self, deployment: str, replicas: int):
        update = {
            'spec': {
                'replicas': replicas
            }
        }
        self.update_deployment(deployment, update)

    def set_deployment_image(self,  deployment: str, image: int):
        update = {
            'spec': {
                'template': {
                    'spec': {
                        'containers[0]': {
                            'image': image
                        }
                    }
                }
            }
        }
        self.update_deployment(deployment, update)

    def verify_deployment_update(self, deployment: str):
        self.verify_pod_updates_complete(deployment)
        self.verify_pod_terminations_complete(deployment)

    def verify_pod_updates_complete(self, deployment: str):
        log.debug('Verifying pod updates completion: deployment={}'.format(deployment))
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while (time.time() < timeout_time and still_updating):
            log.debug('Checking deployment replica status: deployment={}'.format(deployment))
            result = self.appsV1Api.read_namespaced_deployment(deployment, self.namespace)
            status = result.status
            desired_replicas = status.replicas
            all_pods_updated = desired_replicas == status.updated_replicas
            all_pods_available = desired_replicas == status.available_replicas
            no_pods_unavailable = status.unavailable_replicas is None
            still_updating = not (all_pods_updated and all_pods_available and no_pods_unavailable)
            if (still_updating):
                time.sleep(1)

        if (still_updating):
            raise Exception('Deployment Update Timeout Exceeded')

    def verify_pod_terminations_complete(self, deployment: str):
        log.debug('Verifying pod terminations completion: deployment={}'.format(deployment))
        timeout_time = time.time() + TIMEOUT_SECONDS
        still_updating = True
        while (time.time() < timeout_time and still_updating):
            log.debug('Checking deployment pod status: deployment={}'.format(deployment))
            result = self.coreV1Api.list_namespaced_pod(self.namespace, label_selector='app={}'.format(deployment))
            still_updating = not all(pod.metadata.deletion_timestamp is None for pod in result.items)
            if (still_updating):
                time.sleep(1)

        if (still_updating):
            raise Exception('Pod Termination Timeout Exceeded')
