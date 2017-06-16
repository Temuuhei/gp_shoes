# -*- encoding: utf-8 -*-
##############################################################################
#
#    USI-ERP, Enterprise Management Solution    
#    Copyright (C) 2007-2009 USI Co.,ltd (<http://www.usi.mn>). All Rights Reserved
#    $Id:  $
#
#    ЮүЭсАй-ЕРП, Байгууллагын цогц мэдээлэлийн систем
#    зохиогчийн эрх авсан 2007-2010 ЮүЭсАй ХХК (<http://www.usi.mn>). 
#
#    Зохиогчийн зөвшөөрөлгүйгээр хуулбарлах ашиглахыг хориглоно.
#
#    Харилцах хаяг :
#    Э-майл : info@usi.mn
#    Утас : 976 + 70151145
#    Факс : 976 + 70151146
#    Баянзүрх дүүрэг, 4-р хороо, Энхүүд төв,
#    Улаанбаатар, Монгол Улс
#
#
##############################################################################

from openerp.osv import fields, osv, orm
from lxml import etree
from openerp.tools import mute_logger
import time
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from datetime import datetime

class stock_fill_easy(osv.osv_memory):
    _name = 'stock.fill.easy'
    _description = 'Stock Fill Easy'
    
    def _get_availability(self, cr, uid, ids, name, args, context=None):
        res = {}
        for o in self.browse(cr, uid, ids, context=context):
            res[o.id] = o.qty
        return res
    
    _columns = {
        'transit_id': fields.many2one('stock.transit.order', 'Parent Transit Order', ondelete='cascade'),
        'consume_id': fields.many2one('stock.consume.order', 'Parent Consume Order', ondelete='cascade'),
        'scan_field':   fields.char('Scan Field', size=13),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'qty': fields.float('Quantity', required=True),
        'availability': fields.function(_get_availability, string='Available Qty', type="float"),
        #'lines': fields.one2many('stock.fill.inventory.line', 'fill_id', 'Lines')
    }
    
    def _get_transit(self, cr, uid, context=None):
        res = False
        context = context or {}
        if 'active_id' in context and context['active_id'] and context['active_model'] == 'stock.transit.order':
            return context['active_id']
        return res
    
    def _get_consume(self, cr, uid, context=None):
        res = False
        context = context or {}
        if 'active_id' in context and context['active_id'] and context['active_model'] == 'stock.consume.order':
            return context['active_id']
        return res
    
    def _get_warehouse(self, cr, uid, context=None):
        if context['warehouse_id']:
            return context['warehouse_id']
        return False
    
    def view_init(self, cr, uid, fields_list, context=None):
        """
         Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view with new columns.
        """
        if context is None:
            context = {}
        #res = osv.TransientModel.view_init(cr, uid, fields_list, context=context)
        res = super(stock_fill_easy, self).view_init(cr, uid, fields_list, context=context)
        if len(context.get('active_ids',[])) > 1:
            raise osv.except_osv(_('Error!'), _('You cannot perform this operation on more than one Procurement Order.'))
        
        return res
    
    _defaults = {
        'transit_id': _get_transit,
        'consume_id': _get_consume,
        'warehouse_id': _get_warehouse,
        'qty': 0.0
    }
    
    def onchange_scan(self, cr, uid, ids, scan, consume, transit, context=None):
        if scan:
            if not isinstance(scan, str):
                scan = str(scan)
            if context is None:
                context = {}
            context = dict(context,display_ean=True)
            procure_obj = self.pool.get('procurement.order')
            prod_id = self.pool.get('product.product').search(cr, uid, ['|',('ean13','=',scan),
                                                                         ('ean13','ilike',scan)], context=context)
            if prod_id and prod_id[0]:
                exist = []
                qty = 0.0
                if transit:
                    exist = procure_obj.search(cr, uid, [('product_id','=',prod_id[0]),
                                                         ('transit_order_id','=',transit)], context=context)
                if consume:
                    exist = procure_obj.search(cr, uid, [('product_id','=',prod_id[0]),
                                                         ('consume_order_id','=',consume)], context=context)
                if exist:
                    procure = procure_obj.read(cr, uid, exist[0], ['product_qty'], context=context)
                    qty = procure['product_qty']
                return { 'value':{'product_id': prod_id[0],
                                  'qty': qty,
                                  'scan_field': ''}}
            else:
                return {'warning': {
                    'title': _("Warning for %s") % scan,
                    'message': u'Бараа олдсонгүй'}}
        return {}
    
    def onchange_qty(self, cr, uid, ids, product_id, qty, warehouse_id, transit, consume, context=None):
        if context is None:
            context = {}
        procurement_obj = self.pool.get('procurement.order')
        context = dict(context,display_ean=True)
        if product_id and qty > 0 and warehouse_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if consume:
                consume = True
            values = procurement_obj.onchange_product_qty(cr, SUPERUSER_ID, [], product_id, qty, prod.uom_id.id, warehouse_id, consume, context=context)
            return values
        return {}
    
    def fill_procure(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        procure_obj = self.pool.get('procurement.order')
        
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        context.update({'display_ean':True})
        form = self.browse(cr, uid, ids[0], context=context)
        # Calculate theoretical quantity by searching the quants as in quants_get
        if form.product_id:
            exist = []
            if form.consume_id:
                exist = procure_obj.search(cr, uid, [('product_id','=',form.product_id.id),('consume_order_id','=',form.consume_id.id)], context=context)
            if form.transit_id:
                exist = procure_obj.search(cr, uid, [('product_id','=',form.product_id.id),('transit_order_id','=',form.transit_id.id)], context=context)
            if exist:
                procure_obj.write(cr, uid, exist,
                            {'product_qty': form.qty}, context=context)
            else:
                values = procure_obj.onchange_product_id(cr, SUPERUSER_ID, [], form.product_id.id, form.qty, form.product_id.uom_id.id, form.warehouse_id.id, form.consume_id, context=context)
                values_qty = procure_obj.onchange_product_qty(cr, SUPERUSER_ID, [], form.product_id.id, form.qty, form.product_id.uom_id.id, form.warehouse_id.id, form.consume_id, context=context)
                values['value'].update({'consume_order_id': form.consume_id and form.consume_id.id or False,
                                        'transit_order_id': form.transit_id and form.transit_id.id or False,
                                        'product_qty': form.qty,
                                        'product_id': form.product_id.id,
                                        'product_uos': form.product_id.uos_id and form.product_id.uos_id.id or form.product_id.uom_id.id,
                                        'date_planned': datetime.now(),
                                        'availability': values_qty['value']['availability']})
                procure_obj.create(cr, uid, values['value'])
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                'l10n_mn_stock', 'view_stock_fill_easy')[1]
        return {'name': _('Fill Procurement'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.fill.easy',
                'views': [(view, 'form')],
                'view_id': view,
                'target': 'new',
                'res_id': False,
                'context': context }
    