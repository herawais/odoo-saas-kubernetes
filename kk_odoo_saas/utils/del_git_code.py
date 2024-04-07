from kubernetes import config, client
from kubernetes.stream import stream
from odoo.addons.smile_log.tools import SmileDBLogger
from odoo.exceptions import UserError
import yaml


# import git_aggregator

def del_git_dir(self, path):
    """
    It will delete addons directory inside running container
    """
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    if self.app_name and path:
        try:
            data2 = yaml.safe_load(self.configuration.config_file)
            config.load_kube_config_from_dict(data2)
        except config.config_exception.ConfigException as e:
            _logger.error(str(e))
            raise UserError("Unable to Connect K8s Cluster")
        core_v1_api = client.CoreV1Api()

        try:
            pod = core_v1_api.list_namespaced_pod(namespace='default', label_selector='app={}'.format(self.app_name))
        except Exception as e:
            raise UserError("Unable to connect to cluster")
        resp1 = stream(core_v1_api.connect_get_namespaced_pod_exec,
                       pod.items[0].metadata.name,
                       'default',
                       command=['chmod', '-R', 'ugo+rw', path],
                       stderr=True, stdin=False,
                       stdout=True, tty=False)

        resp = stream(core_v1_api.connect_get_namespaced_pod_exec,
                      pod.items[0].metadata.name,
                      'default',
                      command=['rm', '-rf', path ],
                      stderr=True, stdin=False,
                      stdout=True, tty=False)

        resp3 = stream(core_v1_api.connect_get_namespaced_pod_exec,
                      pod.items[0].metadata.name,
                      'default',
                      command=['mkdir', path ],
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        _logger.info(str(resp1))
        _logger.info(str(resp))
        _logger.info(str(resp3))
        _logger.info(str(path))
        _logger.info(str("code deleted"))
