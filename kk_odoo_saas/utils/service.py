from kubernetes import client, config
import random
from urllib.parse import urlparse
import logging

_logger = logging.getLogger(__name__)
from odoo.addons.smile_log.tools import SmileDBLogger


def create_service(specs, metadata, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    core_v1_api = client.CoreV1Api()
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=metadata,
        spec=specs
    )
    # Creation of the Deployment in specified namespace
    try:
        service = core_v1_api.create_namespaced_service(namespace=namespace, body=body)
        _logger.info("Service created. status='%s'" % service.metadata.name)

    except client.exceptions.ApiException as e:
        _logger.error(str(e))




def create_odoo_service(app_name, namespace, self=False):
    service_name = app_name + "-odoo-service"
    specs = client.V1ServiceSpec(
        selector={"app": app_name, "tier": "backend"},
        ports=[client.V1ServicePort(
            name='odoo-port',
            protocol="TCP",
            port=80,
            target_port=8069,
        ),
            client.V1ServicePort(
                name='longpolling',
                protocol="TCP",
                port=8072,
                target_port=8072,
            )
        ],
        type="NodePort"
    )
    metadata = client.V1ObjectMeta(
        name=service_name,
        labels={"app": app_name}
    )
    create_service(metadata=metadata, specs=specs, namespace=namespace, self=self)


def delete_odoo_service(app_name, namespace, self=False):
    service_name = app_name + "-odoo-service"
    core_v1_api = client.CoreV1Api()

    try:
        service = core_v1_api.delete_namespaced_service(name=service_name, namespace=namespace)
        _logger.info(service)

    except client.exceptions.ApiException as e:
        _logger.error(str(e))



