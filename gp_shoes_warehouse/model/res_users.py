# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

import odoo.addons.decimal_precision as dp

class Users(models.Model):
    _inherit = ['res.users']
    allowed_cash = fields.Many2many('cash', string = 'Allowed Cash')
    allowed_warehouses = fields.Many2many('stock.warehouse', string='allowed Warehouse')
    allowed_wh = fields.Many2many('stock.warehouse','res_users_sq_wh', string='Размераар хайхын агуулахууд')