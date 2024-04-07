from kubernetes import config, client
import yaml
from kubernetes.client.rest import ApiException
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


def read_logs(app_name, self=False, config_file=None, since_seconds=None, previous=False, tail_lines=None):
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    try:
        data2 = yaml.safe_load(config_file)
        config.load_kube_config_from_dict(data2)

    except config.config_exception.ConfigException as e:
        raise UserError("Unable to Connect K8s Cluster")

    try:
        api_instance = client.CoreV1Api()
        odoo_pods = api_instance.list_namespaced_pod(namespace='default',
                                                     label_selector='app={0},tier={1}'.format(str(self.app_name),
                                                                                              'backend'))
        for pod in odoo_pods.items:
            if pod.metadata and pod.metadata.name and (self.app_name + '-odoo-deployment' in pod.metadata.name):
                odoo_logs = api_instance.read_namespaced_pod_log(name=pod.metadata.name, namespace='default',
                                                                 tail_lines=tail_lines, since_seconds=since_seconds)
                return odoo_logs
        return False
    except ApiException as e:
        _logger.error(e)
        return False
