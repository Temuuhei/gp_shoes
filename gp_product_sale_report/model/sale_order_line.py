# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cash_payment = fields.Float('Cash payment', default=0)
    card_payment = fields.Float('Card payment', default=0)

    @api.onchange('cash_payment')
    def onChangeCash(self):
        for object in self:
            limit = object.product_uom_qty * object.price_unit
            if limit < object.cash_payment:
                object.cash_payment = limit
            object.card_payment = limit - object.cash_payment

    @api.onchange('card_payment')
    def onChangeCard(self):
        for object in self:
            limit = object.product_uom_qty * object.price_unit
            if limit < object.card_payment:
                object.card_payment = limit
            object.cash_payment = limit - object.card_payment