# -*- coding: utf-8 -*-
import base64

import psycopg2
import requests
import os
from odoo import models, fields, api, _
from ..utils import k8s_deployment as k8s
from ..utils import ingress, logs
from ..utils import del_git_code as dc
import re
from odoo.exceptions import ValidationError, MissingError
from odoo.addons.smile_log.tools import SmileDBLogger
import logging
import xmlrpc.client
import random
import string
from odoo.addons.queue_job.exception import RetryableJobError
from odoo.exceptions import AccessError
from datetime import timedelta
from ..utils import pg_server as pgx
_logger = logging.getLogger(__name__)


class SaaSAppSslSecret(models.Model):
    _name = 'kk_odoo_saas.app.ssl_secret'
    name = fields.Char('Secret Name')


class SaaSApp(models.Model):
    _name = 'kk_odoo_saas.app'
    _description = 'SaaS App'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    app_name = fields.Char('App Unique Id',
                           default=lambda self: self.env['ir.sequence'].next_by_code('kk_odoo_saas.app'), tracking=True, copy=False)
    name = fields.Char(tracking=True)
    is_custom_image = fields.Boolean(default=True)
    docker_image = fields.Many2one('kk_odoo_saas.k8s.docker.images')
    is_pvt_dkr_repo = fields.Boolean('Using Private Docker Repository')

    is_extra_addon = fields.Boolean('Use Extra Addons')
    extra_addons = fields.Char('Git Url', tracking=True)
    is_private_repo = fields.Boolean('Is Private Repository?')
    git_token = fields.Char('Auth Token')

    # K8s values
    client = fields.Many2one('res.partner', related='admin_user.partner_id', tracking=True)
    country_id = fields.Many2one(string="Country", comodel_name='res.country',
                                 help="Country for which this instance is being deployed")

    admin_user = fields.Many2one("res.users", "Client User", tracking=True)

    def _get_default_cluster_config(self):
        cluster = self.env['kk_odoo_saas.k8s.config'].search([], limit=1)
        if cluster:
            return cluster.id
        return False

    configuration = fields.Many2one('kk_odoo_saas.k8s.config', string='Configuration', default=_get_default_cluster_config)

    domain_name = fields.Char(related='configuration.domain_name')
    sub_domain_name = fields.Char(required=True)

    is_dedicated_node = fields.Boolean(string='Any Dedicated Node')
    node_id = fields.Many2one('kk_odoo_saas.k8s.node', string='Node')
    node_key = fields.Char()
    node_value = fields.Char()

    demo_data = fields.Boolean('Install Demo Data')
    status = fields.Selection([('d', 'Draft'), ('l', 'Launched'), ('m', 'Modified'), ('del', 'Deleted')],
                              string='Status', default='d', tracking=True)
    expiry_date = fields.Date(tracking=True)
    subscription_id = fields.Many2one('sale.subscription', string='Related Subscription', tracking=True)
    notes = fields.Text()
    module_ids = fields.Many2many(comodel_name='saas.app', string='Modules to install')

    login_email = fields.Char('Login Email')
    login_pwd = fields.Char('Login Pwd')

    master_login_email = fields.Char('Master Login Email')
    master_login_pwd = fields.Char('Master Login Pwd')

    custom_domain_ids = fields.One2many('saas.app.custom.domain', 'saas_app_id', string='Custom Domains')

    def _default_db_name(self):
        return self.sub_domain_name

    k8s_logs = fields.Many2many('smile.log', string='K8s Logs', compute='_get_k8s_logs')

    # db server relation
    def _get_default_db_server(self):
        db_server = self.env['kk_odoo_saas.k8s.master_db_creds'].search([], limit=1)
        if db_server:
            return db_server
        return False
    db_server_id = fields.Many2one('kk_odoo_saas.k8s.master_db_creds', string="DB Server", default=_get_default_db_server)
    client_db_name = fields.Char("Database Name", required=True)
    login_url = fields.Char('Login URL', compute='_get_instance_login_url')

    # _sql_constraints = [
    #     ('hostname_uniq', 'unique(hostname)', "A Domain already exists. Domain's name must be unique!"),
    # ]

    @api.model
    def create(self, values):
        _logger = logging.getLogger(__name__)
        if self:
            _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        res = super(SaaSApp, self).create(values)

        if not res.validate_domain_name():
            _logger.error('Either Domain or Subdomain is not valid')
            raise ValidationError('Either Domain or Subdomain is not valid')
        return res

    def write(self, vals):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        # if vals and 'status' not in vals and self.status not in ['d', 'del']:
        #     vals.update({'status': 'm'})

        res = super(SaaSApp, self).write(vals)

        if 'custom_domain_ids' in vals:
            #todo: add validation, limit number of domains per instance
            self.update_app()

        if 'sub_domain_name' or 'domain_name' in vals:
            if not self.validate_domain_name():
                _logger.error('Either Domain or Subdomain is not valid')
                raise ValidationError('Either Domain or Subdomain is not valid')
        return res


    @api.onchange('app_name')
    def set_sub_domain_name(self):
        self.sub_domain_name = self.app_name
        # also set the database name
        self.client_db_name = self.app_name

    def validate_domain_name(self):
        if self.domain_name and self.sub_domain_name:
            full_name = self.sub_domain_name + self.domain_name
            domain_regex = r'(([\da-zA-Z])([_\w-]{,62})\.){,127}(([\da-zA-Z])[_\w-]{,61})?([\da-zA-Z]\.((xn\-\-[a-zA-Z\d]+)|([a-zA-Z\d]{2,})))'
            domain_regex = '{0}$'.format(domain_regex)
            valid_domain_name_regex = re.compile(domain_regex, re.IGNORECASE)
            full_name = full_name.lower().strip()
            if re.match(valid_domain_name_regex, full_name):
                return True
        return

    def deploy_app(self):
        self.ensure_one()
        k8s.create_deployment(app_name=self.app_name, config_file=self.configuration.config_file, self=self)
        ingress.create_ingress(app_name=self.app_name, self=self)
        self.status = 'l'
        self.with_delay().post_init_tasks()

    def delete_app_from_wizard(self, delete_db, delete_pv, delete_svc, delete_ing, delete_deployment):
        # if delete_db:
        #     self.delete_database_remotely(db_master_pwd=db_master_pwd)
        k8s.delete_app_with_options(self, delete_db, delete_pv, delete_svc, delete_ing, delete_deployment)

        self.status = 'del'

    def update_app(self):
        k8s.update_app(self)
        self.status = 'l'

    def get_url(self):
        return "http://{0}{1}".format(self.sub_domain_name, self.domain_name)

    def deploy_apps_from_git(self):
        k8s.deploy_apps_from_git(self)

    def restart_odoo_service(self):
        k8s.restart_odoo_service(self)

    def action_show_subscription(self):
        self.ensure_one()
        assert self.subscription_id, "This app is not associated with any Subscription"
        return {
            "type": "ir.actions.act_window",
            "name": "Subscription",
            "res_model": "sale.subscription",
            "res_id": self.subscription_id.id,
            "view_mode": "form",
        }

    def action_create_subscription(self):
        self.ensure_one()
        assert not self.subscription_id, "This app is already associated with Subscription"
        return {
            "type": "ir.actions.act_window",
            "name": "Subscription",
            "res_model": "sale.subscription",
            "view_mode": "form",
            "context": {
                "default_name": self.name + "'s SaaS Subscription",
                "default_build_id": self.id,
                "default_partner_id": self.client.id,
            }
        }

    def _get_instance_login_url(self):
        for app in self:
            app.login_url = ''
            response, db = pgx.get_admin_credentials(app)
            if response and db:
                app.login_url = "https://{0}{1}/saas/login?db={2}&login={3}&passwd={4}".format(self.sub_domain_name,
                                                                                           self.domain_name, db, response[0][0],
                                                                                           response[0][1])
            else:
                _logger.info("Unknown Error!")

    def action_connect_instance(self):
        self.ensure_one()
        response, db = pgx.get_admin_credentials(self)
        if response and db:
            login = response[0][0]
            password = response[0][1]
            login_url = "https://{0}{1}/saas/login?db={2}&login={3}&passwd={4}".format(self.sub_domain_name, self.domain_name, db, login, password)
            _logger.info("Login URL %r " % (login_url))
            return {
                'type': 'ir.actions.act_url',
                'url': login_url,
                'target': 'new',
            }
        else:
            _logger.info("Unknown Error!")


    def create_instance_admin_user_for_client(self, models1, db, uid, password, client_pwd):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        try:
            adm_user_id = models1.execute_kw(db, uid, password,
                                             'res.users', 'search_read',
                                             [[['login', '=', 'admin']]], {'fields': ['groups_id'], 'limit': 1}
                                             )
            if adm_user_id:
                adm_user_id = adm_user_id[0]
                groups_ids = adm_user_id.get('groups_id', False)
                if groups_ids:
                    new_user_id = models1.execute_kw(db, uid, password, 'res.users', 'create',
                                                     [{'name': self.client.name,
                                                       'login': self.client.email,
                                                       'company_ids': [1], 'company_id': 1,
                                                       'password': client_pwd}])
                    if new_user_id:
                        _logger.info('Created client Account on instance')
                        return models1.execute_kw(db, uid, password, 'res.groups', 'write',
                                                  [groups_ids, {'users': [(4, new_user_id)]}])
        except xmlrpc.client.Error as e:
            _logger.error(str(e))
            return

    def reset_apps_admin_pwd(self):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        protocol = 'https'
        url = protocol + '://{0}{1}'.format(self.sub_domain_name, self.domain_name)
        db = self.sub_domain_name
        new_pwd_client = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        new_pwd_master = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        username = 'admin'
        password = 'admin'
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(db, username, password, {})
            _logger.info('Sending request to app with uid {}'.format(uid))
            models1 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            try:
                if self.create_instance_admin_user_for_client(models1, db, uid, password, new_pwd_client):
                    _logger.info('Updated Client User\'s Access Rights on instance')
                    self.update({'login_pwd': new_pwd_client, 'login_email': self.client.email})

                adm_user_id = models1.execute_kw(db, uid, password,
                                                 'res.users', 'search',
                                                 [[['login', '=', 'admin']]], {'limit': 1}
                                                 )[0]
                if models1.execute_kw(db, uid, password, 'res.users', 'write', [[adm_user_id], {
                    'password': new_pwd_master,
                }]):
                    self.update({'master_login_pwd': new_pwd_master, 'master_login_email': 'admin'})
                    self.send_app_pwd_cred_email()
                    _logger.info('Password and login changed Successfully')
            except xmlrpc.client.Error as e:
                _logger.error(str(e))
        except xmlrpc.client.Error as e:
            _logger.error(str(e))

    def set_user_country(self):
        country_code = self.country_id.code
        if self.country_id and self.country_id.code:
            _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
            protocol = 'https'
            url = protocol + '://{0}{1}'.format(self.sub_domain_name, self.domain_name)
            db = self.sub_domain_name
            username = 'admin'
            password = 'admin'
            try:
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
                uid = common.authenticate(db, username, password, {})
                _logger.info('Sending request to app with uid {}'.format(uid))
                models1 = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
                try:
                    country = models1.execute_kw(db, uid, password,
                                                     'res.country', 'search_read',
                                                     [[['code', 'ilike', country_code]]], {'fields': ['id'], 'limit': 1}
                                                     )
                    if country:
                        country = country[0]
                        if country:
                            new_user_id = models1.execute_kw(db, uid, password, 'res.company', 'write',
                                                             [[1], {'country_id': country_code and self.country_id.id,
                                                                    'currency_id': country_code and self.country_id.currency_id.id}])
                            if new_user_id:
                                _logger.info('Updated country of the user')
                except xmlrpc.client.Error as e:
                    _logger.error(str(e))
            except xmlrpc.client.Error as e:
                _logger.error(str(e))

    def post_init_tasks(self):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
        if not self.check_site_assible():
            _logger.info('Waiting for the App to become live....')
            raise RetryableJobError('Unable to get the app live.')
        else:
            self.set_user_country()
            self.reset_apps_admin_pwd()

    def check_site_assible(self):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        try:
            resp = requests.get('http://' + self.sub_domain_name + self.domain_name)
            _logger.info('App, sent this status code {}'.format(resp.status_code))
            if resp.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            _logger.error(str(e))
            return False

    def send_app_pwd_cred_email(self):
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

        template = False
        try:
            template = self.env.ref('kk_odoo_saas.app_invitation_email', raise_if_not_found=False)
        except ValueError:
            pass
        assert template._name == 'mail.template'

        template_values = {
            'email_to': '${object.admin_user.email|safe}',
            'email_cc': False,
            'auto_delete': True,
            'partner_to': False,
            'scheduled_date': False,
        }
        template.write(template_values)

        if not self.admin_user.email:
            _logger.error(_("Cannot send email: user %s has no email address.", self.admin_user.name))
        with self.env.cr.savepoint():
            try:
                template.send_mail(self.id, force_send=True, raise_exception=True)
            except Exception as e:
                _logger.error(str(e))
        _logger.info(_("App Details email sent for user <%s> to <%s>", self.admin_user.login, self.admin_user.email))

    def _message_get_suggested_recipients(self):
        recipients = super(SaaSApp, self)._message_get_suggested_recipients()
        try:
            for saas_app in self:
                if saas_app.client:
                    saas_app._message_add_suggested_recipient(recipients, partner=saas_app.client, reason=_('SaaS Client'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    def _get_k8s_logs(self):
        for app in self:
            app.k8s_logs = False
            logs_ = self.env['smile.log'].search([('res_id', '=', app.id), ('model_name', '=', self._name)])
            for log in logs_:
                app.k8s_logs = [(4, log.id)]

    def get_pod_logs(self):
        output = logs.read_logs(app_name=self.app_name, config_file=self.configuration.config_file, self=self, tail_lines=None)
        if output:
            result = base64.b64encode(output.encode())
            attachment_obj = self.env['ir.attachment']
            # create attachment
            attachment_id = attachment_obj.create(
                {'name': self.app_name+'-odoo-logs.log', 'datas': result, 'public': False})
            # prepare download url
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
            # download
            return {
                "type": "ir.actions.act_url",
                "url": str(download_url),
                "target": "new",
            }
        else:
            raise MissingError('Unable to get logs \nReason: Running Pod / Container not found')

    def action_log_viewer(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/saas/instance/{app_id}".format(app_id=self.id),
            "target": "new",
        }

    def get_timed_pod_logs(self, interval=None, since_seconds=None, previous=None, tail_lines=None):
        output = logs.read_logs(app_name=self.app_name, config_file=self.configuration.config_file, self=self, since_seconds=since_seconds)
        if output:
            return output

    def update_docker_image(self, container_arguments, env_vars=False):
        patched_deployment = k8s.update_deployment(self=self, container_arguments=container_arguments, env_vars=env_vars)
        if patched_deployment:
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': 'Image Update in Progress',
                 'message': 'Deployment in Progress with latest docker image'}
            )
            return True

    def get_odoo_deployment(self):
        deployment = k8s.read_deployment(self=self)
        if deployment:
            return deployment
        return False

    def refresh_node_list(self):
        if self.configuration:
            self.configuration.update_cluster_nodes()

    def get_pg_db_connection(self, db='postgres'):
        for rec in self:
            if rec.db_server_id.master_pass and rec.db_server_id.master_username and rec.db_server_id.server_url:
                try:
                    _logger.info("Going to connect to PG DB server")
                    conn = psycopg2.connect(database=db,
                                            user=rec.db_server_id.master_username,
                                            password=rec.db_server_id.master_pass,
                                            host=rec.db_server_id.server_url,
                                            port=rec.db_server_id.server_port or 5432
                                            )
                    if conn:
                        _logger.info("Connected to PG DB server")
                        return conn
                except Exception as e:
                    _logger.exception(e)
                    return
            else:
                return

    def del_git_dir(self):
        base_version = self.docker_image.base_version
        delete_path = "/var/lib/odoo/addons/" + str(base_version)
        dc.del_git_dir(self, path=delete_path)


class SaaSAppDomain(models.Model):
    _name = 'saas.app.custom.domain'
    _description = 'SaaS App Custom Domain'

    name = fields.Char('Domain Name', required=True)
    saas_app_id = fields.Many2one('kk_odoo_saas.app')
    ssl = fields.Boolean('Enable SSL?', default=True)


class DockerAccount(models.Model):
    _name = 'saas.docker.hub.account'

    username = fields.Char('docker hub username')
    pwd = fields.Char('Password or Access Token')
    # for more info https://docs.docker.com/docker-hub/access-tokens/