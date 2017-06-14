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
    cash = fields.Many2one('cash', string = 'Cash')

    def confirm(self):
        context = self._context or {}
        so = self.env['sale.order'].browse(context.get('active_id'))
        for wizard in self:
            context = self._context or {}
            # if so.payment_term_id.type == mixed:
            if wizard.amount < 0:
                raise UserError(
                    _('Amount can not be less than zero.'))
            if wizard.amount == 0:
                return True
            if wizard.amount > 0:
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
        so.action_confirm()
        return True