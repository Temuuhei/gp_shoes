# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


class SaleOrderCashRegister(models.TransientModel):
    _name = "sale.order.cash.register"
    _description = "Sales Order Cash Register"

    amount = fields.Float('Amount', help="The amount paid in cash.")
    amount_card = fields.Float('Amount', help="The amount paid in cash.")
    cash = fields.Many2one('cash', string = 'Бэлэн мөнгө',domain="[('type', '=', 'cash')]")
    card = fields.Many2one('cash', string = 'Карт',domain="[('type', '=', 'card')]")


    def confirm(self):
        context = self._context or {}
        so = self.env['sale.order'].browse(context.get('active_id'))
        for wizard in self:
            context = self._context or {}
            # if so.payment_term_id.type == mixed:
            if wizard.amount < 0:
                raise UserError(
                    _('Amount can not be less than zero.'))
            # if wizard.amount == 0:
            #     return True
            if wizard.cash and wizard.amount > 0:
                wizard.cash.amount += wizard.amount
                self.env['cash.history'].create({
                    'parent_id': wizard.cash.id,
                    'amount': wizard.amount,
                    'remaining_amount': wizard.cash.amount,
                    'description': so.name + u' дугаартай борлуулалтаас [%s]'%so.id + u' [' + so.payment_term_id.type + u']',
                    'date': datetime.today(),
                    'user': self.env.uid,
                    'action': 'in'
                })
            if wizard.card and wizard.amount_card > 0:
                wizard.card.amount += wizard.amount_card
                self.env['cash.history'].create({
                    'parent_id': wizard.card.id,
                    'amount': wizard.amount_card,
                    'remaining_amount': wizard.card.amount,
                    'description': so.name + u' дугаартай борлуулалтаас [%s]' % so.id + u' [' + so.payment_term_id.type + u']',
                    'date': datetime.today(),
                    'user': self.env.uid,
                    'action': 'in'
                })

            so.write({'cash_pay':wizard.amount,
                      'card_pay': wizard.amount_card})
            so.action_confirm()
        return True