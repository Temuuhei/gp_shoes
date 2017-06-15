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

    @api.multi
    def my_function(self):
         first_warehouse = 0
         picking_type = 0
         outgoing_location = 0
         stock_move = []
         for item in self:
             first_warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', item.location_id.id)], limit=1)
             picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',first_warehouse.id),
                                                                   ('code','=','internal')],limit=1)
             outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', first_warehouse.id),
                                                                   ('code', '=', 'outgoing')], limit=1)
             location_id = item.location_id.id
             stock_move.append((0,0, {'product_id': item.product_id.id,
                                'product_uom_qty': int(item.qty),
                                'state': 'draft',
                                'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                                'procure_method': 'make_to_stock',
                                'location_id': item.location_id.id,
                                'location_dest_id': outgoing_location.id,
                                'company_id': item.company_id.id,
                                'date_expected': item.in_date,
                                'date': item.in_date,
                                'name': item.product_tmp_id,
                                'scrapped':False,
                                }))
         return \
            {
             'name':_("Stock Transit Order"),
             'type': 'ir.actions.act_window',
             'view_mode': 'form',
             'res_model': 'stock.picking',
             'target': 'new',
             'context': {
                 'default_picking_type_id':picking_type.id,
                 'default_location_id':self.location_id.id,
                 'default_location_dest_id':False,
                 'default_origin':'temka',
                 'default_move_lines':[line.stock_move for line in self],
             }

             }