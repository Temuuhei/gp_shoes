from datetime import datetime

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class Quant(models.Model):
    """ Quants are the smallest unit of stock physical instances """
    _name = "stock.quant"
    _inherit = "stock.quant"
    _description = "Quants"

    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, ondelete="restrict", readonly=True, required=True)
    product_tmp_id = fields.Char(string="Product related", related='product_id.product_tmpl_id.name',store=True )

class PickingType(models.Model):
    """ The picking type determines the picking view """
    _name = "stock.picking"
    _inherit = "stock.picking"
    _description = "Stock Picking"

    @api.multi
    def my_function(self, cr, uid, ids, context=None):
         print'Temkaaaaaaaa\n\n\n\n\n', ids
         for item in self:
             # do something with selected records

            print'Temkaaaaaaaa\n\n\n\n\n',item.product_id

