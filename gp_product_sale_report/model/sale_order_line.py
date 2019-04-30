# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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


    @api.model
    def create(self, values):
        create = super(SaleOrderLine, self).create(values)
        quant = self.env['stock.quant'].search([('location_id', '=', create.order_id.warehouse_id.lot_stock_id.id),
                                                ('product_id', '=', create.product_id.id)])
        qt = 0
        for q in quant:
            qt += q.qty
        if not quant or qt <= 0 or qt < create.product_uom_qty:
            raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s') % create.name, )
        if not create.cash_payment and not create.card_payment:
            raise ValidationError(_('You cannot create card and cash payment with 0!'))
        return create

    @api.multi
    def write(self, values):
        write = super(SaleOrderLine, self).write(values)
        if "product_uom_qty" in values or "product_id" in values:
            quant = self.env['stock.quant'].search([('location_id', '=', self.order_id.warehouse_id.lot_stock_id.id),
                                                    ('product_id', '=', self.product_id.id)])
            if not quant or quant.qty <= 0 or quant.qty < self.product_uom_qty:
                raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s')% write.name)
        if not self.cash_payment and not self.card_payment:
            raise ValidationError(_('You cannot create card and cash payment with 0!'))
        return write