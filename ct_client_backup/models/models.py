# -*- coding: utf-8 -*-
import os

from odoo import models, fields, api, _
from odoo.exceptions import UserError, MissingError
import requests
import xmlrpc
import logging
import base64

_logger = logging.getLogger(__name__)


class SaaSAppBackup(models.Model):
    _name = 'kk_odoo_saas.app.backup'
    _description = 'SaaS App Backup'

    name = fields.Char()
    app = fields.Many2one('kk_odoo_saas.app', 'SaaS App')
    file_name = fields.Char(string="File Name")
    file_path = fields.Char(string="File Path")
    url = fields.Char(string="Url")
    backup_date_time = fields.Datetime(string="Backup Time (UTC)")
    status = fields.Selection(string="Status", selection=[('failed', 'Failed'), ('success', 'Success')])
    message = fields.Char(string="Message")
    file_size = fields.Char(string="File Size")

    def download_db_file(self):
        """
        to download the database backup, it stores the file in attachment
        :return: Action
        """
        file_path = self.file_path
        _logger.info("------------ %r ----------------" % file_path)
        if self.url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.url,
                'target': 'new',
            }
        try:
            with open(file_path, 'rb') as reader:
                result = base64.b64encode(reader.read())
        except IOError as e:
            raise MissingError('Unable to find File on the path')
        attachment_obj = self.env['ir.attachment'].sudo()
        name = self.file_name
        attachment_id = attachment_obj.create({
            'name': name,
            'datas': result,
            'public': False
        })
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        _logger.info("--- %r ----" % download_url)
        self.url = download_url
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'new',
        }

    def action_restore_backup_to_instance(self, restore_to_id=False):
        """
        it will restore the backup to a new instance,
        the instance should be created manually,
        and there should be no database at new_instance.com/web/database/selector
        :param: restore_to_id is kk_saa_app object on which we have to restore backup
        :return: False
        """
        if self.app and restore_to_id:
            restore_url = restore_to_id.get_url()
            if self.file_path and os.path.exists(self.file_path) and requests.get(restore_url).status_code < 400:
                db_list = []
                try:
                    db_list = xmlrpc.client.ServerProxy(restore_url + '/xmlrpc/db').list()
                except xmlrpc.client.ProtocolError as e:
                    _logger.info("There is no database on Db selector")

                _logger.info("All Databases on Postgres Server -> {} <-".format(db_list))
                _logger.info("New Db name: {}".format(restore_to_id.app_name))
                if restore_to_id.app_name not in db_list:
                    self.restore_backup_to_client(self.file_path, restore_url, restore_to_id.app_name,
                                                  restore_to_id.backup_master_pass)
                else:
                    raise UserError("Cant restore Backup, Database already existed, please delete it.")
            else:
                raise UserError("Cant restore Backup! the url is not accessible or backup file not exists.")
        else:
            _logger.error("Cant restore Backup, Backup Id, or Restore App Missing")
            raise UserError("Cant restore Backup, Backup Id, or Restore App Missing")

    def restore_backup_to_client(self, file_path, restore_url, db_name, master_pwd):
        if file_path and restore_url and db_name and master_pwd:
            restore_url = restore_url + '/web/database/restore'
            data = {
                'master_pwd': master_pwd,
                'name': db_name,
                'copy': 'true',
                'backup_file': '@' + file_path
            }
            backup = open(file_path, "rb")
            try:
                response = requests.post(restore_url, data=data, files={"backup_file": backup})
                if response.status_code == 200:
                    _logger.info("Restore Done, this is the response Code: {}".format(response.status_code))
                else:
                    _logger.info("Restore Done, this is the response Code: {}".format(response.status_code))

                return {
                    'success': True,
                }
            except Exception as e:
                return {
                    'success': False,
                }
        else:
            _logger.error("Cant restore Db One of the parameter is Missing")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('saas_app.backup')
        res = super(SaaSAppBackup, self).create(vals)
        return res

    def calc_backup_size(self):
        if not os.path.exists(self.file_path):
            return
            # calculate file size in KB, MB, GB

        def convert_bytes(size):
            """ Convert bytes to KB, or MB or GB"""
            for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return "%3.1f %s" % (size, x)
                size /= 1024.0

        self.file_size = convert_bytes(os.path.getsize(self.file_path))
