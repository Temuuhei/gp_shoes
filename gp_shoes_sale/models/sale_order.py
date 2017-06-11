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

class sale_order(models.Model):
    _inherit = "sale.order"
    discount_manager = fields.Many2one('res.users', string='Discount Manager')

    def custom_confirm(self):
        print'\n custom confirm \n'
        for order in self:
            if order.payment_term_id and not order.payment_term_id.type == 'card':
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
            if order.payment_term_id.type == 'card' or not order.payment_term_id:
                order.action_confirm()


