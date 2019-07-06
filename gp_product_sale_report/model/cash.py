# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class cash(models.Model):
    _name = "cash"
    _inherit = "cash"

    warehouse = fields.Many2one('stock.warehouse', 'Warehouse')