import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)



class SaasPackage(models.Model):
    _name = "saas.package"
    _inherit = ["saas.period.product.mixin"]

    is_published = fields.Boolean("Publish It?", default=True)
    package_image = fields.Image(
        string='Package image'
    )
    name = fields.Char(copy=False)
    module_ids = fields.Many2many('saas.app', string="Modules to install")
    docker_image = fields.Many2one('kk_odoo_saas.k8s.docker.images', 'Related Docker Image')
    stripe_product_id = fields.Char('Stripe Id')
    subscription_template = fields.Many2one('sale.subscription.template')

    @api.model
    def create(self, vals):
        res = super(SaasPackage, self).create(vals)
        if not res.product_tmpl_id:
            res.product_tmpl_id = self.env["product.template"].create({
                "name": res.name,
                "image_1920": res.package_image,
                "saas_package_id": res.id,
                "is_saas_product": True,
                "type": 'service',
                "purchase_ok": False,
                "subscription_template_id": self.env.ref("sale_subscription.monthly_subscription").id,
                "recurring_invoice": True,
                "website_published": True,
                "list_price": 0,
            })
        return res

    def write(self, vals):
        res = super(SaasPackage, self).write(vals)
        if vals.get('month_price', None) is not None or vals.get('year_price', None) is not None:
            self._update_variant_prices()
        return res

    def _update_variant_prices(self):
        for app in self:
            for variant in app.product_tmpl_id.product_variant_ids:
                for attr in variant.product_template_attribute_value_ids:
                    if attr.name == "Monthly":
                        attr.update({'price_extra': app.month_price})
                    if attr.name == "Annually":
                        attr.update({'price_extra': app.year_price})


    def refresh_page(self):
        # Empty-function for purpose of refreshing page
        pass

