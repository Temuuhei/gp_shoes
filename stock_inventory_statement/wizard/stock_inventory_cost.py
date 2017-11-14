# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import date, datetime
import time

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

class stock_inventory_cost(osv.osv_memory):
    _name = "stock.inventory.cost"
    _description = "Stock Inventory Income Cost"
    
    _columns = {
        'inventory_id': fields.many2one('stock.inventory', 'Inventory', required=True),
        'lines':  fields.one2many('stock.inventory.cost.line', 'wizard_id', 'Inventory Incomes')
    }
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_inventory_cost, self).default_get(cr, uid, fields, context=context)
        product_obj = self.pool.get('product.product')
        inventory = self.pool.get('stock.inventory').browse(cr, uid, context['active_id'])
        if 'inventory_id' in fields:
            res['inventory_id'] = inventory.id
        if 'lines' in fields and inventory.state == 'counted':
            lines = []
            prods = map(lambda x:x.product_id.id, inventory.move_ids)
            prices = product_obj.price_get(cr, uid, prods, ptype='standard_price',
                    context=dict(context,warehouse=inventory.warehouse_id.id))
            for move in inventory.move_ids:
                if move.location_id.usage == 'inventory':
                    lines.append((0,0, {
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom': move.product_uom.id,
                        'prodlot_id': move.restrict_lot_id.id,
                        'product_qty': move.product_uom_qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'price_unit': prices.get(move.product_id.id, 0)
                    }))
            
            res['lines'] = lines
        return res
    
    def process(self, cr, uid, ids, context=None):
        wiz = self.browse(cr, uid, ids[0], context=context)
        for line in wiz.lines:
            if line.move_id.state <> 'done':
                line.move_id.write({'price_unit': line.price_unit})
        
        return True
    
class stock_inventory_cost_line(osv.osv_memory):
    _name = 'stock.inventory.cost.line'
    _description = 'Stock Inventory Income Cost Line'
    
    _columns = {
        'move_id': fields.many2one('stock.move', 'Move', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom': fields.many2one('product.uom', 'UOM', readonly=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production Lot', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location src', readonly=True),
        'location_dest_id': fields.many2one('stock.location', 'Location dest', readonly=True),
        'price_unit': fields.float('Unit Cost', required=True),
        'wizard_id': fields.many2one('stock.inventory.cost', 'Wizard', ondelete='cascade')
    }