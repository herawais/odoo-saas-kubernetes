from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    saas_app_id = fields.Many2one("saas.app", ondelete="cascade", index=True)
    saas_package_id = fields.Many2one("saas.package", ondelete="cascade", index=True)
    is_saas_product = fields.Boolean("Is SaaS product?", default=False)

    @api.model
    def create(self, vals):
        if vals.get("is_saas_product"):
            vals["taxes_id"] = [(5,)]
            vals["supplier_taxes_id"] = [(5,)]
        return super(ProductTemplate, self).create(vals)
