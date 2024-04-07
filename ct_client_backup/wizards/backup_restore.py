from odoo import fields, models
import logging
from odoo.exceptions import UserError, MissingError

_logger = logging.getLogger(__name__)


class BackupRestore(models.TransientModel):
    _name = 'saas.client.backup.restore.wizard'
    name = fields.Char('Name')
    backup_id = fields.Many2one('kk_odoo_saas.app.backup', 'Backup Name')
    restore_to = fields.Many2one('kk_odoo_saas.app', 'Restore Backup To')

    def action_call_restore_function(self):
        """
        It will call the Backup Function Async, Thanks to queue_job module
        :return:
        """
        if self.backup_id and self.backup_id.app and self.restore_to:
            self.backup_id.action_restore_backup_to_instance(self.restore_to)
        else:
            _logger.error("Cant restore Backup, Backup Id, or Restore App Missing")
            raise UserError("Cant restore Backup, Backup Id, or Restore App Missing")
