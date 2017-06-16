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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from lxml import etree
import time

class report_product_label(osv.osv_memory):
    _name = "report.product.label"
    _description = "Product Label"
    
    def report_action(self, cr, uid, ids, context=None):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        if context is None:
            context = {}
        form = self.read(cr, uid, ids[0], context=context)
        ids = 'active_ids' in context and context['active_ids'] or []
        if ids and 'active_model' in context and context['active_model'] == 'product.template':
            prod_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','=',ids)], context=context)
            if prod_ids:
                ids = prod_ids
        if not ids:
            if form['root_type'] == 'location':
                ids = form['location_ids']
            else:
                ids = form['product_ids']
        model = 'product.product'
        if form['root_type'] == 'location':
            model = 'stock.location'
        data = {
            'ids': ids,
            'model': model,
            'form': form
        }
        data['form']['active_ids'] = context.get('active_ids', False)
        action = self.pool.get("report").get_action(cr, uid, [], 'l10n_mn_stock.report_product_label', data=data, context=context)
        return action
        
    
    def _get_warehouse(self, cr, uid, context=None):
        '''
            Боломжит агуулахуудыг олж тодорхойлно.
        '''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wids = (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
        if wids:
            return wids[0]
        return False
    
    def _get_type(self, cr, uid, context=None):
        if 'active_model' in context and context['active_model'] == 'stock.location':
            return 'location'
        return 'product'
    
    _columns = {
        'root_type':    fields.selection([('location','Location'),('product','Product')], 'Root Type', required=True),
        'type':         fields.selection([('price','With price'),('label','Without price')], 'Type', required=True),
        'report_type':  fields.selection([('long','Long'),('short','Short')], 'Report Type', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'location_ids': fields.many2many('stock.location', 'report_product_label_location_rel',
                                         'report_id', 'location_id', 'Location'),
        'product_ids':  fields.many2many('product.product', 'report_product_label_product_rel',
                                         'report_id', 'product_id', 'Product'),
    }
    
    _defaults = {
        'root_type': _get_type,
        'type': 'price',
        'report_type': 'short',
        'warehouse_id': _get_warehouse,
    }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(report_product_label, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        user_obj = self.pool.get('res.users')
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            for node in doc.xpath("//field[@name='warehouse_id']"):
                node.set('domain', [('id','in',map(lambda x:x.id,user.allowed_warehouses) or [-1])].__repr__())
            whs = self._get_warehouse(cr, uid, context=context)
            if whs:
                wh = self.pool.get('stock.warehouse').browse(cr, uid, whs, context=context)
                location_ids = self.pool.get('stock.location').search(cr, uid, [('usage','=','internal'),('location_id','child_of',[wh.lot_stock_id.id])], context=context)
                if location_ids:
                    for node in doc.xpath("//field[@name='location_ids']"):
                        node.set('domain', [('id','in',location_ids)].__repr__())
            res['arch'] = etree.tostring(doc)
        return res
    
    def onchange_warehouse(self, cr, uid, ids, warehouse_id, context=None):
        context = context or {}
        if warehouse_id:
            wh = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            location_ids = self.pool.get('stock.location').search(cr, uid, [('usage','=','internal'),('location_id','child_of',[wh.lot_stock_id.id])], context=context)
            if location_ids:
                return {'domain':{'location_ids':[('id','in',location_ids)]},
                        'value':{'location_ids':location_ids}}
        return {}
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
