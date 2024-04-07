import psycopg2
from odoo import models, fields, api
from kubernetes import config, client
from odoo.exceptions import UserError
import yaml
import logging

_logger = logging.getLogger(__name__)

class SaaSAppK8sConfig(models.Model):
    _name = 'kk_odoo_saas.k8s.config'
    _description = 'Kubernetes Cluster Configuration'
    name = fields.Char()
    config_file = fields.Text('Yaml Configuration File')
    cluster_name = fields.Char('')
    namespaces = fields.Text('Namespaces in Cluster')
    domain_name = fields.Char('Domain Name')

    def check_connectivity(self):
        if self.config_file:
            try:
                data2 = yaml.safe_load(self.config_file)
                config.load_kube_config_from_dict(data2)
                v1 = client.CoreV1Api()
                response = v1.list_namespace()
                nss = []
                for namespace in response.items:
                    nss.append(namespace.metadata.name)
                nl = '\n'
                self.namespaces = nl.join(nss)
            except config.config_exception.ConfigException as e:
                raise UserError("Unable to Connect K8s Cluster")
        else:
            raise UserError("Please Add config file")

    def validate_domain_name(self):
        if self.domain_name:
            pass

    def get_default_config(self):
        for conf in self.search([], limit=1):
            return conf

    def update_cluster_nodes(self):
        if self.config_file:
            try:
                data2 = yaml.safe_load(self.config_file)
                config.load_kube_config_from_dict(data2)
                v1 = client.CoreV1Api()
                response = v1.list_node()
                node_env = self.env['kk_odoo_saas.k8s.node']
                if response:
                    node_env.search([]).unlink()
                    for node in response.items:
                        node_env.create({'name': node.metadata.name, 'labels': str(node.metadata.labels), 'annotations': str(node.metadata.annotations), 'taints': str(node.spec.taints), 'yaml_info': str(node)})
            except config.config_exception.ConfigException as e:
                _logger.error(e)
                raise UserError("Unable to Connect K8s Cluster")
        else:
            raise UserError("Please Add config file")


class DockerImages(models.Model):
    _name = 'kk_odoo_saas.k8s.docker.images'

    name = fields.Char('Image Name', required=True)
    tag = fields.Char('Tag Name', required=True, default='latest')
    description = fields.Char('Description')
    is_pvt_dkr_repo = fields.Boolean('Using Private Docker Repository')
    b64_dkr_config = fields.Text('base64 docker config json file')
    repo_link = fields.Char('Related Repository')
    base_version = fields.Selection([('14.0', '14.0'), ('15.0', '15.0'), ('16.0', '16.0')], required=True)
    # base_version is for pulling git code in folder e.g /var/lib/odoo/addons/14.0 etc.

    @api.depends('name', 'tag')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.tag:
                name = name + ':' + record.tag
            res.append((record.id, name))
        return res


class Node(models.Model):
    _name = 'kk_odoo_saas.k8s.node'
    name = fields.Char('Node Name')
    labels = fields.Text('Labels')
    annotations = fields.Text()
    taints = fields.Text()

    yaml_info = fields.Text("Yaml Description")


class MasterDbCreds(models.Model):
    _name = 'kk_odoo_saas.k8s.master_db_creds'

    name = fields.Char('DB Server Name')
    master_username = fields.Char('Master Username', default='postgres', required=True)
    master_pass = fields.Char('Master Password', required=True)
    server_url = fields.Char('Server URL', required=True)
    server_port = fields.Char('Server Port', default='5432', required=True)
    status = fields.Selection([('connected', 'Connected'), ('not_connected', 'Not Connected')], default='not_connected')

    def check_connectivity(self):
        for rec in self:
            if rec.master_username and rec.master_pass and rec.server_url:
                try:
                    conn = psycopg2.connect(database='postgres',
                                            user=rec.master_username,
                                            password=rec.master_pass,
                                            host=rec.server_url,
                                            port=rec.server_port or 5432)
                    if conn:
                        _logger.info("Connected to PG DB server")
                        self.status = 'connected'
                        return conn
                except Exception as e:
                    _logger.exception(e)
                    self.status = 'not_connected'
                    raise UserError('Unable to Connect Postgres.\nPlease Check Postgres Credentials...!')
            else:
                self.status = 'not_connected'
                raise UserError('Please Enter Postgres Credentials...!')
