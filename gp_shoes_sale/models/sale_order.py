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
    _order = 'date desc'
    def _check_discount(self):
        for order in self:
            discount = False
            if order.order_line:
                for line in order.order_line:
                    if not line.price_unit == line.price_original:
                        discount = True
                        order.check_discount = True
                        break


    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    def _default_payment_term(self):
        payment_term_id = self.env['account.payment.term'].search([('default','=',True)], limit=1)
        return payment_term_id

    def _default_partner(self):
        partner_ids = self.env['res.partner'].search([('customer','=',True)],limit=1)[0]
        return partner_ids


    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)
    date = fields.Datetime(string='Order Date', required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False,default=fields.Datetime.now())
    discount_manager = fields.Many2one('res.users', string='Discount Manager')
    check_discount = fields.Boolean(compute=_check_discount, string='Check Discount')
    cash_pay = fields.Float(string='Бэлэн')
    card_pay = fields.Float(string='Карт')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term',required = True, oldname='payment_term',
                                      default =_default_payment_term)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True,
                                 states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True,
                                 change_default=True, index=True, track_visibility='always')

    @api.multi
    @api.onchange('partner_id','warehouse_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        # if self.partner_id :
        #     values['payment_term_id'] = self.env['account.payment.term'].search([('default','=',True)])[0]
        allowed_whs = self.env.user.allowed_warehouses
        if allowed_whs:
            for a in allowed_whs:
                allow_wh = self.env['stock.warehouse'].search([('id', '=', a.id)])[0]
                values['warehouse_id'] = allow_wh[0]
        self.update(values)

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


