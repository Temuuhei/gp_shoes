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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class change_standard_price(osv.osv_memory):
    _inherit = "stock.change.standard.price"
    _description = "Change Standard Price"
    
    def _is_cost_per_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        return user.company_id.store_cost_per_warehouse
    
    _columns = {
        'old_price': fields.float('Old Price', readonly=True, digits_compute=dp.get_precision('Product Price')),
        'new_price': fields.float('Price', required=True, digits_compute=dp.get_precision('Product Price'),
            help="If cost price is increased, stock variation account will be debited "
            "and stock output account will be credited with the value = (difference of amount * quantity available).\n"
            "If cost price is decreased, stock variation account will be creadited and stock input account will be debited."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'warehouse_required': fields.boolean('Warehouse required?'),
        'qty_available': fields.float('Stock on hand', readonly=True),
        'total_diff': fields.float('Total Different', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Account Journal'),
        'inventory_location_id': fields.many2one('stock.location', 'Inventory Location')
    }
    
    _defaults = {
        'warehouse_required': _is_cost_per_warehouse,
    }
    
    def onchange_warehouse(self, cr, uid, ids, warehouse_id=False, new_price=False, context=None):
        if not warehouse_id:
            return {'value':{'old_price': 0, 'total_diff': 0}}
        
        if context is None:
            context = {}
        if not context.get('active_id', False):
            return {'value':{'old_price': 0, 'total_diff': 0}}
        
        if not new_price:
            new_price = 0
        
        product_id = context['active_id']
        if context.get("active_model") == 'product.product':
            product_pool = self.pool.get('product.product')
            old_price = product_pool.price_get(cr, uid, [product_id], ptype='standard_price',
                        context=dict(context, warehouse=warehouse_id))[context['active_id']]
            qty_available = product_pool.read(cr, uid, product_id, ['qty_available'],
                    context=dict(context, warehouse=warehouse_id))['qty_available']
        else:
            product_pool = self.pool.get('product.template')
            prod = product_pool.browse(cr, uid, product_id)
            old_price = product_pool._price_get(cr, uid, [prod], ptype='standard_price',
                        context=dict(context, warehouse=warehouse_id))[prod.id]
            
            qty_available = sum( variant['qty_available'] for variant in self.pool.get('product.product').read(cr, uid, 
                    map(lambda x:x.id, prod.product_variant_ids), ['qty_available'],
                    context=dict(context, warehouse=warehouse_id)))
        
        return {'value':{'old_price': old_price, 'qty_available': qty_available, 
                'total_diff': (new_price - old_price) * qty_available,
                'new_price': old_price}}
    
    def onchange_new_price(self, cr, uid, ids, new_price=0, old_price=0, qty_available=0, context=None):
        return {'value':{'total_diff': qty_available * (new_price - old_price)}}

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        if context.get("active_model") == 'product.product':
            product_pool = self.pool.get('product.product')
        else:
            product_pool = self.pool.get('product.template')
        
        res = super(change_standard_price, self).default_get(cr, uid, fields, context=context)

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        warehouse_required = False
        warehouse_id = False
        if user.company_id.store_cost_per_warehouse:
            warehouse_required = True
            warehouse_id = (user.allowed_warehouses and user.allowed_warehouses[0].id) or False
            if context.get("active_model") == 'product.product':
                old_price = product_pool.price_get(cr, uid, [context['active_id']], ptype='standard_price',
                        context=dict(context, warehouse=warehouse_id))[context['active_id']]
            else:
                prod_temp = product_pool.browse(cr, uid, context['active_id'])
                old_price = product_pool._price_get(cr, uid, [prod_temp], ptype='standard_price',
                        context=dict(context, warehouse=warehouse_id))[prod_temp.id]
            if 'new_price' in fields:
                res['new_price'] = old_price
            if 'old_price' in fields:
                res['old_price'] = old_price
            
        else:
            stock_on_hand = product_pool.read(cr, uid, context['active_id'], ['qty_available'])['qty_available']
            
            if 'qty_available' in fields:
                res['qty_available'] = stock_on_hand
        
        if 'warehouse_required' in fields:
            res.update({'warehouse_required': warehouse_required})
        if 'warehouse_id' in fields:
            res.update({'warehouse_id': warehouse_id})
        
        return res

    def change_price(self, cr, uid, ids, context=None):
        """ Changes the Standard Price of Product.
            And creates an account move accordingly.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """

        company = self.pool.get('res.users').browse(cr, uid, uid).company_id        
        if company.store_cost_per_warehouse == False:
            if context is None:
                context = {}
            rec_id = context.get('active_id', False)
            assert rec_id, _('Active ID is not set in Context.')
            if context.get("active_model") == 'product.product':
                prod_obj = self.pool.get('product.product')
                rec_id = prod_obj.browse(cr, uid, rec_id, context=context).product_tmpl_id.id
            prod_obj = self.pool.get('product.template')
            
            res = self.browse(cr, uid, ids, context=context)
            
            prod_obj.do_change_standard_price(cr, uid, [rec_id], res[0].new_price, context)
            return {'type': 'ir.actions.act_window_close'}
        else:
            print 'changing price...'
            if context is None:
                context = {}
            rec_id = context.get('active_id', False)
            assert rec_id, _('Active ID is not set in Context.')
            if context.get("active_model") == 'product.template':
                prod_obj = self.pool.get('product.template')
                template_id = rec_id
                prod = prod_obj.browse(cr, uid, rec_id, context=context)
                rec_id = prod.product_variant_ids[0].id
                uom_id = prod.uom_id.id
            else:
                prod = self.pool.get('product.product').browse(cr, uid, rec_id, context=context)
                uom_id = prod.uom_id.id
                template_id = prod.product_tmpl_id.id
            
            form = self.browse(cr, uid, ids[0], context=context)
            
            if form.warehouse_required:
                values = self.onchange_warehouse(cr, uid, ids, form.warehouse_id.id, form.new_price, context=context)['value']
                old_price = values['old_price']
                total_diff = values['total_diff']
                warehouse = form.warehouse_id
            else:
                old_price = form.old_price
                total_diff = form.qty_available * (form.new_price - form.old_price)
                warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [])[0]
                warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id)
                
            
            # Тооллого үүсгэх
            inventory_obj = self.pool.get('stock.inventory')
            inventory_line_obj = self.pool.get('stock.inventory.line')
            prod_lot_id = False
            if prod.track_all or prod.track_incoming or prod.track_outgoing:
                lots = self.pool.get('stock.production.lot').search(cr, uid, [('product_id','=',prod.id)],
                                                 order='create_date desc', limit=1)
                prod_lot_id = (lots and lots[0]) or False
            inventory_id = inventory_obj.create(cr, uid, {
                    'location_id': form.inventory_location_id.id,
                    'state': 'draft',
                    'filter': 'partial',
                    'warehouse_id': warehouse.id,
                    'specification': _('Standard Price of %s product has changed')% prod.name_get(context=context)[0][1],
                    'line_ids': [(0,0,{
                        'location_id': warehouse.lot_stock_id.id,
                        'product_id': rec_id,
                        'product_uom_id': uom_id,
                        'prod_lot_id':prod_lot_id
                    }), (0,0,{
                        'location_id': warehouse.lot_stock_id.id,
                        'product_id': rec_id,
                        'product_uom_id': uom_id,
                        'prod_lot_id':prod_lot_id
                    })]
            }, context=context)
            
            inventory_obj.prepare_inventory(cr, uid, [inventory_id], context=context)
            inventory = inventory_obj.browse(cr, uid, inventory_id, context=context)
            lines = inventory.line_ids
            theoretical_qty = lines[0].theoretical_qty
            lines[0].write({'product_qty':theoretical_qty+1})
            lines[1].write({'product_qty':theoretical_qty})
            inventory_obj.action_check(cr, uid, [inventory_id], context=context)
            cr.execute("update stock_inventory_line set theoretical_qty=%s where id = %s" %\
                          (theoretical_qty+1,lines[1].id))
            #lines[1].write({'product_qty':theoretical_qty,'theoretical_qty':theoretical_qty+1})
            lines[1].refresh()
            inventory_line_obj._resolve_inventory_line(cr, uid, lines[1], context=context)
            inventory.refresh()
            for move in inventory.move_ids:
                if total_diff > 0:
                    if move.location_dest_id.usage == 'internal':
                        move.write({'price_unit':total_diff}, context=context)
                    else:
                        move.write({'price_unit':0}, context=context)
                else:
                    if move.location_id.usage == 'internal':
                        move.write({'price_unit':-total_diff}, context=context)
                    else:
                        move.write({'price_unit':0}, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=dict(context,standard_price_change=True))
            
            self.pool.get('product.template').write(cr, uid, [template_id], 
                        {'standard_price': form.new_price}, context=dict(context,warehouse=warehouse.id))
            
            
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')

            result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_inventory_form')
            id = result and result[1] or False
            result = act_obj.read(cr, uid, [id], context=context)[0]

            #compute the number of delivery orders to display
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_inventory_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inventory_id
            
            return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
