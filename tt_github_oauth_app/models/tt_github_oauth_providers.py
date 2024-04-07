import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class TTAuthProviderInherit(models.Model):
    _inherit = "auth.oauth.provider"

    tt_client_secret = fields.Char(string="Client Secret")
    tt_is_github = fields.Boolean(compute='_compute_is_secret_required')
    tt_user_type = fields.Selection([('internal', 'Internal User'),
                                     ('portal', 'Portal User')], default="portal", string='User Type')

    def _compute_is_secret_required(self):
        for rec in self:
            if rec.auth_endpoint:
                if 'github' in rec.auth_endpoint:
                    rec.tt_is_github = True
                else:
                    rec.tt_is_github = False
            else:
                rec.tt_is_github = False
