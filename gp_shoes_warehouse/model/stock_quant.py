# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

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
            warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', item.location_id.id)], limit=1)
            if first_warehouse == 0:
                first_warehouse = warehouse
                picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', first_warehouse.id),
                                                                      ('code', '=', 'internal')], limit=1)
                outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', first_warehouse.id),
                                                                           ('code', '=', 'outgoing')], limit=1)
            elif first_warehouse.id > 0:
                if not (warehouse == first_warehouse):
                    raise UserError(_("You can create transit order only for one location at time.") )
            stock_move.append((0, 0, {'product_id': item.product_id.id,
                                      'product_uom_qty': 1,
                                      'state': 'draft',
                                      'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                                      'procure_method': 'make_to_stock',
                                      'location_id': item.location_id.id,
                                      'location_dest_id': outgoing_location.id,
                                      'company_id': item.company_id.id,
                                      'date_expected': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'name': item.product_tmp_id,
                                      'scrapped': False,
                                      }))
        if stock_move:
            return \
                {
                    'name': _("Stock Transit Order"),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'target': 'new',
                    'context': {
                        'default_picking_type_id': picking_type.id,
                        'default_location_id': outgoing_location.id,
                        'default_location_dest_id': False,
                        'default_origin':'Тайлбар бичнэ үү...',
                        'default_min_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'default_move_lines': stock_move,
                    }

                }
class Picking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"
    _description = "Transfer"
    _order = "date desc"

    def _default_stock_picking(self):
        # if self.location_id:
            # warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.location_id.id)], limit=1)
        picking_type = self.env['stock.picking.type'].search([('active', '=',True),
                                                              ('code', '=', 'internal'),
                                                             ('warehouse_id', '=',self.env.user.allowed_warehouses[0].id)], limit=1)
        return picking_type

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return self.env.user.allowed_warehouses[0].lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    @api.model
    def _compute_your_picking(self):
        if self:
            for s in self:
                # print '\n\n\ncreate: %s, uid; %s\n\n\n'%(s.create_uid,self.env.uid)
                if s.create_uid.id == self.env.uid:
                    s.inv = False
                    # print '\n\n 1-----------'
                else:
                    if  s.state in ('draft','done'):
                        # print '\n\n 2-----------'
                        s.inv = False
                    else:
                        # print '\n\n 3-----------'
                        s.inv = True

                # print '\n\n\n\n\n\n',s.inv
            return True


    location_id = fields.Many2one(
            'stock.location', "Source Location Zone",
            default=_default_location_id,
            readonly=True, required=True,
            states={'draft': [('readonly', False)]}, domain = "[('usage', '=', 'internal')]")
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain = "[('usage', '=', 'internal')")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Picking Type',
        required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain = "[('code', '=', 'internal')]",
        default= _default_stock_picking)
    inv = fields.Boolean('Create user',compute='_compute_your_picking')

class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"
    _inherit = "stock.inventory"

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return self.env.user.allowed_warehouses[0].lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))


    location_id = fields.Many2one(
        'stock.location', 'Inventoried Location',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain = "[('code', '=', 'internal')]",
        default=_default_location_id)
