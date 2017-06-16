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

class stock_fill_inventory(osv.osv_memory):
    _name = 'stock.fill.inventory'
    _description = 'Stock Fill Inventory'
    
    _columns = {
        'remove_current_list': fields.boolean('Remove Current List'),
        'category_ids': fields.many2many('product.category','inventory_fill_category_rel','wiz_id','categ_id','Product Category'),
        'manufacture_ids': fields.many2many('res.partner','inventory_fill_manufacture_rel','wiz_id','part_id','Supplier & Manufacturer'),
        'product_ids': fields.many2many('product.product', 'inventory_fill_product_rel','wiz_id','prod_id','Products'),
        'unavailable': fields.boolean('Fill with unavailable products'),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'set_stock_zero': fields.boolean("Set to zero",help="If checked, all product quantities will be set to zero to help ensure a real physical inventory is done"),
        'scan_field':   fields.char('Scan Field', size=13),
        'type': fields.selection([('scan','Scanner'),('pick','Pick')], 'Type', required=True),
        'product_id': fields.many2one('product.product', 'Product'),
        'inventory_id': fields.many2one('stock.inventory', 'Inventory', required=True),
        'qty': fields.float('Quantity')
        #'lines': fields.one2many('stock.fill.inventory.line', 'fill_id', 'Lines')
    }
    
    def _get_inventory(self, cr, uid, context=None):
        res = False
        context = context or {}
        if 'active_id' in context and context['active_id']:
            return context['active_id']
        return res
    
    def _default_location(self, cr, uid, context=None):
        context = context or {}
        res = False
        if 'active_id' in context and context['active_id']:
            inv = self.pool.get('stock.inventory').browse(cr, uid, context['active_id'], context=context)
            if inv and inv.warehouse_id and inv.warehouse_id.lot_stock_id:
                return inv.warehouse_id.lot_stock_id.id
        return res
    
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
        res = super(stock_fill_inventory, self).view_init(cr, uid, fields_list, context=context)
        if len(context.get('active_ids',[])) > 1:
            raise osv.except_osv(_('Error!'), _('You cannot perform this operation on more than one Stock Inventories.'))

        if context['active_model'] == 'stock.inventory' and context.get('active_id', False):
            stock = self.pool.get('stock.inventory').browse(cr, uid, context.get('active_id', False))

            if stock.state == 'done':
                raise osv.except_osv(_('Warning!'), _('Stock Inventory is already Validated.'))
        return res
    
    _defaults = {
        'remove_current_list': False,
        'location_id': _default_location,
        'inventory_id': _get_inventory,
        'type': 'scan',
        'qty': 0.0
    }
    
    def onchange_scan(self, cr, uid, ids, scan, inventory_id, context=None):
        if scan:
            if not isinstance(scan, str):
                scan = str(scan)
            if context is None:
                context = {}
            inventory_obj = self.pool.get('stock.inventory.line')
            context = dict(context,display_ean=True)
            prod_ids = self.pool.get('product.product').search(cr, uid, ['|',('ean13','=',scan),
                                                                         ('ean13','ilike',scan)], context=context)
            if prod_ids and prod_ids[0]:
                qty = 0.0
                exist = inventory_obj.search(cr, uid, [('inventory_id','=',inventory_id),
                                                        ('product_id','=',prod_ids[0])], context=context)
                if exist and exist[0]:
                    inv = inventory_obj.browse(cr, uid, exist[0], context=context)
                    qty = inv.product_qty or 0.0
                return { 'value':{'product_id': prod_ids[0],
                                  'qty': qty,
                                  'scan_field': ''}}
            else:
                return {'warning': {
                    'title': _("Warning for %s") % scan,
                    'message': u'Бараа олдсонгүй'}}
        return {}
    
    def fill_inventory(self, cr, uid, ids, context=None):
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
        inventory_line_obj = self.pool.get('stock.inventory.line')
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        category_obj = self.pool.get('product.category')
        
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        context.update({'display_ean':True})
        form = self.browse(cr, uid, ids[0], context=context)
        inventory = self.pool.get('stock.inventory').browse(cr, uid, context['active_id'])
        if inventory.state not in ('draft','confirm') :
            raise osv.except_osv(_('Error !'), _('You can only renew inventory lines on draft document.'))
        
        existing_lines = {}
        if form.remove_current_list :
            inventory_line_obj.unlink(cr, uid, map(lambda x:x.id,inventory.line_ids), context=context)
        else:
            for line in inventory.line_ids:
                key = '%s,%s,%s' % (line.location_id.id, line.product_id.id, line.prod_lot_id.id)
                existing_lines[key] = line.id
        
        location_ids = location_obj.search(cr, uid, [('location_id','child_of', [form.location_id.id])], context=context)
        if form.type == 'pick':
            extra_where = ""
            join = ""
            if form.product_ids:
                extra_where += " and pp.id in ("+','.join(map(lambda x:str(x.id), form.product_ids))+") "
            if form.category_ids:
                category_ids = category_obj.search(cr, uid, [('parent_id','child_of',
                                map(lambda x:x.id, form.category_ids))], context=context)
                extra_where += " and pt.categ_id in ("+ ','.join(map(str,category_ids)) +") "
            if form.manufacture_ids:
                join += " left join product_supplierinfo psf on psf.product_tmpl_id = pt.id "
                partners = ','.join(map(lambda x:str(x.id), form.manufacture_ids))
                extra_where += " and (psf.name in (%s) or pt.manufacturer in (%s) ) " % (partners,partners)
            if not extra_where:
                raise osv.except_osv(_('Warning !'), _('You must be set any one filter!'))
            
            query_date = time.strftime('%Y-%m-%d %H:%M:%S')
            cr.execute("""select pp.id,lot_id,q.location_id,sum(q.qty) 
                            from stock_quant q 
                                join product_product pp on q.product_id = pp.id
                                join product_template pt on pp.product_tmpl_id = pt.id """+join+"""
                            where q.location_id in %s """+extra_where+"""
                            group by pp.id,lot_id,q.location_id""",(tuple(location_ids),))
            fetched = cr.fetchall()
            prods = map(lambda x:x[0], fetched)
            name_dict = dict(product_obj.name_get(cr, uid, prods, context=context))
            prod_datas = dict([(x['id'], x) for x in product_obj.read(cr, uid, prods, ['uom_id'])])
            for prod, lot, location, qty in fetched:
                key = '%s,%s,%s' % (location, prod, lot)
                if key in existing_lines:
                    inventory_line_obj.write(cr, uid, [existing_lines[key]],
                                {'product_qty': (form.set_stock_zero and 0) or qty,
                                 'theoretical_qty': qty}, context=context)
                else:
                    existing_lines[key] = inventory_line_obj.create(cr, uid, {
                                'inventory_id': inventory.id,
                                'location_id': location,
                                'product_id': prod,
                                'product_uom_id': prod_datas[prod]['uom_id'][0],
                                'product_qty': (not form.set_stock_zero and qty) or 0,
                                'theoretical_qty': qty,
                                'prod_lot_id': lot,
                                'name':name_dict[prod],
                    })
            
            if form.unavailable:
                cr.execute("select pp.id, pt.uom_id from product_product pp "
                           "join product_template pt on pt.id = pp.product_tmpl_id "
                           "join product_uom u on pt.uom_id = u.id "
                           + join +
                           "where pp.active and pp.id not in %s "
                           + extra_where,
                        tuple([tuple(prods or [-1])])
                )
                fetched = cr.fetchall()
                prods = map(lambda x:x[0], fetched)
                name_dict = dict(product_obj.name_get(cr, uid, prods, context=context))
                for prod, uom in fetched:
                    key = '%s,%s,%s' % (form.location_id.id,prod,False)
                    if key in existing_lines:
                        inventory_line_obj.write(cr, uid, [existing_lines[key]],
                                    {'product_qty': 0,
                                     'theoretical_qty': 0}, context=context)
                    else:
                        existing_lines[key] = inventory_line_obj.create(cr, uid, {
                                    'inventory_id': inventory.id,
                                    'location_id': form.location_id.id,
                                    'product_id': prod,
                                    'product_uom_id': uom,
                                    'product_qty': 0,
                                    'theoretical_qty': 0,
                                    'prod_lot_id': False,
                                    'name':name_dict[prod],
                        })
            
            return {'type': 'ir.actions.act_window_close'}
        else:
            quant_obj = self.pool["stock.quant"]
            # Calculate theoretical quantity by searching the quants as in quants_get
            if form.product_id and form.location_id:
                
                dom = [('company_id', '=', user.company_id.id), ('location_id', '=', form.location_id.id), 
                            ('product_id','=', form.product_id.id)]
                quants = quant_obj.search(cr, uid, dom, context=context)
                th_qty = sum([x.qty for x in quant_obj.browse(cr, uid, quants, context=context)])
                key = '%s,%s,%s' % (form.location_id.id,form.product_id.id,False)
                if key in existing_lines:
                    inventory_line_obj.write(cr, uid, [existing_lines[key]],
                                {'product_qty': form.qty,
                                 'theoretical_qty': th_qty or 0.0}, context=context)
                else:
                    existing_lines[key] = inventory_line_obj.create(cr, uid, {
                                'inventory_id': inventory.id,
                                'location_id': form.location_id.id,
                                'product_id': form.product_id.id,
                                'product_uom_id': form.product_id.uom_id.id,
                                'product_qty': form.qty,
                                'theoretical_qty': th_qty or 0.0,
                                'prod_lot_id': False,
                                'name':form.product_id.name_get(context=context)[0][1],
                    })
            view = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                    'l10n_mn_stock', 'view_stock_fill_inventory')[1]
            return {'name': _('Change Sales Price'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.fill.inventory',
                    'views': [(view, 'form')],
                    'view_id': view,
                    'target': 'new',
                    'res_id': False,
                    'context': context }

class stock_fill_inventory_line(osv.osv_memory):
    _name = 'stock.fill.inventory.line'
    _description = 'Stock Fill Inventory Line'
    
    _columns = {
        'fill_id':  fields.many2one('stock.fill.inventory', 'Fill', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'qty': fields.float('Product Qty', required=True)
    }
    