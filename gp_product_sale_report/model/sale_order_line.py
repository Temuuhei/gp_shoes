# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cash_payment = fields.Float('Cash payment', default=0)
    card_payment = fields.Float('Card payment', default=0)