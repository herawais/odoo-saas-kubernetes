from kubernetes import client, config

import logging
from odoo.addons.smile_log.tools import SmileDBLogger


def create_pv_claim(meta_data, specs, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)


    k8s_apps_v1 = client.CoreV1Api()

    dep = client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=meta_data,
        spec=specs
    )
    try:
        resp = k8s_apps_v1.create_namespaced_persistent_volume_claim(
            body=dep, namespace=namespace)
        _logger.info("Volume created. status='%s'" % resp.metadata.name)
    except client.exceptions.ApiException as e:
        _logger.error(msg=str(e))


def create_odoo_pv_claim(app_name, namespace="default", self=False):
    specs = client.V1PersistentVolumeClaimSpec(
        access_modes=[
            'ReadWriteOnce'
        ],
        storage_class_name="gp2",
        resources=client.V1ResourceRequirements(
            requests={
                'storage': '8Gi'
            }
        )
    )
    meta_data = client.V1ObjectMeta(
        name=app_name + "-odoo-web-pv-claim",
        labels={"app": app_name}
    )
    create_pv_claim(meta_data=meta_data, specs=specs, namespace=namespace, self=self)


def delete_odoo_pv_claim(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    claim_name = app_name + "-odoo-web-pv-claim"
    core_v1_api = client.CoreV1Api()

    try:
        pv = core_v1_api.delete_namespaced_persistent_volume_claim(name=claim_name, namespace=namespace)
        _logger.info(str(pv))
    except client.exceptions.ApiException as e:
        _logger.error(str(e))




