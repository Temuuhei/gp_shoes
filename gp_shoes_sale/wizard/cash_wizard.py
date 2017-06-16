# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime


class CashManagement(models.TransientModel):
    _name = "cash.management"
    _description = "Cash Management"

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    amount = fields.Float('Amount')
    description = fields.Char('Description')

    @api.onchange('advance_payment_method')
    def confirm(self):
        context = self._context or {}
        if self._context.get('put_in', False):
            cash = self.env['cash'].browse(context.get('active_id'))
            for wizard in self:
                cash.amount += wizard.amount
                self.env['cash.history'].create({
                    'parent_id':cash.id,
                    'amount':wizard.amount,
                    'remaining_amount': cash.amount,
                    'description':wizard.description,
                    'date':datetime.today(),
                    'user':self.env.uid,
                    'action':'in'

                })

        elif self._context.get('take_out', False):
            cash = self.env['cash'].browse(context.get('active_id'))
            for wizard in self:
                if cash.amount < wizard.amount:
                    raise UserError(
                        _('Not enough money in the cash register.'))
                cash.amount -= wizard.amount
                self.env['cash.history'].create({
                    'parent_id': cash.id,
                    'amount': wizard.amount,
                    'remaining_amount': cash.amount,
                    'description': wizard.description,
                    'date': datetime.today(),
                    'user': self.env.uid,
                    'action': 'out'

                })

        return True
