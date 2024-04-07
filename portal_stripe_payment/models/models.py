# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class StripeCheckoutSession(models.Model):
    _name = 'portal.stripe.checkout.session'
    name = fields.Char()
    user_id = fields.Many2one('res.users', 'Client User')
    session_id = fields.Char()
    session_completed = fields.Boolean(default=False)
    completion_payload = fields.Text()

    def post_session_completion_tasks(self, session=None):
        if session is None:
            session = {}
            _logger.error('session is None, Exiting')

        session_object = session.get('data', {'object': False}).get('object')
        if session_object:
            session_id = session_object.get('id')
            client_reference_id = session_object.get('client_reference_id')
            if session_id and client_reference_id:
                db_session = self.sudo().search([('session_id', '=', session_id), ('session_completed', '=', False),
                                                 ('user_id', '=', int(client_reference_id))], limit=1)
                if db_session:  # <<<----------
                    db_session.sudo().write({'completion_payload': str(session), 'session_completed': True})
                    stripe_sub_id = session_object.get('subscription')
                    if stripe_sub_id:
                        self.env['sale.subscription'].sudo().create_from_stripe_api(user_id=client_reference_id,
                                                                                    stripe_sub_id=stripe_sub_id)
                else:
                    _logger.error('Unable to find stripe checkout session on db')
            else:
                _logger.error('Session id is not found, Exiting')
        else:
            _logger.error('session object not found, Exiting')


