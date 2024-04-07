from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    build_id = fields.Many2one("kk_odoo_saas.app")
    is_pkg_pdt = fields.Boolean(default=False)

    def _split_subscription_lines(self):
        """Split the order line according to subscription templates that must be created."""
        self.ensure_one()
        res = dict()
        for line in self.order_line:
            if line.product_id:
                for p_id, p_name in line.product_id.name_get():
                    if '(Annually)' in p_name:
                        line.product_id.update(
                            {'subscription_template_id': self.env.ref('sale_subscription.yearly_subscription').id})
                    elif '(Monthly)' in p_name:
                        line.product_id.update(
                            {'subscription_template_id': self.env.ref('sale_subscription.monthly_subscription').id})

        new_sub_lines = self.order_line.filtered(lambda
                                                     l: not l.subscription_id and l.product_id.subscription_template_id and l.product_id.recurring_invoice)
        templates = new_sub_lines.mapped('product_id').mapped('subscription_template_id')
        for template in templates:
            lines = self.order_line.filtered(
                lambda l: l.product_id.subscription_template_id == template and l.product_id.recurring_invoice)
            res[template] = lines
        return res

    def _action_confirm(self):
        """Update and/or create subscriptions on order confirmation."""
        res = super(SaleOrder, self)._action_confirm()
        # self.create_saas_app_from_subscription()
        return res

    def create_saas_app_from_subscription(self):
        for so in self:
            lines = so.order_line.filtered(lambda l: l.subscription_id is not False)
            p_ids = so.order_line.mapped('product_id')
            if lines and p_ids:
                saas_app_ids = [app.id for app in self.env['saas.app'].search([('year_product_id', 'in', p_ids.ids)])]
                if not saas_app_ids:
                    saas_app_ids = [app.id for app in self.env['saas.app'].search([('month_product_id', 'in', p_ids.ids)])]
                line = lines[0]
                sub_id = line.subscription_id
                pkg = False
                if so.is_pkg_pdt:
                    pkg = self.env['saas.package'].search([('year_product_id', 'in', p_ids.ids)])
                    if not pkg:
                        pkg = self.env['saas.package'].search([('month_product_id', 'in', p_ids.ids)])
                    if pkg:
                        saas_app_ids = pkg.module_ids.ids
                if so and so.build_id and sub_id:
                    so.build_id.update({'subscription_id': sub_id.id,
                                        'module_ids': [(6, 0, saas_app_ids)]
                                        })
                    sub_id.build_id = so.build_id
                    so.build_id.deploy_app()
                else:
                    saas_app_env = self.env['kk_odoo_saas.app']
                    def_vals = saas_app_env.default_get(fields_list=['app_name', ])
                    if self.partner_id.user_ids:
                        def_vals['admin_user'] = self.partner_id.user_ids.ids[0]
                    configurations = self.env["kk_odoo_saas.k8s.config"]
                    config = configurations.get_default_config()
                    if config:
                        def_vals['configuration'] = config.id
                        def_vals['sub_domain_name'] = def_vals.get('app_name')
                        def_vals['subscription_id'] = sub_id.id
                        def_vals['module_ids'] = [(6, 0, saas_app_ids)]
                        def_vals['docker_image'] = pkg.docker_image.id
                        def_vals['name'] = '{}\'s SaaS App'.format(self.partner_id.name)
                        saas_app = saas_app_env.create(def_vals)

                        sub_id.build_id = saas_app.id
                        self.build_id = saas_app.id

                        _logger.info('Going to Deploy SaaS App, Subscription is going to start')
                        saas_app.deploy_app()
                    else:
                        _logger.error('Cant create SaaS App, No K8s configuration found')
