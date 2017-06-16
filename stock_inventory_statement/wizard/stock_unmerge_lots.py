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
from openerp.osv import osv, fields
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp import _, api, SUPERUSER_ID, tools
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import netsvc
from datetime import datetime
from lxml import etree
import time

class stock_unmerge_lots(osv.osv_memory):
    _name = "stock.unmerge.lots"
    _description = "UnMerge Lots"
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_unmerge_lots, self).default_get(cr, uid, fields, context=context)
        if 'wiz_warehouse' in context:
            context = dict(context)
            #context['warehouse'] = context['wiz_warehouse']
        if context.get('active_id'):
            stock_prodlot = self.pool.get('stock.production.lot').browse(cr, uid, context['active_id'], context=context)
            if 'product_id' in fields:
                res.update({'product_id': stock_prodlot.product_id.id})
            if 'product_uom' in fields:
                res.update({'product_uom': stock_prodlot.product_id.product_tmpl_id.uom_id.id})
            if 'prod_lot' in fields:
                res.update({'prod_lot' : stock_prodlot.id})
            if 'warehouse_id' in fields:
                res.update({'warehouse_id': context['warehouse']})
            selection_ids = self._create_selections(cr, uid, context['active_id'], context=context)
            if len(selection_ids) == 1:
                res.update({'choice': selection_ids[0]})
        return res
    
    def _create_selections(self, cr, uid, src_lot, context=None):
        ''' 
            Gets all internal location and product's lots has in production quantity
        '''
        #body = u"Gets all internal location and product's lots has in production quantity"
        #logger.notifyChannel(u"[Агуулах][Функциональ][stock.unmerge.lots]", netsvc.LOG_DEBUG, body)
        location_obj = self.pool.get('stock.location')
        prodlot_obj = self.pool.get('stock.production.lot')
        selection_obj = self.pool.get('stock.unmerge.choice')
        lot_obj = prodlot_obj.browse(cr, uid, src_lot, context)
        product = lot_obj.product_id.id
        warehouse = self.pool.get('stock.warehouse').browse(cr, uid, context['warehouse'], context)
        location_ids = tuple(self.pool.get('stock.location').search(cr, uid, 
                        [('location_id','child_of',[warehouse.view_location_id.id])], context=context))
        cr.execute('''
            select 
                sum(qty),
                location_id 
            from 
                stock_quant 
            where 
                product_id = %s 
            and lot_id = %s
            and location_id in %s
            group by lot_id, location_id
            having sum(qty) > 0
            ''',(lot_obj.product_id.id,lot_obj.id,location_ids))
        res = []
        fetched = cr.fetchall()
        for qty, loc in fetched: 
            new_sel = selection_obj.create(cr, uid, {
                    'location_id': loc,
                    'product_qty': qty
            })
            res.append(new_sel)
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(stock_unmerge_lots, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context and context.get('active_model', False) \
            and context['active_model'] == 'stock.production.lot' and context.get('active_id', False) :
            if 'wiz_warehouse' in context:
                context = dict(context)
            selection_ids = self._create_selections(cr, uid, context['active_id'], context=context)
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='choice']")
            domain = "[('id','in',["+ ','.join(map(str,selection_ids)) +"])]"
            for node in nodes:
                node.set('domain', domain)
            res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'qty' : fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_id' : fields.many2one('product.product', 'Product', required=True, select=True),
        'product_uom' : fields.many2one('product.uom','UOM'),
        'line_ids' : fields.one2many('stock.unmerge.lots.lines','lot_id','Production lots', required=True),
        'prod_lot' : fields.many2one('stock.production.lot','Production Lot', select=True, required=True),
        'choice' : fields.many2one('stock.unmerge.choice','Select Location', required=True, ondelete='cascade'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True) 
    }
    
    def split_lot(self, cr, uid, ids, context=None):
        """ To split a lot
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: An ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        return self.split(cr, uid, ids, context.get('active_ids'), context=context)
    
    def split(self, cr, uid, ids, prodlot_ids, context=None):
        """ To split stock moves into production lot
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param move_ids: the ID or list of IDs of stock move we want to split
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        picking_obj = self.pool.get('stock.picking')
        quant_obj = self.pool.get('stock.quant')
        location_obj = self.pool.get('stock.location')
        picking_type_obj = self.pool.get('stock.picking.type')
        data = self.browse(cr, uid, ids[0], context=context)
        inv_location_id = location_obj.search(cr, uid, [('usage','=','inventory')])
        if not inv_location_id:
            raise osv.except_osv(_('Error !'), _('There is no inventory location defined on this company!'))
        prodlot_name = self.pool.get('stock.production.lot').read(cr, uid, prodlot_ids[0], ['name'], context=context)['name']
        inv_location_id = inv_location_id[0]
        splited_qty = 0
        prod_name = data.product_id.name_get(context=context)[0][1]
        stock_moves = []
        for l in data.line_ids:
            if l.existing_name.id == prodlot_ids[0]:
                raise osv.except_osv(_('Error !'), _("You have selected same lot as switching lot!"))
            if l.quantity <= 0:
                raise osv.except_osv(_('Error !'), _("You have entered invalid quantity on %s switching lot!") % l.existing_name.name)
            stock_moves.append( (0,0, {
                'location_id': inv_location_id,
                'location_dest_id': data.choice.location_id.id,
                'product_uom': data.product_id.uom_id.id,
                'product_uom_qty': l.quantity,
                'name': prod_name,
                'product_id': data.product_id.id,
                'product_uos_qty': l.quantity,
                'product_uos': data.product_id.uom_id.id,
                'note': u'%s барааны %s сери дугаар бүхий %s үлдэгдлээс %s сери лүү %s тоо хэмжээгээр шилжүүллээ.' %\
                    (prod_name, prodlot_name, data.choice.product_qty, l.existing_name.name, l.quantity),
            }) )
            splited_qty += l.quantity
        if stock_moves:
            if data.choice.product_qty < splited_qty:
                raise osv.except_osv(_('Error !'), _('Your split quantity is greater than existing stock!'))
            stock_moves.append( (0,0,{
                'location_id': data.choice.location_id.id,
                'location_dest_id': inv_location_id,
                'product_uom': data.product_id.uom_id.id,
                'product_uos_qty': splited_qty,
                'product_uom_qty':splited_qty,
                'product_uos': data.product_id.uom_id.id,
                'name': prod_name,
                'product_id': data.product_id.id,
                'note': u'%s барааны %s сери дугаар бүхий %s үлдэгдлээс %s тоо хэмжээгээр өөр сери лүү шилжүүлэв.' % \
                    (prod_name, prodlot_name, data.choice.product_qty, splited_qty)
            }))
            picking_type_id = picking_type_obj.search(cr, uid, [('code', '=', 'internal')], context=context)
            if not picking_type_id:
                raise osv.except_osv(_('Error !'), _(''))
            picking_type_id = picking_type_id[0]
            pick_id = picking_obj.create(cr, uid, {
                'picking_type_id': picking_type_id,
                'company_id': data.warehouse_id.company_id.id,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'move_type': 'direct',
                'state': 'draft',
                'move_lines': stock_moves
            })
            move_obj = self.pool.get('stock.move')
            wf_service = netsvc.LocalService("workflow")
            
            cr.execute("select id from stock_move where picking_id = %s", (pick_id,))
            move_ids = map(lambda x:x[0], cr.fetchall())
            move_obj.action_confirm(cr, uid, move_ids, context=context)
            move_obj.force_assign(cr, uid, move_ids, context=context)
            wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_confirm', cr)
            picking_obj.action_done(cr, uid, [pick_id], context=context)
            wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_done', cr)
            wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
            
            mod_obj = self.pool.get('ir.model.data')
            form_id = mod_obj._get_id(cr, uid, 'stock', 'view_picking_form')
            form_res = mod_obj.browse(cr, uid, form_id, context=context).res_id
            tree_id = mod_obj._get_id(cr, uid, 'stock', 'vpicktree')
            tree_res = mod_obj.browse(cr, uid, tree_id, context=context).res_id
            return {
                'name': _('Internal Moves'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'view_id': False,
                'views': [(tree_res, 'tree'),(form_res, 'form')],
                'context': context,
                'domain': [('id','=',pick_id)],
                'type': 'ir.actions.act_window',
                'context': '{"search_default_available":0,"search_default_done":1,"search_default_warehouse_id":False}'
             }
        
        return {'type':'ir.actions.act_window.close'}
    
stock_unmerge_lots()

class stock_unmerge_lots_lines(osv.osv_memory):
    _name = "stock.unmerge.lots.lines"
    _description = "Split lines"
    
    _columns = {
        'name': fields.char('Tracking serial', size=64),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'existing_name': fields.many2one('stock.production.lot','Lots', required=True),
        'lot_id': fields.many2one('stock.unmerge.lots', 'Lot'),
    }
    _defaults = { 
        'quantity': lambda *x: 1,
    }
    
    def onchange_existing_name(self, cr, uid, ids, lot_id, context={}):
        res = {}
        if lot_id:
            lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id)
            res = {'value':{'lot_id':lot.id, 'name': lot.name}}
        return res
        
stock_unmerge_lots_lines()

class stock_unmerge_choice(osv.osv_memory):
    _name = "stock.unmerge.choice"
    _description = "Choice of location for unmerge"
    
    def name_get(self, cr, uid, ids, context={}):
        res = []
        for selection in self.browse(cr, uid, ids, context=context) :
            name = selection.location_id.name
            res.append( (selection.id, name) )
        return res
    _rec_name = 'location_id'
    
    _columns = {
        'location_id' : fields.many2one('stock.location','Location', required=True),
        'product_qty' : fields.float('Quantity')
    }
    
stock_unmerge_choice()