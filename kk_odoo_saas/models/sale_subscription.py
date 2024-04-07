from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'
    build_id = fields.Many2one("kk_odoo_saas.app", string="Related SaaS Instance")
    is_saas = fields.Boolean('Is SaaS Subscription')

    def start_subscription(self):
        res = super(SaleSubscription, self).start_subscription()
        if self.build_id:
            self.build_id.deploy_app()
        return res

    @api.model
    def create(self, vals):
        res = super(SaleSubscription, self).create(vals)
        return res
