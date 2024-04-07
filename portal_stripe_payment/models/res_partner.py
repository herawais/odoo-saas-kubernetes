# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'
    related_stripe_id = fields.Char()
