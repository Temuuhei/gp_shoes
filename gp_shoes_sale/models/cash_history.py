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

class cash_history(models.Model):
    _name = "cash.history"
    parent_id = fields.Many2one('cash',string = 'Parent')
    amount = fields.Float(string='Amount')
    description = fields.Char(string='Description')
    date = fields.Datetime(string='Action Date')
    user = fields.Many2one('res.users', string='Action User')



    

