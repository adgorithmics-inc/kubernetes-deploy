import logging
from kubernetes import client, config
from typing import List, Tuple

log = logging.getLogger(__name__)
# config.load_incluster_config()
config.load_kube_config()


class KubeApi:
    """
    Wrapper for kubernetes client
    """

    def __init__(self, namespace: str, deployment_group: str):
        self.appsApiClient = client.AppsV1Api()
        self.extensionsApiClient = client.ExtensionsV1beta1Api()
        self.namespace = namespace

    def get_deployments(self, label_selector: str):
        deployments = {}
        response = self.client.list_namespaced_deployment(self.namespace, label_selector=label_selector)

        for deployment in response.items:
            deployments[deployment.metadata.name] = {
                'image': deployment.spec.template.spec.containers[0].image,
                'replicas': deployment.status.replicas,
            }
        return deployments

    def scale_down_deployments(self, deployments: List[str]):
        print('Scale Down {}'.format(deployments))

    def scale_up_deployments(self, deployments: List[str]):
        print('Scale Up {}'.format(deployments))

    def set_deployment_images(self, deployments: List[Tuple(str, str)]):
        print('Set Images {}'.format(deployments))
