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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

class stock_production_lot_wizard(osv.osv_memory):
    _name = "stock.production.lot.wizard"
    _description = "Choose warehouse to open Production Lot tree"
    
    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'product_ids':  fields.many2many('product.product', 'wizard_view_product_prodlot_rel', 'wizard_id', 'product_id', 'Products')
     }
    
    _defaults = {
        'warehouse_id': lambda obj, cr, uid, c: c.get('warehouse', False)
     }
    
    def open_tree(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        objme = self.browse(cr, uid, ids[0], context=context)
        data_obj = self.pool.get('ir.model.data')
        tree_view_id = data_obj.get_object(cr, uid, 'stock', 'view_production_lot_tree').id
        search_view_id = data_obj.get_object(cr, uid, 'stock', 'search_product_lot_filter').id
        form_view_id = data_obj.get_object(cr, uid, 'stock', 'view_production_lot_form').id
        locations = []
        lot_ids = []
        prod_ids = []
        locations = self.pool.get('stock.location').search(cr, uid, 
            [('usage', '=', 'internal'),('location_id','child_of',[objme.warehouse_id.view_location_id.id])], context=context)
        if objme.product_ids:
            prod_ids = map(lambda x: x.id, objme.product_ids)
        else:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('type','in',['product','consu'])], context=context)
        if locations:
            cr.execute('''select
                    lot_id
                from
                    stock_quant
                where
                    location_id IN %s and lot_id is not null and
                    product_id in %s
                group by lot_id''',(tuple(locations),tuple(prod_ids)))
            lot_ids = map(lambda x:x[0], cr.fetchall())
        if not lot_ids:
            lot_ids = [-1]
        context.update({
                'full':'1',"search_default_available":1,
                "wiz_warehouse":objme.warehouse_id.id,
                'warehouse': objme.warehouse_id.id
        })
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.production.lot',
            'name': _("Production lots"),
            'views': [(tree_view_id,'tree'),(form_view_id,'form'),(search_view_id,'search')],
            'type': 'ir.actions.act_window',
            'help': _("This is the list of all the production lots (serial numbers) you recorded. When you select a lot, you can get the upstream or downstream traceability of the products contained in lot. By default, the list is filtred on the serial numbers that are available in your warehouse but you can uncheck the 'Available' button to get all the lots you produced, received or delivered to customers."),
            'domain': [('id','in',lot_ids)],
            'context': context
         }
    
stock_production_lot_wizard()    