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

class cash(models.Model):
    _name = "cash"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    name = fields.Char(string='Name')
    amount = fields.Float(string='Amount')
    note = fields.Text(string='Note')
    history = fields.One2many('cash.history','parent_id',string='Note')

    @api.multi
    def take_money(self):
        for i in self:
            print'\n\n aaaaaaaa %s \n\n' % i
        print'\n\n take_money %s \n\n'%self
        # create history line and update amount




