from kubernetes import client
from odoo.addons.smile_log.tools import SmileDBLogger
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


def create_deployment(meta_data, specs, namespace="default", self=False):
    # Deployment
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=meta_data,
        spec=specs)
    k8s_apps_v1 = client.AppsV1Api()
    try:
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=deployment, namespace=namespace)
        _logger.info("Deployment created. name='%s'" % resp.metadata.name)
    except client.exceptions.ApiException as e:
        _logger.error(str(e))


def create_docker_repo_secret(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    k8s_apps_v1 = client.CoreV1Api()
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name=app_name+'-dkr-registry-key',
            labels={
                "app": app_name,
                "tier": "backend"
            }
        ),
        data={
            '.dockerconfigjson': self.docker_image.b64_dkr_config
        },
        type='kubernetes.io/dockerconfigjson',
    )
    try:
        resp = k8s_apps_v1.create_namespaced_secret(
            body=secret, namespace=namespace)
        _logger.info("Secret created. name='%s'" % resp.metadata.name)
        return True
    except client.exceptions.ApiException as e:
        _logger.error(str(e))
    return False


def delete_docker_repo_secret(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    k8s_apps_v1 = client.CoreV1Api()
    try:
        resp = k8s_apps_v1.delete_namespaced_secret(app_name+'-dkr-registry-key', namespace=namespace)
        _logger.info(str(resp))
        return True
    except client.exceptions.ApiException as e:
        _logger.error(str(e))
    return False


def create_odoo_deployment(app_name, namespace="default", self=False):
    image = 'odoo:15.0'
    res_limits = {'ephemeral-storage': '1Gi'}

    image_pull_secrets = []
    if self.is_custom_image and self.docker_image:
        image = "{0}:{1}".format(self.docker_image.name, self.docker_image.tag)
        if self.docker_image.is_pvt_dkr_repo and self.docker_image.b64_dkr_config:
            if create_docker_repo_secret(app_name, namespace, self):
                sec_name = app_name+"-dkr-registry-key"
                image_pull_secrets.append(client.V1LocalObjectReference(name=sec_name))

    meta_data = client.V1ObjectMeta(name=app_name + "-odoo-deployment",
                                    labels={"app": app_name})
    args_odoo = ['--database=' + self.sub_domain_name]
    # args_odoo = []

    if self.demo_data:
        args_odoo.append('--without-demo=False')
    else:
        args_odoo.append('--without-demo=True')

    if self.module_ids:
        module_names = ''
        for module in self.module_ids:
            module_names = module_names + module.name + ','
        args_odoo.append("--init={0}".format(module_names))

    if self.db_server_id:
        _logger.critical('Cant deploy app, PG username or password cant find')
        UserError("Cant deploy app, PG username or password cant find")

    limits = client.V1ResourceRequirements(limits=res_limits)

    tolerations = []
    node_selector = {}
    if self and self.is_dedicated_node and self.node_id:
        # tolerations = [client.V1Toleration(effect='NoSchedule', key=self.node_key, value=self.node_value, operator='Equal')]
        # specific for aws clusters
        node_selector['kubernetes.io/hostname'] = self.node_id.name

    odoo_container = client.V1Container(
        name="odoo",
        image=image,
        env=[
            client.V1EnvVar(name="HOST", value=self.db_server_id.server_url),
            client.V1EnvVar(name="USER", value=self.db_server_id.master_username),
            client.V1EnvVar(name="PASSWORD", value=self.db_server_id.master_pass),
            client.V1EnvVar(name="PORT", value=self.db_server_id.server_port),
            client.V1EnvVar(name="ODOO_HTTP_SOCKET_TIMEOUT", value="100"),
             ],
        ports=[client.V1ContainerPort(container_port=8069, name="odoo-port"),
               client.V1ContainerPort(container_port=8072, name="longpolling")],
        args=args_odoo,
        image_pull_policy='Always',
        # command=['chown', '-R', '101:101', '/mnt/extra-addons'],
        resources=limits,
        # comment following line, if you want to run as odoo user
        # security_context=client.V1SecurityContext(run_as_user=0, run_as_group=0),
        volume_mounts=[client.V1VolumeMount(name=app_name + "-odoo-web-pv-storage", mount_path="/var/lib/odoo/")]
    )
    # pod Volume Claim
    volume_claim = client.V1PersistentVolumeClaimVolumeSource(claim_name=app_name + "-odoo-web-pv-claim")
    # pod volume
    volume = client.V1Volume(name=app_name + "-odoo-web-pv-storage", persistent_volume_claim=volume_claim)
    # Strategy
    strategy = client.V1DeploymentStrategy(type="Recreate")
    # Template
    # for  running as a odoo user changes instead of stash
    spec = client.V1PodSpec(containers=[odoo_container], volumes=[volume], image_pull_secrets=image_pull_secrets,
                            security_context=client.V1PodSecurityContext(run_as_group=101, run_as_user=101,
                                                                         fs_group=101, fs_group_change_policy='Always'),
                            node_selector=node_selector)

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": app_name, "tier": "backend"}),
        spec=spec
    )
    selector = client.V1LabelSelector(match_labels={"app": app_name, "tier": "backend"})

    # Spec
    specs = client.V1DeploymentSpec(
        replicas=1,
        strategy=strategy,
        selector=selector,
        template=template,
    )
    create_deployment(meta_data, specs, namespace, self=self)


def delete_odoo_deployment(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
    dep_name = app_name + "-odoo-deployment"
    core_v1_api = client.AppsV1Api()

    try:
        deployment = core_v1_api.delete_namespaced_deployment(name=dep_name, namespace=namespace)
        if self.is_custom_image and self.docker_image:
            if self.docker_image.is_pvt_dkr_repo and self.docker_image.b64_dkr_config:
                delete_docker_repo_secret(app_name, namespace, self)
        _logger.info(str(deployment))

    except client.exceptions.ApiException as e:
        _logger.error(str(e))
