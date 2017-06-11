# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class SaleOrderCashRegister(models.TransientModel):
    _name = "sale.order.cash.register"
    _description = "Sales Order Cash Register"

    amount = fields.Float('Amount', help="The amount paid in cash.")
    cash = fields.Many2one('cash', string = 'Cash')

    def confirm(self):
        for wizard in self:
            context = self._context or {}
            order = self.env['sale.order'].browse(context.get('active_id'))
            cash = self.env['cash'].browse(wizard.cash)
            if wizard.amount < 0:
                raise UserError(
                    _('Not enough money in the cash register.'))

            # return {
            #     'name': 'Down payment',
            #     'type': 'service',
            #     'invoice_policy': 'order',
            #     'property_account_income_id': self.deposit_account_id.id,
            #     'taxes_id': [(6, 0, self.deposit_taxes_id.ids)],
            # }
