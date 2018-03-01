# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

class StockQuant(models.Model):
    _inherit = "stock.quant"
    # _order = "default_code_integer asc"

    # default_code_integer = fields.Integer(related='product_id.product_tmpl_id.default_code_integer', string="Default code")

class StockMove(models.Model):
    _inherit = "stock.move"
    # _order = "default_code_integer asc"

    # default_code_integer = fields.Integer(related='product_id.product_tmpl_id.default_code_integer', string="Default code")

class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    # _order = "default_code_integer asc"

    # default_code_integer = fields.Integer(related='product_id.product_tmpl_id.default_code_integer', string="Default code")
