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

    def action_confirm(self):
        print'\n\n confirm \n\n'

        # data_obj = self.pool.get('ir.model.data')
        # form_data_id = data_obj._get_id(cr, uid, 'res_partner_extended', 'confirm_unlink_res_partner_bank_wizard_form')
        # form_view_id = False
        # if form_data_id:
        #     form_view_id = data_obj.browse(cr, uid, form_data_id, context=context).res_id
        # return {
        #     'name': 'Confirm removing bank account',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'view_id': False,
        #     'views': [(form_view_id, 'form'), ],
        #     'res_model': 'confirm.unlink.res.partner.bank.wizard',
        #     'type': 'ir.actions.act_window',
        #     'target': 'new',
        #     'flags': {'form': {'action_buttons': True}, }
        # }


        super(sale_order, self).action_confirm()
