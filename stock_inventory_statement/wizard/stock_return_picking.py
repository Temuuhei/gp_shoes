# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-2014 Monos Group (<http://monos.mn>).
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
import time
from datetime import datetime, date

class stock_return_picking_fill(osv.osv_memory):
    _name = "stock.return.picking.fill"
    _description = "Stock Return Picking Fill"
    
    _columns = {
        'return_id': fields.many2one('stock.return.picking', 'Return Wizard'),
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'move_ids': fields.many2many('stock.move', 'stock_return_pciking_move_rel', 'wizard_id', 'move_id', 'Stock Moves')
    }
    
    _defaults = {
        'return_id': lambda obj, cr, uid, c={}:c.get('wizard_id',False),
        'picking_id': lambda obj, cr, uid, c={}:c.get('picking_id',False)
    }
    
    def create(self, cr, uid, vals, context=None):
        return super(stock_return_picking_fill, self).create(cr, uid, vals, context=context)
    
    def stock_fill(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        fill = self.browse(cr, uid, ids[0], context=context)
        line_obj = self.pool.get('stock.return.picking.line')
        if fill.move_ids:
            for m in fill.move_ids:
                values = line_obj.onchange_move(cr, uid, [], m.id, context=context)
                
                values['value'].update({'move_id': m.id,
                                         'picking_id': fill.picking_id and fill.picking_id.id or False,
                                         'wizard_id': fill.return_id.id})
                line_obj.create(cr, uid, values['value'], context=context)
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                    'stock', 'view_stock_return_picking_form')[1]
        return {'name': _('Stock Return Picking'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.return.picking',
                    'views': [(view, 'form')],
                    'view_id': view,
                    'target': 'new',
                    'res_id': fill.return_id.id,
                    'context': context }
    
class stock_return_picking_line(osv.osv_memory):
    _inherit = "stock.return.picking.line"
    
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'allowed_qty': fields.float('Possible for Return')
    }
    
    _defaults = {
        'picking_id': lambda obj, cr, uid, c={}:c.get('picking_id',False),
        'allowed_qty': 0
    }
    
    def onchange_move(self, cr, uid, ids, move_id, context=None):
        if context is None:
            context = {}
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get('product.uom')
        move_obj = self.pool.get('stock.move')
        values = {}
        if move_id:
            move = move_obj.browse(cr, uid, move_id, context=context)
            qty = 0
            quant_search = quant_obj.search(cr, uid, [('history_ids','=',move.id),
                                ('qty','>',0),
                        ('location_id','child_of',[move.location_dest_id.id])], context=context)
            for quant in quant_obj.browse(cr, uid, quant_search, context=context):
                if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                    qty += quant.qty
            qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
            values['value'] = {'product_id': move.product_id.id,
                               'quantity': qty,
                               'allowed_qty':qty}
        return values
    
    def onchange_qty(self, cr, uid, ids, quantity=0, allowed_qty=0, context=None):
        if context is None:
            context = {}
        return {'value': {'quantity':min(allowed_qty, quantity)}}
    
class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking'),
        'stock_return_check': fields.boolean('Stock Return Type Check'),
        'stock_return_category': fields.many2one('stock.return.type', string='Stock Return Type', help="The stock return type."),
        'fill': fields.boolean('Fill')
    }

    _defaults = {
        'picking_id': lambda obj, cr, uid, c={}:c.get('active_id',False),
        'fill': False,
        'invoice_state': '2binvoiced',
    }
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        sale_obj = self.pool.get('sale.order')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        if pick and pick.group_id:
            res.update({'invoice_state': '2binvoiced'})
            sale_ids = sale_obj.search(cr, uid, [('procurement_group_id','=',pick.group_id.id)], context=context)
            if 'stock_return_category' in fields:
                if sale_ids and pick.picking_type_id.code == 'outgoing':
                    res.update({'stock_return_check': True})
                else:
                    res.update({'stock_return_check': False})
        
        if 'product_return_moves' in fields:
            for move in res['product_return_moves']:
                move.update({'allowed_qty': move['quantity']})            

        uom_obj = self.pool.get('product.uom')                
        quant_obj = self.pool.get("stock.quant")
        chained_move_exist = False
        result1 = []
        if pick:
            if pick.state != 'done':
                raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Done!"))

            for move in pick.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quant_search = quant_obj.search(cr, uid, [('history_ids', 'in', move.id),('location_id', 'child_of', move.location_dest_id.id)], context=context)
                for quant in quant_obj.browse(cr, uid, quant_search, context=context):
                    if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        qty += quant.qty
                qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
                result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})        
        res.update({'product_return_moves': result1})
        if 'product_return_moves' in fields:
            for move in res['product_return_moves']:                
                move.update({'allowed_qty': move['quantity']})                
        return res
    
    def fill_action(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                    'l10n_mn_stock', 'stock_return_fill_form')[1]
        context = dict(context.items(), wizard_id=ids[0])
        return {'name': _('Stock Return Picking'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.return.picking.fill',
                    'views': [(view, 'form')],
                    'view_id': view,
                    'target': 'new',
                    'res_id': False,
                    'context': context }
    
    def clear_action(self, cr, uid, ids, context=None):
        context = context or {}
        line_obj = self.pool.get('stock.return.picking.line')
        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.product_return_moves:
                line_ids = map(lambda x:x.id, wiz.product_return_moves)
                line_obj.unlink(cr, uid, line_ids, context=context)
            self.write(cr, uid, [wiz.id], {'fill':True}, context=context)
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                    'stock', 'view_stock_return_picking_form')[1]
        return {'name': _('Stock Return Picking'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.return.picking',
                    'views': [(view, 'form')],
                    'view_id': view,
                    'target': 'new',
                    'res_id': ids[0],
                    'context': context }
    
    def _create_returns(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0], context=context)
        new_picking, picking_type_id = super(stock_return_picking, self)._create_returns(cr, uid, ids, context=context)
        if data.stock_return_check == True:
            pick_obj = self.pool.get("stock.picking")
            move_obj = self.pool.get("stock.move")
            move_ids = [x.id for x in pick_obj.browse(cr, uid, new_picking, context=context).move_lines]
            pick_obj.write(cr, uid, new_picking, {'stock_return_type_id': data.stock_return_category.id})
        return new_picking, picking_type_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: