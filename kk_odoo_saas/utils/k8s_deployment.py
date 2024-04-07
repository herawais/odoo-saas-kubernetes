from kubernetes import config, client
import yaml
from kubernetes.stream import stream

from odoo.exceptions import UserError
from .odoo_components import deploy_odoo_components, delete_odoo_components, delete_odoo_components_from_options,\
    update_odoo_components
from .pg_server import delete_databases
from odoo.addons.smile_log.tools import SmileDBLogger
from .utils import generate_commit_sha

def create_deployment(app_name, config_file, self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    try:
        data2 = yaml.safe_load(config_file)
        config.load_kube_config_from_dict(data2)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")
    if app_name:
        deploy_odoo_components(app_name=app_name, namespace="default", self=self)
    else:
        _logger.error("Cant find App Name")
        raise UserError("Cant find App Name")


def delete_app_with_options(self, delete_db, delete_pv, delete_svc, delete_ing, delete_deployment):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    try:
        data = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")
    if self.app_name:
        delete_odoo_components_from_options(app_name=self.app_name, namespace="default", self=self, delete_db=delete_db,
                                            delete_pv=delete_pv, delete_svc=delete_svc,
                                            delete_ing=delete_ing, delete_deployment=delete_deployment)
        if delete_db:
            delete_databases(self)
    else:
        _logger.error("Cant find App Name")
        raise UserError("Cant find App Name")


def update_app(self):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    try:
        data = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")
    if self.app_name:
        update_odoo_components(app_name=self.app_name, namespace="default", self=self)
    else:
        _logger.error("Cant find App Name")
        raise UserError("Cant find App Name")


def fetch_secrets_from_cluster(self):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    try:
        data2 = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data2)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")

    secs = []
    if self.app_name:
        core_v1_api = client.CoreV1Api()
        secrs = core_v1_api.list_namespaced_secret(namespace='default')
        for sec in secrs.items:
            secs.append(sec.metadata.name)
    return secs


def deploy_apps_from_git(self):
    """
    To pull code from github inside running container
    """

    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    try:
        data2 = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data2)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")

    if self.app_name:
        core_v1_api = client.CoreV1Api()
        pod = core_v1_api.list_namespaced_pod(namespace='default', label_selector='app={}'.format(self.app_name))
        if self.is_extra_addon and self.extra_addons and pod and pod.items:
            base_version = self.docker_image.base_version
            clone_path = "/var/lib/odoo/addons/" + str(base_version)
            if self.is_private_repo and self.git_token:
                url = self.extra_addons
                url = url.replace("http://", "")
                url = url.replace("https://", "")
                url = url.replace("www.", "")
                git_url = "https://oauth2:{0}@{1}".format(self.git_token, url)
            else:
                git_url = self.extra_addons
            is_clone_error = False
            error = ''
            exec_command = ['git', '-C', clone_path, 'pull']
            resp = stream(core_v1_api.connect_get_namespaced_pod_exec,
                          pod.items[0].metadata.name,
                          'default',
                          command=exec_command,
                          stderr=True, stdin=True,
                          stdout=True, tty=False,
                          _preload_content=False)
            while resp.is_open():
                resp.update(timeout=10)
                if resp.peek_stdout():
                    _logger.info(str(resp.read_stdout()))
                if resp.peek_stderr():
                    is_clone_error = True
                    error = resp.read_stderr()
                    _logger.error(str(error))
                    break
            resp.close()

            if is_clone_error:
                if error and "not a git repository (or any" in error:
                    resp1 = stream(core_v1_api.connect_get_namespaced_pod_exec,
                                  pod.items[0].metadata.name,
                                  'default',
                                  command=['chmod', '-R', 'ugo+rw', clone_path],
                                  stderr=True, stdin=False,
                                  stdout=True, tty=False,
                                  _preload_content=False)
                    resp = stream(core_v1_api.connect_get_namespaced_pod_exec,
                                  pod.items[0].metadata.name,
                                  'default',
                                  command=['git', 'clone', git_url, clone_path],
                                  stderr=True, stdin=False,
                                  stdout=True, tty=False,
                                  _preload_content=False)
                    while resp.is_open():
                        resp.update(timeout=25)
                        if resp.peek_stdout():
                            _logger.info(str(resp.read_stdout()))
                        if resp.peek_stderr():
                            error = resp.read_stderr()
                            _logger.error(str(error))
                        else:
                            _logger.info(str(
                                "No Response"
                            ))
                    resp.close()
        else:
            return False


def restart_odoo_service(self):


    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    try:
        data2 = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data2)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")

    if self.app_name:
        core_v1_api = client.CoreV1Api()
        pod = core_v1_api.list_namespaced_pod(namespace='default', label_selector='app={}'.format(self.app_name))
        exec_command = ['./mnt/restart_odoo.sh']
        resp = stream(core_v1_api.connect_get_namespaced_pod_exec,
                      pod.items[0].metadata.name,
                      'default',
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False,
                      _preload_content=False)
        while resp.is_open():
            resp.update(timeout=10)
            if resp.peek_stdout():
                _logger.info(str(resp.read_stdout()))
            if resp.peek_stderr():
                error = resp.read_stderr()
                _logger.error(str(error))
                break
        resp.close()


def read_deployment(self, dep_type='odoo'):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    try:
        data = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")
    if self.app_name:
        dep_name = self.app_name + "-odoo-deployment"
        core_v1_api = client.AppsV1Api()

        try:
            deployment = core_v1_api.read_namespaced_deployment(name=dep_name, namespace='default')
            if deployment:
                return deployment
            return
        except Exception as e:
            pass
    else:
        _logger.error("Cant find App Name")
        raise UserError("Cant find App Name")


def update_deployment(self, container_arguments, dep_type='odoo', env_vars=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    try:
        data = yaml.safe_load(self.configuration.config_file)
        config.load_kube_config_from_dict(data)
    except config.config_exception.ConfigException as e:
        _logger.error(str(e))
        raise UserError("Unable to Connect K8s Cluster")
    if self.app_name:
        core_v1_api = client.AppsV1Api()
        try:
            deployment = read_deployment(self=self)
            if container_arguments:
                deployment.spec.template.spec.containers[0].args = eval(container_arguments)
            if env_vars:
                deployment.spec.template.spec.containers[0].env = env_vars
            deployment.spec.template.metadata.labels['COMMIT_SHA'] = generate_commit_sha(10)

            patched_deployment = core_v1_api.patch_namespaced_deployment(name=deployment.metadata.name,
                                                                         namespace='default',
                                                                         body=deployment)
            return patched_deployment
        except Exception as e:
            _logger.error(str(e))
    else:
        _logger.error("Cant find App Name")
        raise UserError("Cant find App Name")
