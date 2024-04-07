# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
import stripe
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'
    stripe_subscription_id = fields.Char(string="Related Stripe Subscription")

    def create_from_stripe_api(self, user_id=False, stripe_sub_id=False):
        if not stripe_sub_id or not user_id:
            return
        stripe.api_key = self.env['ir.config_parameter'].sudo().get_param('stripe_secret_api_key')
        ssub = stripe.Subscription.retrieve(str(stripe_sub_id))
        if ssub:
            try:
                stripe_price_id = ssub.get('items').get('data')[0].get('price').get('id')
                if stripe_price_id:
                    saas_package = self.env['saas.package'].sudo().search([('stripe_product_id', '=', stripe_price_id)])
                    if saas_package and saas_package.subscription_template:
                        self._create_from_stripe_api(user_id, saas_package, stripe_sub_id)
                    else:
                        _logger.error('Unable to find SaaS package or Subscription Template')
                else:
                    _logger.error('Unable to find Stripe Price ID')

            except Exception as e:
                _logger.error(str(e))
        else:
            _logger.error('Unable to find Stripe Subscription object')

    def _create_from_stripe_api(self, user_id, package, stripe_sub_id):
        user = self.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
        if user and package and stripe_sub_id:
            new_sub = self.env['sale.subscription'].sudo().create({
                'partner_id': user.partner_id.id,
                'template_id': package.subscription_template.id,
                'stripe_subscription_id': stripe_sub_id,
                'recurring_invoice_line_ids':
                    [(0, 0,
                      {'product_id': package.year_product_id.id, 'name': package.name, 'price_unit': package.year_price,
                       'uom_id': package.year_product_id.uom_id.id})]
            })
            started = new_sub.sudo().start_subscription()
            if started:
                try:
                    invoice_action = new_sub.sudo().generate_recurring_invoice()
                    invoice_id = invoice_action.get('res_id')
                    if invoice_id:
                        invoice_obj = self.env['account.move'].sudo().browse([invoice_id])
                        if invoice_obj:
                            invoice_obj.action_post()
                            new_sub.sudo().create_saas_app_from_subscription(user_id=user_id, package=package)

                        #     Payment = self.env['account.payment'].with_context(default_line_ids=invoice_obj.invoice_line_ids.ids, default_invoice_ids=[(4, invoice_id, False)])
                        #     print(Payment)
                        #     payment_vals = {
                        #         'date': datetime.date.today(),
                        #         'amount': invoice_obj.amount_total,
                        #         'payment_type': 'inbound',
                        #         'partner_type': 'customer',
                        #         'partner_id': user.partner_id.id,
                        #         'line_ids': invoice_obj.invoice_line_ids,
                        #         # 'ref': self.communication,
                        #         # 'journal_id': self.journal_id.id,
                        #         # 'currency_id': self.currency_id.id,
                        #         # 'partner_bank_id': self.partner_bank_id.id,
                        #         # 'payment_method_id': self.payment_method_id.id,
                        #         # 'destination_account_id': self.line_ids[0].account_id.id
                        #     }
                        #
                        #     payment = Payment.sudo().create(payment_vals)
                        #     print(payment.action_post())

                except UserError as e:
                    _logger.error(e)
            else:
                _logger.error("Unable to start subscription")
        else:
            _logger.error('Stripe Subscription Id not found')

    def create_saas_app_from_subscription(self, user_id=False, package=False):
        saas_app_env = self.env['kk_odoo_saas.app']

        def_vals = saas_app_env.default_get(fields_list=['app_name'])

        if user_id:
            def_vals['admin_user'] = user_id
        else:
            def_vals['admin_user'] = self.partner_id.user_ids.ids[0]
        app_name = def_vals.get('app_name')
        configurations = self.env["kk_odoo_saas.k8s.config"]
        config = configurations.get_default_config()
        if config:
            def_vals['configuration'] = config.id
            def_vals['sub_domain_name'] = app_name
            def_vals['subscription_id'] = self.id
            def_vals['client_db_name'] = app_name
            # def_vals['module_ids'] = [(6, 0, saas_app_ids)]
            if package:
                def_vals['docker_image'] = package.docker_image.id
            def_vals['name'] = '{}'.format(self.code)

            saas_app = saas_app_env.create(def_vals)

            self.build_id = saas_app.id

            _logger.info('Going to Deploy SaaS App, Subscription is going to start')
            # saas_app.deploy_app()
        else:
            _logger.error('Cant create SaaS App, No K8s configuration found')
