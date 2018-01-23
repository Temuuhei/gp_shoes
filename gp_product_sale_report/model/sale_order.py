# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def custom_confirm(self):
        for order in self:
            cash_amount = 0
            card_amount = 0
            cashes = self.env['cash'].search([('warehouse', '=', order.warehouse_id.id)])
            for order_line in order.order_line:
                cash_amount += order_line.cash_payment
                card_amount += order_line.card_payment

            if cashes:
                for cash in cashes:
                    if cash.type == 'cash' and cash_amount:
                        cash.history.create({
                            'parent_id': cash.id,
                            'amount': cash_amount,
                            'remaining_amount': cash.amount,
                            'description': order.name + u' дугаартай борлуулалтаас [%s]' % order.id + u' [' + order.payment_term_id.type + u']',
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'in'
                        })
                    if cash.type == 'card' and card_amount:
                        cash.history.create({
                            'parent_id': cash.id,
                            'amount': card_amount,
                            'remaining_amount': cash.amount,
                            'description': order.name + u' дугаартай борлуулалтаас [%s]' % order.id + u' [' + order.payment_term_id.type + u']',
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'in'
                        })

                order.write({'cash_pay': cash_amount, 'card_pay': card_amount})
                order.action_confirm()
                #     Борлуулалтаас үүссэн Барааны хөдөлгөөнийг шууд батлах
                stock_picking = self.env['stock.picking'].search([('origin', '=', order.name)])
                if stock_picking:
                    for s in stock_picking:
                        wiz_act = s.do_new_transfer()
                        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                        wiz.process()
                        print'Automat confirmed of Stock Picking'