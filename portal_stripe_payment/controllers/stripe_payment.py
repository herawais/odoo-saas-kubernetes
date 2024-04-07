import json
from datetime import datetime
from odoo.addons.rest_api.controllers.main import *
from odoo import http, tools, _, SUPERUSER_ID
import stripe

import logging

_logger = logging.getLogger(__name__)


class StripePayment(http.Controller):
    @http.route('/api/stripe/create-checkout-session', methods=['POST'], type='http', csrf=False, auth='none', cors=rest_cors_value)
    @check_permissions
    def create_checkout_session(self, **kw):
        cr, uid = request.cr, request.session.uid
        api_key = request.env(cr, uid)['ir.config_parameter'].sudo().get_param('stripe_secret_api_key')
        saas_portal_url = request.env(cr, uid)['ir.config_parameter'].sudo().get_param('portal_url', 'https://saas.vercel.app')
        pscs = request.env(cr, uid)['portal.stripe.checkout.session']

        if not api_key:
            return error_response_400__invalid_object_id()
        stripe.api_key = api_key
        try:
            body = json.loads(request.httprequest.data)
        except Exception as e:
            _logger.error(e)
            return error_response_400__invalid_object_id()

        if body.get('plan_id'):

            user = request.env(cr, uid)['res.users'].browse([uid])
            partner = user.partner_id

            plan = request.env(cr, uid)['saas.package'].sudo().search([('id', '=', body.get('plan_id'))])
            if plan and plan.stripe_product_id:
                try:
                    checkout_session = stripe.checkout.Session.create(
                        line_items=[
                            {
                                'price': plan.stripe_product_id,
                                'quantity': 1,
                            },
                        ],
                        client_reference_id=uid,
                        mode='subscription',
                        success_url=str(saas_portal_url) + '/payment/success?session_id={CHECKOUT_SESSION_ID}',
                        cancel_url=str(saas_portal_url) + '/payment/canceled',
                        customer_email=partner.email if partner.email and not partner.related_stripe_id else None,
                        customer=partner.related_stripe_id if partner.related_stripe_id else None,
                    )
                    pscs.sudo().create({'name': datetime.now(), 'session_id': checkout_session.id, 'user_id': uid})
                    return successful_response(200, {'redirect_url': checkout_session.url})
                except Exception as e:
                    _logger.error(e)
                    return error_response_400__invalid_object_id()

        return error_response_400__invalid_object_id()



    @http.route('/api/stripe/webhooks', methods=['POST'], type='json', csrf=False, auth='public', cors='*')
    # @check_permissions
    def stripe_webhook(self, **kw):
        event = None
        stripe_signature = request.httprequest.headers.get('Stripe-Signature')

        cr, uid = request.cr, request.session.uid
        endpoint_secret = request.env(cr, uid)['ir.config_parameter'].sudo().get_param('stripe_endpoint_secret')

        if not stripe_signature or not endpoint_secret:
            return json.dumps({'error': 'stripe signature or endpoint secret not found'})

        payload = request.httprequest.data

        try:
            event = stripe.Webhook.construct_event(payload, stripe_signature, endpoint_secret)

            if event.get('type') == 'checkout.session.completed':
                pscs = request.env(cr, uid)['portal.stripe.checkout.session']
                pscs.with_delay().post_session_completion_tasks(session=json.loads(payload))  #<<<-------------
                # pscs.post_session_completion_tasks(session=json.loads(payload))

                return json.dumps({'response': 'Success! Creating Subscription... '})


        except ValueError as e:
            # Invalid payload
            _logger.error(e)
            return json.dumps({'error': 'ValueError occurred'})
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            _logger.error(e)
            return json.dumps({'error': 'Unable to verify Signature'})
        return json.dumps({'error': 'Unknown Error Occurred'})

