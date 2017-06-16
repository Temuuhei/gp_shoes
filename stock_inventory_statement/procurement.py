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
import threading
import time
import logging
from datetime import datetime

from openerp.api import Environment
from openerp.osv import osv, fields
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp import _, api, SUPERUSER_ID, tools
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import netsvc
from openerp import pooler

_logger = logging.getLogger('STOCK')

class stock_warehouse_orderpoint(osv.osv):
    _inherit = 'stock.warehouse.orderpoint'
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM for changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            v = {'product_uom': prod.uom_id.id}
            return {'value': v, 'domain':{'product_uom':[('category_id','=',prod.uom_id.category_id.id)]}}
        return {}
    
    def onchange_product_uom(self, cr, uid, ids, product_id, product_uom, context=None):
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if product_uom:
                uom = self.pool.get('product.uom').browse(cr, uid, product_uom, context=context)
                if uom.category_id.id <> prod.uom_id.category_id.id:
                    raise osv.except_osv(_('Wrong UoM !'), _('You have to select UoM for same category with default UoM of %s product.')
                                    % (prod.name,))
        return {}
    
    _columns = {
        'procure_method': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True, select=True),
        'supplier_id': fields.many2one('res.partner', 'Supplier'),
        'transit_warehouse': fields.many2one('stock.warehouse', 'Supplier Warehouse'),
        'day': fields.integer('Day', required=True)
    }
    
    _sql_constraint = [
        ('product_warehouse_unique', 'UNIQUE(warehouse_id,product_id,procure_method)', 'The product must be unique on each warehouse!'),
    ]
    
    def _check_warehouse(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.procure_method == 'make_to_stock' and obj.transit_warehouse.id == obj.warehouse_id.id :
            _logger.warn('The Supplier Warehouse must be different for own warehouse: (stock.warehouse.orderpoint,%s)' % obj.id)
            return False
        return True
    
    _constraints = [
        (_check_warehouse, 'The Supplier Warehouse must be different for own warehouse.', ['transit_warehouse','warehouse_id']),
    ]
    
    def _default_warehouse(self, cr, uid, context=None):
        res = self.pool.get('res.users').read(cr, uid, uid, ['allowed_warehouses'])['allowed_warehouses']
        return (len(res) == 1 and res[0]) or False
    
    _defaults = {
        'warehouse_id': _default_warehouse,
        'day': lambda *a: 30,
    }
    
    def user_see_all_warehouse(self, cr, uid, context=None):
        group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
                'stock', 'group_locations')[1]
        cr.execute("select count(*) from res_groups_users_rel where uid = %s and gid = %s",(uid, group_id))
        if cr.fetchone()[0] > 0:
            return True
        return False
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(stock_warehouse_orderpoint, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, 
                    context=context, toolbar=toolbar, submenu=False)
        user_obj = self.pool.get('res.users')
        if view_type == 'form' and not self.user_see_all_warehouse(cr, uid):
            user = user_obj.browse(cr, uid, uid, context=context)
            if 'warehouse_id' in res['fields']:
                res['fields']['warehouse_id']['selection'] = \
                    map(lambda x:(x.id,x.name), user.allowed_warehouses) or [('',False)]
        return res
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(osv.osv, self).default_get(cr, uid, fields, context)
        return res
    
stock_warehouse_orderpoint()

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    
    def _procure_orderpoint_confirm_inherit(self, cr, uid, warehouse_ids, automatic=False,\
        use_new_cursor=False, procure_method='all', cron_day=False, user_id=False, context=None):
        
        t1 = datetime.now()
        if context is None:
            context = self.pool.get('res.users').context_get(cr, uid)
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        purchase_obj = self.pool.get('purchase.order')
        pricelist_obj = self.pool.get('product.pricelist')
        purchase_line_obj = self.pool.get('purchase.order.line')
        sale_line_obj = self.pool.get('sale.order.line')
        sale_obj = self.pool.get('sale.order')
        uom_obj = self.pool.get('product.uom')
        stock_transit_obj = self.pool.get('stock.transit.order')
        
        res = {}
        if cron_day: # Сар бүрийн тогтсон өдөрт ажиллуулахаар тохируулсан байвал бусад өдөрт нь алгасна.
            today = datetime.today()
            if today.day <> cron_day:
                message = "Procurement._procure_orderpoint_confirm() skipped until %s day of month" % cron_day
                _logger.info(message)
                cr.close()
                return res
        for wh in warehouse_obj.browse(cr, SUPERUSER_ID, warehouse_ids, context=context):
            company = wh.company_id
            if wh.property_replenishment_user:
                purchase_uid = wh.property_replenishment_user.id
            else:
                purchase_uid = uid
            taxes = self.pool.get('account.tax').search(cr, uid, 
                    [('type_tax_use','=','purchase'),('price_include','=',True),
                     ('company_id','=',company.id)])
            _logger.info(wh.name+ ' ' +str(wh.view_location_id.id))
            location_ids_tuple = tuple(location_obj.search(cr, purchase_uid, 
                [('location_id','child_of', [wh.view_location_id.id]),
                 ('usage','=','internal')], context=context))
            # Тухайн агуулахын зохистой нөөцийн дүрэм
            if procure_method == 'all':
                method_search = ['make_to_stock','make_to_order']
            else:
                method_search = [procure_method]
            orderpoint_ids = orderpoint_obj.search(cr, SUPERUSER_ID, [('warehouse_id','=',wh.id),
                                                     ('location_id','child_of',[wh.view_location_id.id]),
                                                     ('procure_method','in',method_search)], context=context)
            if not orderpoint_ids:
                continue
            orderpoints = orderpoint_obj.browse(cr, SUPERUSER_ID, orderpoint_ids, context=context)
            
            _logger.info("%s warehouse calculating procurement with %s number of orderpoint..." % (wh.name, len(orderpoint_ids)))
            
            todo_stock_dict = {}
            todo_order_dict = {}
            
            prods = map(lambda x:x.product_id.id, orderpoints)
            prod_name = dict(product_obj.name_get(cr, purchase_uid, prods, context=context))
            uom_dict = dict(map(lambda x:(x.product_id.id, x.product_uom.id), orderpoints))
            uom_obj_dict = dict(map(lambda x:(x.product_id.id, x.product_uom), orderpoints))
            # Тухайн барааны ирээдүйн үлдэгдлийг тооцоолох
            cr.execute("select r.product_id, coalesce(sum(r.product_qty),0) "
                       "from report_stock_inventory r "
                       "where r.product_id in %s "
                       # "and r.state in ('done','confirmed','waiting','assigned') "
                       "and r.location_type = 'internal' "
                       "and r.date <= %s "
                       "and r.location_id in %s "
                       "group by r.product_id",
                    (tuple(prods), time.strftime('%Y-%m-%d %H:%M:%S'), location_ids_tuple))
            _logger.debug("select r.product_id, coalesce(sum(r.product_qty),0) from report_stock_inventory r where r.product_id in %s and r.location_type = 'internal' and r.date <= %s and r.location_id in %s group by r.product_id" % (tuple(prods), time.strftime('%Y-%m-%d %H:%M:%S'), location_ids_tuple))
            stock_dict = dict(cr.fetchall() or [])
            _logger.info(stock_dict)
            count_of_total = 0 # Нийт нөөц шаардлагатай нэр төрөл
            count_of_procurement = 0 # Нөхөн дүүргэлтээр авах нэр төрөл
            count_of_inter_purchase = 0 # Ком-хооронд худалдан авах нэр төрөл
            count_of_external_purchase = 0 # Гадны харилцагчаас худалдан авах нэр төрөл
            for orderpoint in orderpoints:
                stock_qty = stock_dict.get(orderpoint.product_id.id, 0)
                if stock_qty < (orderpoint.product_min_qty or 0):
                    needed_qty = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - stock_qty
                    reste = needed_qty % orderpoint.qty_multiple
                    if reste > 0:
                        needed_qty += orderpoint.qty_multiple - reste
                    
                    if needed_qty <= 0:
                        continue
                    
                    count_of_total += 1
                    if orderpoint.procure_method == 'make_to_stock' :
                        if orderpoint.transit_warehouse.id not in todo_stock_dict:
                            todo_stock_dict[orderpoint.transit_warehouse.id] = {}
                        if orderpoint.product_id.id not in todo_stock_dict[orderpoint.transit_warehouse.id]:
                            todo_stock_dict[orderpoint.transit_warehouse.id][orderpoint.product_id.id] = 0
                        todo_stock_dict[orderpoint.transit_warehouse.id][orderpoint.product_id.id] += needed_qty
                        count_of_procurement += 1

                    elif orderpoint.procure_method == 'make_to_order':
                        supplier = orderpoint.supplier_id or orderpoint.product_id.seller_id
                        if not supplier :
                            _logger.warning('Make to order %s product cannot find supplier. skipped for %s warehouse.' %\
                                           (orderpoint.product_id.name,wh.name))
                            continue
                        if not todo_order_dict.get(supplier.id, False):
                            existings = purchase_obj.search(cr, purchase_uid, [
                                ('partner_id', '=', supplier.id),
                                ('company_id','=',company.id),
                                ('warehouse_id', '=', wh.id),
                                ('state','=','draft'),
                                ('supplier_warehouse_id','=',0)
                            ], context=context)
                            if existings :
                                purchase_obj.write(cr, purchase_uid, [existings][0], {'date_order':time.strftime('%Y-%m-%d')}, context=context)
                                purchase_id = existings[0]
                                pricelist_id = purchase_obj.read(cr, uid, purchase_id, ['pricelist_id'])['pricelist_id'][0]
                            else :
                                vals = {
                                    'company_id': company.id,
                                    'partner_id': supplier.id,
                                    'order_line': [(6,0,[])],
                                    'warehouse_id': wh.id,
                                }
                                vals.update(purchase_obj.onchange_warehouse_id(cr, purchase_uid, [], wh.id)['value'])
                                vals.update(purchase_obj.onchange_partner_id(cr, purchase_uid, [], supplier.id)['value'])
                                if not vals['pricelist_id']:
                                    ff = partner_obj.read(cr, uid, company.partner_id.id, 
                                            ['property_product_pricelist_purchase'])['property_product_pricelist_purchase']
                                    if not ff:
                                        _logger.warning('Make to order %s supplier cannot find pricelist. skipped for %s warehouse.' %\
                                                        (supplier.name,wh.name))
                                        continue
                                    vals['pricelist_id'] = ff[0]
                                pricelist_id = vals['pricelist_id']
                                purchase_id = purchase_obj.create(cr, purchase_uid, vals, context=context)
                            todo_order_dict[supplier.id] = {
                                       'purchase_id':purchase_id,
                                       'supplier_partner_obj':supplier,
                                       'lines_data': {},
                                       'pricelist_id': pricelist_id
                            }
                        key = (orderpoint.product_id.id, False)
                        if key not in todo_order_dict[supplier.id]['lines_data']:
                            todo_order_dict[supplier.id]['lines_data'][key] = {
                                    'ordering_qty': 0,
                                    'name': prod_name[orderpoint.product_id.id],
                                    'uom_id': orderpoint.product_uom,
                            }
                        todo_order_dict[supplier.id]['lines_data'][key]['ordering_qty'] += needed_qty
                        count_of_external_purchase += 1

            _logger.info("%s warehouse calculating %s number of needed products.\n Procurement: %s, External Purchase: %s, Inter-company purchase: %s." % \
                             (wh.name, count_of_total, count_of_procurement, count_of_external_purchase, count_of_inter_purchase))
            
            # Нөхөн дүүргэлтийн санал үүсгэх шаардлагатай бараануудын хувьд
            # өмнө нь үүссэн ноорог саналууд байгаа эсэхийг шалгана.
            if todo_stock_dict :
                proc_pack_names = []
                check_prod_ids = []
                for x, v in todo_stock_dict.iteritems():
                    check_prod_ids += v.keys()
                cr.execute("select proc.product_id, proc.id, proc.move_dest_id, "
                           "proc.product_qty from procurement_order proc "
                           "where proc.product_id in %s and proc.location_id in %s "
                           "and proc.company_id = %s and proc.state = 'draft'",
                           (tuple(check_prod_ids), location_ids_tuple, company.id))
                _logger.info("select proc.product_id, proc.id, proc.move_dest_id, proc.product_qty from procurement_order proc where proc.product_id in %s and proc.location_id in %s and proc.company_id = %s and proc.state = 'draft'" % (tuple(check_prod_ids), location_ids_tuple, company.id))
                procure_exists = {}
                for prod, proc, proc_move, qty in cr.fetchall():
                    if prod not in procure_exists : 
                        procure_exists[prod] = (proc, proc_move, qty)
                # Нөхөн дүүргэлтийн захиалга үүсгэнэ.
                for supp_warehouse, procure_data in todo_stock_dict.iteritems():
                    supp_warehouse_obj = self.pool.get('stock.warehouse').browse(cr, SUPERUSER_ID, supp_warehouse)
                    if not supp_warehouse_obj.property_replenishment_user:
                        _logger.warning(_('There is no procurement user defined on this warehouse: %s') % supp_warehouse_obj.name)
                        continue
                    todo_check_available = {}
                    for prod, needed_qty in procure_data.iteritems():
                        todo_check_available[prod] = {
                            'ordering_qty': needed_qty,
                            'name': '/',
                            'uom_id': uom_obj_dict[prod],
                            'expire_range': False,
                            'line_ids': [prod]
                        }
                    if todo_check_available:
                        _logger.info("There is %s number of products stock available on %s warehouse" % (len(todo_check_available.keys()), supp_warehouse_obj.name))
                        stock_transit_id = False
                        cr.execute("select id from stock_transit_order "
                                   "where state = 'draft' and warehouse_id = %s "
                                   "and supply_warehouse_id = %s and company_id = %s",
                            (supp_warehouse, wh.id, wh.company_id.id))
                        ff = cr.fetchone()
                        if ff and ff[0]:
                            stock_transit_id = ff[0]
                            stock_transit_obj.write(cr, uid, [stock_transit_id], {'date_order':time.strftime('%Y-%m-%d')}, context=context)
                        else :
                            stock_transit_id = stock_transit_obj.create(cr, uid, {
                                    'date_order': time.strftime('%Y-%m-%d'),
                                    'warehouse_id': wh.id,
                                    'supply_warehouse_id': supp_warehouse,
                                    'user_id': supp_warehouse_obj.property_replenishment_user.id,
                            }, context=context)
                        
                        proc_pack_names.append(stock_transit_obj.read(cr, uid, stock_transit_id, ['name'])['name'])
                        if 'make_to_stock' not in res:
                            res['make_to_stock'] = []
                        res['make_to_stock'].append(stock_transit_id)
                        for prod, proddata in todo_check_available.iteritems():
                            needed_qty = proddata['ordering_qty']
                            if prod in procure_exists:
                                self.write(cr, purchase_uid, [procure_exists[prod][0]],{
                                        'date_planned': time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'product_qty': max(needed_qty, procure_exists[prod][2]),
                                        'product_uos_qty': max(needed_qty, procure_exists[prod][2]),
                                        'origin': 'auto',
                                        'transit_order_id': stock_transit_id
                                }, context=context)
                                if procure_exists[prod][1]:
                                    cr.execute("update stock_move set product_qty = %s, "
                                               "product_uos_qty = %s, "
                                               "date_expected = %s where id = %s",
                                        (max(needed_qty, procure_exists[prod][2]),
                                         max(needed_qty, procure_exists[prod][2]), 
                                         time.strftime('%Y-%m-%d %H:%M:%S'), procure_exists[prod][1]))
                            else:
                                proc_id = self.create(cr, purchase_uid, {
                                    'origin': 'auto',
                                    'product_uos_qty': needed_qty,
                                    'product_uom': uom_dict[prod],
                                    'product_uos': uom_dict[prod],
                                    'product_qty': needed_qty,
                                    # 'procure_method': 'make_to_stock',
                                    # 'location_id': wh.wh_input_stock_loc_id.id,
                                    'product_id': prod,
                                    'date_planned': time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'company_id': company.id,
                                    # 'warehouse_id': wh.id,
                                    'name': prod_name[prod],
                                    'transit_order_id': stock_transit_id
                                }, context=context)
                if proc_pack_names:
                    _logger.info("%s warehouse computing %s number of procurement and created %s procurement orders..." % \
                             (wh.name, len(todo_stock_dict.keys() + todo_order_dict.keys()), ','.join(proc_pack_names)))

            purchase_names = []
            if todo_order_dict:
                # Гадны харилцагчаас худалдан авалтын ноорог захиалга үүсгэнэ.
                for supplier_id, datas in todo_order_dict.iteritems():
                    product_ids = tuple(map(lambda x:x[0], datas['lines_data'].keys()))
                    cr.execute("select l.product_id, l.id, l.product_qty "
                               "from purchase_order_line l "
                               "where l.order_id = %s and l.product_id in %s ",
                            (datas['purchase_id'], product_ids))
                    exist_lines = dict([(x['product_id'], x) for x in cr.dictfetchall() or []])
                    create_lines = []
                    for prod, prodd in datas['lines_data'].iteritems():
                        prod = prod[0]
                        needed_qty = prodd['ordering_qty']
                        if prod in exist_lines:
                            return_line_id = exist_lines[prod]['id']
                            purchase_qty = exist_lines[prod]['product_qty']
                            cr.execute("update purchase_order_line set product_qty = %s where id = %s",
                                    (needed_qty, return_line_id))
                        else :
                            create_lines.append( (prod, needed_qty, datas['supplier_partner_obj'].id) )
                    
                    if create_lines:
                        try:
                            price_dict = pricelist_obj.price_get_multi(cr, 
                                purchase_uid, pricelist_ids=[datas['pricelist_id']], 
                                products_by_qty_by_partner=create_lines, 
                                context=dict(context.items(),warehouse=wh.id,company_id=company.id))
                        except:
                            _logger.warning('%s supplier price getting problem:%s' % (datas['supplier_partner_obj'].name, sys.exc_info()) )
                            continue
                        
                        for prod, qty, part in create_lines:
                            price = price_dict[prod]
                            # хурдан ажиллуулах.
                            return_line_id = purchase_line_obj.create(cr, purchase_uid, {
                                'product_id': prod,
                                'price_unit': price[datas['pricelist_id']],
                                'base_price': price['base'],
                                'product_uom': uom_dict[prod],
                                'product_qty': qty,
                                'name': prod_name[prod],
                                'date_planned': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'taxes_id': [(6,0,taxes)],
                                'order_id': datas['purchase_id'],
                                'state': 'draft'
                            }, context=dict(context.items(), no_store_function=True))
                    # Захиалгын нийлбэр үнийг тооцоолох
                    purchase_names.append(purchase_obj.read(cr, purchase_uid, datas['purchase_id'], ['name'], context=context)['name'])
                    _line_ids = purchase_line_obj.search(cr, purchase_uid, [('order_id','=',datas['purchase_id'])])
                    if _line_ids:
                        _line_data = purchase_line_obj.read(cr, purchase_uid, _line_ids[0],['product_qty'])
                        purchase_line_obj.write(cr, purchase_uid, [_line_ids[0]], {
                            'product_qty': _line_data['product_qty'],
                        }, context=context)
                        
                    if 'make_to_order' not in res:
                        res['make_to_order'] = []
                    res['make_to_order'].append(datas['purchase_id'])
            if purchase_names:
                _logger.info("%s warehouse computing %s number of supplier purchase order processed..." % \
                                   (wh.name, purchase_names))
                                
            if use_new_cursor:
                cr.commit()
        message = "Procurement._procure_orderpoint_confirm() runned in :%s seconds" % (((datetime.now() - t1).seconds),)
        _logger.info(message)
        #self.log(cr, uid, False, message)
        if use_new_cursor:
            cr.commit()
            cr.close()
        return True
    
procurement_order()

class procurement_compute(osv.osv_memory):
    _inherit = 'procurement.orderpoint.compute'
    _description = 'Compute Minimum Stock Rules'

    def _procure_calculation_orderpoint_inherit(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        with Environment.manage():
            proc_obj = self.pool.get('procurement.order')
            warehouse_obj = self.pool.get('stock.warehouse')
            #As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            warehouse_ids = []
            new_cr = self.pool.cursor()
            user_obj = self.pool.get('res.users')
            company_id = user_obj.browse(new_cr, uid, uid, context=context).company_id.id
            user = user_obj.browse(new_cr, uid, uid, context=context)
            for warehouse in user.allowed_warehouses:
                _logger.info("Warehouse: %s",warehouse.name)
                warehouse_ids.append(warehouse.id)
            automatic = False
            use_new_cursor=False
            procure_method='all'
            cron_day=False
            user_id=user_obj.browse(new_cr, uid, uid, context=context).id
            proc_obj._procure_orderpoint_confirm_inherit(new_cr, uid, warehouse_ids, automatic, new_cr.dbname, procure_method,  cron_day, user_id, context=context)
            #close the new cursor
            new_cr.close()
            return {}

    def procure_calculation_inherit(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint_inherit, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}