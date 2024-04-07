from datetime import timedelta

import requests
from odoo import models, fields, api, _
import logging
import os
_logger = logging.getLogger(__name__)


class SaaSApp(models.Model):
    _inherit = 'kk_odoo_saas.app'
    backup_db_name = fields.Char(string="Database Name", default=lambda a: a.client_db_name)
    backup_master_pass = fields.Char(string="Master Password")
    backups_enabled = fields.Boolean()

    backups = fields.Many2many(comodel_name='kk_odoo_saas.app.backup', string='Backups')

    def action_create_backup(self):
        """
        It is being called from 2 locations
        :return:
        """
        for app in self:
            response = self.backup_db()
            backup = self.env['kk_odoo_saas.app.backup'].create({'backup_date_time': fields.Datetime.now(),
                                                                 'app': app.id,
                                                                 'file_name': response.get('filename'),
                                                                 'file_path': response.get('filepath'),
                                                                 'message': response.get('message')
                                                                 })
            if response.get('success'):
                backup.write({'status': 'success'})
            else:
                backup.write({'status': 'failed'})
            app.write({'backups': [(4, backup.id)]})

    def action_delete_old_backup(self):
        for app in self:
            for backup in app.backups:
                if backup.backup_date_time < fields.Datetime.now() - timedelta(days=7.0):
                    if os.path.exists(backup.file_path):
                        try:
                            os.remove(backup.file_path)
                            if backup.url:
                                # deleting the attachments related to this backup
                                att_id = backup.url.replace('?download=true', '').replace('/web/content/', '')
                                if att_id:
                                    try:
                                        attch_id = int(att_id)
                                        if attch_id:
                                            self.env['ir.attachment'].browse([attch_id]).unlink()
                                    except ValueError as e:
                                        _logger.error(e)
                            backup.unlink()
                        except OSError as e:
                            _logger.error("Error while deleting file: %s - %s." % (e.filename, e.strerror))
                    else:
                        _logger.error("The file does not exist")

    def backup_db(self):
        """
        Actual Backup function
        :return:
        """
        # get the creds for db manager
        data = {
            'master_pwd': self.backup_master_pass,
            'name': self.backup_db_name,
            'backup_format': 'zip'
        }

        client_url = 'https://{0}{1}'.format(self.sub_domain_name, self.domain_name)
        msg = ''

        # where we want to store backups, in the linux user, with which the odoo-service is running
        backup_dir = os.path.join(os.path.expanduser('~'), 'client_backups')
        if not os.path.exists(backup_dir):
            os.mkdir(backup_dir)

        backup_dir = os.path.join(backup_dir, self.sub_domain_name)
        if not os.path.exists(backup_dir):
            os.mkdir(backup_dir)

        client_url += '/web/database/backup'
        # Without Streaming method
        # response = requests.post(client_url, data=data)
        # Streaming zip, so that everything is not stored in RAM.

        try:
            filename = self.backup_db_name + '-' + fields.Datetime.now().strftime("%m-%d-%Y-%H-%M") + '.zip'
            backed_up_file_path = os.path.join(backup_dir, filename)
            with requests.post(client_url, data=data, stream=True) as response:
                response.raise_for_status()
                with open(os.path.join(backup_dir, filename), 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
            msg = 'Database backup Successful at ' + fields.Datetime.now().strftime("%m-%d-%Y-%H:%M:%S")
            return {
                'success': True,
                'msg': msg,
                'filename': filename,
                'filepath': backed_up_file_path
            }
        except Exception as e:
            msg = 'Failed at ' + fields.Datetime.now().strftime("%m-%d-%Y-%H:%M:%S") + ' ' + str(e)
            return {
                'success': False,
                'msg': msg
            }

    @api.model
    def ignite_backup_server_cron(self):
        """
        A Scheduled Action which will take new backups and del old
        :return: False
        """
        # search for saas instance in lanched and modified states and backups enabled
        apps = self.env['kk_odoo_saas.app'].sudo().search(
            [('status', 'in', ['l', 'm']), ('backups_enabled', '=', True)])

        for app in apps:
            app.action_create_backup()
            app.action_delete_old_backup()
