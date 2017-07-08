# -*- coding: utf-8 -*-
##############################################################################
#
#    Game of Code LLC, Enterprise Management Solution
#    Copyright Game of Code LLC (C) 2017 . All Rights Reserved
#
#    Address :
#    Email :
#    Phone :
#
##############################################################################

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp

class SaleOrder(models.Model):
    _inherit = "sale.order"
    def _check_discount(self):
        for order in self:
            discount = False
            if order.order_line:
                for line in order.order_line:
                    if not line.price_unit == line.price_original:
                        discount = True
                        order.check_discount = True
                        break

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)
    discount_manager = fields.Many2one('res.users', string='Discount Manager')
    check_discount = fields.Boolean(compute=_check_discount, string='Check Discount')
    cash_pay = fields.Float(string='Бэлэн')
    card_pay = fields.Float(string='Карт')

    def custom_confirm(self):
        for order in self:
            if order.payment_term_id and order.payment_term_id.type == 'cash':
                view = self.env['ir.model.data'].get_object_reference('gp_shoes_sale', 'view_sale_order_cash_register')[1]
                return {'name': _('Sales cash Wizard'),
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'view_mode': 'form',
                     'res_model': 'sale.order.cash.register',
                     'views': [(view, 'form')],
                     'view_id': view,
                     'target': 'new',
                     'res_id': False,
                     }
            elif order.payment_term_id and order.payment_term_id.type == 'card':
                view = self.env['ir.model.data'].get_object_reference('gp_shoes_sale', 'view_sale_order_cash_register_card')[1]
                return {'name': _('Sales cash Wizard'),
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'view_mode': 'form',
                     'res_model': 'sale.order.cash.register',
                     'views': [(view, 'form')],
                     'view_id': view,
                     'target': 'new',
                     'res_id': False,
                     }
            elif order.payment_term_id and order.payment_term_id.type == 'mixed':
                view = self.env['ir.model.data'].get_object_reference('gp_shoes_sale', 'view_sale_order_cash_register_mixed')[1]
                return {'name': _('Sales cash Wizard'),
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'view_mode': 'form',
                     'res_model': 'sale.order.cash.register',
                     'views': [(view, 'form')],
                     'view_id': view,
                     'target': 'new',
                     'res_id': False,
                     }
                order.action_confirm()
            # elif not order.payment_term_id:
            #     # order.card_pay = order.amount_total
            order.action_confirm()


