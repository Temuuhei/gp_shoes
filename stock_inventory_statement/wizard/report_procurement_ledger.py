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

from openerp.osv import osv,fields
from openerp.tools.translate import _
from datetime import datetime
from operator import itemgetter
import time

class report_procurement_ledger(osv.osv_memory):
    _name = 'report.procurement.ledger'
    _inherit = 'abstract.report.model'
    _description = 'Report Procurement Ledger'
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_procure_ledger_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'product_ids':  fields.many2many('product.product', 'report_procure_ledger_product_rel',
                            'wizard_id', 'product_id', 'Product'),
        'procure_ids':  fields.many2many('stock.transit.order', 'report_procure_ledger_procure_rel',
                            'wizard_id', 'procure_id', 'Procurement'),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
        'report_type':  fields.selection([('order','Orders'),('product','Products')], 'Report Type', required=True),
        'type':         fields.selection([('detail','Detail'),('summary','Summary')], 'Type', required=True),
        'cost':         fields.boolean('Show Cost Amount?'),
        'lot':          fields.boolean('Show Serial')
        
    }
    
    def _get_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wids = (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
        return wids[0]
    
    _defaults = {
        'company_id': lambda obj,cr,uid,c:obj.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory.report'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'report_type': 'product',
        'type': 'detail',
        'cost': False,
        'warehouse_id': _get_warehouse
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        body = (u"Нөхөн дүүргэлтийн тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
          (form.date_from, form.date_to, form.warehouse_id.name)
        return body
    
    def get_print_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        data = {
            'ids': ids,
            'model': self._name,
            'form': {}
        }
        
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'abstract.report.builder',
            'datas': data,
            'nodestroy': True
        }
    
    def get_export_data(self, cr, uid, ids, report_code, context=None):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        wiz = self.read(cr, uid, ids[0], context=context)
        
        data, titles, head_col, row_span = self.mirror_prepare_report_data(cr, uid, wiz, self._name, context=context)
        if wiz['report_type'] == 'product':
            widths = [2,10,4]
            headers = [
                [u'Д/д',u'Бараа материалын нэрс',u'Бар код',u'Тоо хэмжээ'],
                [None,None,None,None],
                [None,None,None,None]
            ]
            header_span = [((0,0),(0,2)), ((1,0),(1,2)), 
                           ((2,0),(2,2)), ((3,0),(3,2))]
            colx = 4
            for h in head_col:
                if wiz['lot']:
                    headers[0] += [h,None,None]
                    headers[1] += [u'Сери дугаар',u'Орлого',None]
                    headers[2] += [None,u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                    headers[0] += [None,None]
                    headers[1] += [u'Зарлага',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                        header_span += [((colx,0),(colx+6,0))]
                        header_span += [((colx,1),(colx,2))]
                        header_span += [((colx+1,1),(colx+3,1))]
                        header_span += [((colx+4,1),(colx+6,1))]
                        colx += 7
                    else:
                        header_span += [((colx,0),(colx+4,0))]
                        header_span += [((colx,1),(colx,2))]
                        header_span += [((colx+1,1),(colx+2,1))]
                        header_span += [((colx+3,1),(colx+4,1))]
                        colx += 5
                else:
                    headers[0] += [h,None]
                    headers[1] += [u'Орлого',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                    headers[0] += [None,None]
                    headers[1] += [u'Зарлага',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                        header_span += [((colx,0),(colx+5,0))]
                        header_span += [((colx,1),(colx+2,1))]
                        header_span += [((colx+3,1),(colx+5,1))]
                        colx += 6
                    else:
                        header_span += [((colx,0),(colx+3,0))]
                        header_span += [((colx,1),(colx+1,1))]
                        header_span += [((colx+2,1),(colx+3,1))]
                        colx += 4
        else:
            widths = [2,10,4]
            headers = [
                [u'Д/д',u'Бараа материалын нэрс'],
                [None,None],
                [None,None]
            ]
            header_span = [((0,0),(0,2)), ((1,0),(1,2))]
            colx = 2
            if wiz['type'] == 'detail':
                headers[0] += [u'Бар код']
                headers[1] += [None]
                headers[2] += [None]
                header_span += [((colx,0), (colx,2))]
                colx += 1
            headers[0] += [u'Тоо хэмжээ']
            headers[1] += [None]
            headers[2] += [None]
            header_span += [((colx,0), (colx,2))]
            colx += 1
            for h in head_col:
                if wiz['lot'] and wiz['type'] == 'detail':
                    headers[0] += [h,None,None]
                    headers[1] += [u'Сери дугаар',u'Орлого',None]
                    headers[2] += [None,u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                    headers[0] += [None,None]
                    headers[1] += [u'Зарлага',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                        header_span += [((colx,0),(colx+6,0))]
                        header_span += [((colx,1),(colx,2))]
                        header_span += [((colx+1,1),(colx+3,1))]
                        header_span += [((colx+4,1),(colx+6,1))]
                        colx += 7
                    else:
                        header_span += [((colx,0),(colx+4,0))]
                        header_span += [((colx,1),(colx,2))]
                        header_span += [((colx+1,1),(colx+2,1))]
                        header_span += [((colx+3,1),(colx+4,1))]
                        colx += 5
                else:
                    headers[0] += [h,None]
                    headers[1] += [u'Орлого',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                    headers[0] += [None,None]
                    headers[1] += [u'Зарлага',None]
                    headers[2] += [u'Тоо',u'Үнийн дүн']
                    if wiz['cost']:
                        headers[0] += [None]
                        headers[1] += [None]
                        headers[2] += [u'Өртөг дүн']
                        header_span += [((colx,0),(colx+5,0))]
                        header_span += [((colx,1),(colx+2,1))]
                        header_span += [((colx+3,1),(colx+5,1))]
                        colx += 6
                    else:
                        header_span += [((colx,0),(colx+3,0))]
                        header_span += [((colx,1),(colx+1,1))]
                        header_span += [((colx+2,1),(colx+3,1))]
                        colx += 4
        datas = {
            'title': u'Нөхөн дүүргэлтийн тайлан',
            'headers': headers,
            'header_span': header_span,
            'row_span': row_span,
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas':datas}
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        ware_names = []
        wids = []
        if wiz['warehouse_ids']:
            wids = wiz['warehouse_ids']
        else:
            wids = self.pool.get('stock.warehouse').search(cr, uid, [('id','!=',wiz['warehouse_id'][0])], context=context)
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wids, context=context)
        
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'],wiz['date_to']),
                  u'Салбар: %s'%(wiz['warehouse_id'][1])]
        data = []
        res = {}
        where = ''
        total_dict = {}
        if wiz['report_type'] == 'product':
            total_dict = {'qty': 0, 
                          'whs': {}}
        else:
            total_dict = {'qty': 0, 
                          'whs': {}}
        if wiz['product_ids']:
            where = " AND o.product_id in ("+",".join(map(str,wiz['product_ids']))+") "
        if wiz['procure_ids']:
            where = " AND t.id in ("+",".join(map(str,wiz['procure_ids']))+") "
        if wiz['report_type'] == 'product':
            name_dict = {}
            prod_ids = []
            tids = []
            cr.execute("""SELECT t.id, o.product_id AS prod_id, p.ean13 AS ean,
                                SUM(coalesce((o.product_qty / u.factor * u2.factor), 0)) AS qty
                            FROM stock_transit_order t
                                JOIN procurement_order o ON t.id = o.transit_order_id
                                JOIN product_product p ON o.product_id = p.id
                                JOIN product_uom u ON o.product_uom = u.id
                                JOIN product_template pt ON p.product_tmpl_id = pt.id
                                JOIN product_uom u2 ON pt.uom_id = u2.id
                            WHERE o.state in ('confirm','done','running') 
                                AND t.date_order >= %s AND t.date_order <= %s
                                AND t.supply_warehouse_id = %s """+where+"""
                                AND t.warehouse_id in %s
                            GROUP BY t.id,o.product_id,p.ean13
                        """,(wiz['date_from'],wiz['date_to'],wiz['warehouse_id'][0],tuple(wids)))
            result = cr.dictfetchall()
            for r in result:
                if r['prod_id'] not in prod_ids:
                    prod_ids.append(r['prod_id'])
                if r['id'] not in tids:
                    tids.append(r['id'])
            if prod_ids:
                name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
            for r in result:
                if r['prod_id'] not in res:
                    res[r['prod_id']] = {'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                         'ean': r['ean'] or '',
                                         'qty': 0.0,
                                         'lots':[],
                                         'whs': {}}
                res[r['prod_id']]['qty'] += r['qty']
                total_dict['qty'] += r['qty']
            if tids:
                for wh in warehouses:
                    ware_names.append(wh.name)
                    if wh.id not in wids:
                        wids.append(wh.id)
                    name_dict = {}
                    prod_ids = []
                    if wh.id not in total_dict['whs']:
                        total_dict['whs'][wh.id] = {'in_qty': 0.0,
                                                    'in_cost': 0.0,
                                                    'in_amount': 0.0,
                                                    'out_qty': 0.0,
                                                    'out_cost': 0.0,
                                                    'out_amount': 0.0}
                    location_ids = self.pool.get('stock.location').search(cr, uid, 
                                                [('location_id','child_of',[wh.view_location_id.id]),
                                                 ('usage','=','internal')], context=context)
                    tuple_location = tuple(location_ids)
                    cr.execute("""SELECT o.product_id AS prod_id, p.ean13 AS ean, lot.name AS lot, 'out' AS type,
                                        SUM(link.qty * u.factor / u2.factor) AS qty,
                                        SUM(link.qty * u.factor / u2.factor * pack.cost) AS cost,
                                        SUM(link.qty * u.factor / u2.factor * pack.list_price) AS amount
                                    FROM stock_transit_order t 
                                        JOIN procurement_order o ON t.id = o.transit_order_id
                                        JOIN stock_move m ON o.id = m.procurement_id
                                        LEFT JOIN stock_move_operation_link link ON m.id = link.move_id
                                        LEFT JOIN stock_pack_operation pack ON link.operation_id = pack.id
                                        LEFT JOIN stock_production_lot lot ON pack.lot_id = lot.id
                                        JOIN product_product p ON m.product_id = p.id
                                        JOIN product_uom u ON pack.product_uom_id = u.id
                                        JOIN product_template pt ON p.product_tmpl_id = pt.id
                                        JOIN product_uom u2 ON pt.uom_id = u2.id
                                    WHERE m.state = 'done'
                                        AND m.date >= %s AND m.date <= %s
                                        AND t.supply_warehouse_id = %s AND t.id IN %s """+where+"""
                                        AND m.location_id IN %s AND m.location_dest_id NOT IN %s
                                    GROUP BY o.product_id,p.ean13,lot.name
                                UNION ALL 
                                    SELECT o.product_id AS prod_id, pp.ean13 AS ean, lot.name AS lot, 'in' AS type,
                                        SUM(link.qty * u.factor / u2.factor) AS qty,
                                        SUM(link.qty * u.factor / u2.factor * pack.cost) AS cost,
                                        SUM(link.qty * u.factor / u2.factor * pack.list_price) AS amount
                                    FROM stock_transit_order t 
                                        JOIN procurement_order o ON t.id = o.transit_order_id 
                                        JOIN stock_picking p ON t.id = p.transit_order_id
                                        JOIN stock_move m ON p.id = m.picking_id
                                        LEFT JOIN stock_move_operation_link link ON m.id = link.move_id
                                        LEFT JOIN stock_pack_operation pack ON link.operation_id = pack.id
                                        LEFT JOIN stock_production_lot lot ON pack.lot_id = lot.id
                                        JOIN product_product pp ON m.product_id = pp.id
                                        JOIN product_uom u ON pack.product_uom_id = u.id
                                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                                        JOIN product_uom u2 ON pt.uom_id = u2.id
                                    WHERE m.state = 'done'
                                        AND m.date >= %s AND m.date <= %s
                                        AND t.supply_warehouse_id = %s AND t.id IN %s """+where+"""
                                        AND m.location_id NOT IN %s AND m.location_dest_id IN %s
                                    GROUP BY o.product_id,pp.ean13,lot.name
                                        """,(wiz['date_from'],wiz['date_to']+' 23:59:59',wiz['warehouse_id'][0],tuple(tids),tuple_location,tuple_location,
                                             wiz['date_from'],wiz['date_to']+' 23:59:59',wiz['warehouse_id'][0],tuple(tids),tuple_location,tuple_location))
                    result = cr.dictfetchall()
                    for r in result:
                        if r['prod_id'] not in prod_ids:
                            prod_ids.append(r['prod_id'])
                    if prod_ids:
                        name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
                    for r in result:
                        if r['prod_id'] not in res:
                            res[r['prod_id']] = {'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                                 'ean': r['ean'] or '',
                                                 'qty': 0.0,
                                                 'lots':[],
                                                 'whs': {}}
                        if r['lot'] not in res[r['prod_id']]['lots']:
                            res[r['prod_id']]['lots'].append(r['lot'])
                        if wh.id not in res[r['prod_id']]['whs']:
                            res[r['prod_id']]['whs'][wh.id] = {'in_qty': 0.0,
                                                               'in_cost': 0.0,
                                                               'in_amount': 0.0,
                                                               'out_qty': 0.0,
                                                               'out_cost': 0.0,
                                                               'out_amount': 0.0,
                                                               'lots': {}}
                        if r['lot'] not in res[r['prod_id']]['whs'][wh.id]['lots']:
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']] = {'name': r['lot'] or '',
                                                                                 'in_qty': 0.0,
                                                                                 'in_cost': 0.0,
                                                                                 'in_amount': 0.0,
                                                                                 'out_qty': 0.0,
                                                                                 'out_cost': 0.0,
                                                                                 'out_amount': 0.0}
                        if r['type'] == 'in':
                            total_dict['whs'][wh.id]['in_qty'] += r['qty']
                            total_dict['whs'][wh.id]['in_cost'] += r['cost']
                            total_dict['whs'][wh.id]['in_amount'] += r['amount']
                            res[r['prod_id']]['whs'][wh.id]['in_qty'] += r['qty']
                            res[r['prod_id']]['whs'][wh.id]['in_cost'] += r['cost']
                            res[r['prod_id']]['whs'][wh.id]['in_amount'] += r['amount']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_qty'] += r['qty']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_cost'] += r['cost']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_amount'] += r['amount']
                        else:
                            total_dict['whs'][wh.id]['out_qty'] += r['qty']
                            total_dict['whs'][wh.id]['out_cost'] += r['cost']
                            total_dict['whs'][wh.id]['out_amount'] += r['amount']
                            res[r['prod_id']]['whs'][wh.id]['out_qty'] += r['qty']
                            res[r['prod_id']]['whs'][wh.id]['out_cost'] += r['cost']
                            res[r['prod_id']]['whs'][wh.id]['out_amount'] += r['amount']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_qty'] += r['qty']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_cost'] += r['cost']
                            res[r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_amount'] += r['amount']
        else:
            name_dict = {}
            prod_ids = []
            tids = []
            cr.execute("""SELECT t.id, t.name,o.product_id AS prod_id, p.ean13 AS ean,
                                SUM(coalesce((o.product_qty / u.factor * u2.factor), 0)) AS qty
                            FROM stock_transit_order t
                                JOIN procurement_order o ON t.id = o.transit_order_id
                                JOIN product_product p ON o.product_id = p.id
                                JOIN product_uom u ON o.product_uom = u.id
                                JOIN product_template pt ON p.product_tmpl_id = pt.id
                                JOIN product_uom u2 ON pt.uom_id = u2.id
                            WHERE o.state in ('confirm','done','running') 
                                AND t.date_order >= %s AND t.date_order <= %s
                                AND t.supply_warehouse_id = %s """+where+"""
                                AND t.warehouse_id in %s
                            GROUP BY t.id,t.name,o.product_id,p.ean13
                        """,(wiz['date_from'],wiz['date_to'],wiz['warehouse_id'][0],tuple(wids)))
            result = cr.dictfetchall()
            for r in result:
                if r['prod_id'] not in prod_ids:
                    prod_ids.append(r['prod_id'])
                if r['id'] not in tids:
                    tids.append(r['id'])
            if prod_ids:
                name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
            for r in result:
                if r['id'] not in  res:
                    res[r['id']] = {'name': r['name'] or u'Тодорхойгүй',
                                    'qty': 0.0,
                                    'whs': {},
                                    'lines': {}}
                if r['prod_id'] not in res[r['id']]['lines']:
                    res[r['id']]['lines'][r['prod_id']] = {'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                                           'ean': r['ean'] or '',
                                                           'qty': 0.0,
                                                           'lots':[],
                                                           'whs': {}}
                res[r['id']]['qty'] += r['qty']
                res[r['id']]['lines'][r['prod_id']]['qty'] += r['qty']
                total_dict['qty'] += r['qty']
            if tids:
                for wh in warehouses:
                    ware_names.append(wh.name)
                    if wh.id not in wids:
                        wids.append(wh.id)
                    name_dict = {}
                    prod_ids = []
                    if wh.id not in total_dict['whs']:
                        total_dict['whs'][wh.id] = {'in_qty': 0.0,
                                                    'in_cost': 0.0,
                                                    'in_amount': 0.0,
                                                    'out_qty': 0.0,
                                                    'out_cost': 0.0,
                                                    'out_amount': 0.0}
                    location_ids = self.pool.get('stock.location').search(cr, uid, 
                                                [('location_id','child_of',[wh.view_location_id.id]),
                                                 ('usage','=','internal')], context=context)
                    tuple_location = tuple(location_ids)
                    cr.execute("""SELECT t.id,t.name,sp.id AS pick_id, sp.name AS pname,
                                        m.product_id AS prod_id, p.ean13 AS ean, lot.name AS lot, 'out' AS type,
                                        SUM(link.qty * u.factor / u2.factor) AS qty,
                                        SUM(link.qty * u.factor / u2.factor * pack.cost) AS cost,
                                        SUM(link.qty * u.factor / u2.factor * pack.list_price) AS amount
                                    FROM stock_transit_order t 
                                        JOIN procurement_order o ON t.id = o.transit_order_id
                                        JOIN stock_move m ON o.id = m.procurement_id
                                        JOIN stock_picking sp ON m.picking_id = sp.id
                                        LEFT JOIN stock_move_operation_link link ON m.id = link.move_id
                                        LEFT JOIN stock_pack_operation pack ON link.operation_id = pack.id
                                        LEFT JOIN stock_production_lot lot ON pack.lot_id = lot.id
                                        JOIN product_product p ON m.product_id = p.id
                                        JOIN product_uom u ON pack.product_uom_id = u.id
                                        JOIN product_template pt ON p.product_tmpl_id = pt.id
                                        JOIN product_uom u2 ON pt.uom_id = u2.id
                                    WHERE m.state = 'done'
                                        AND m.date >= %s AND m.date <= %s
                                        AND t.supply_warehouse_id = %s AND t.id IN %s """+where+"""
                                        AND m.location_id IN %s AND m.location_dest_id NOT IN %s
                                    GROUP BY t.id,t.name,sp.id,sp.name,m.product_id,p.ean13,lot.name
                                UNION ALL 
                                    SELECT t.id,t.name,p.id AS pick_id, p.name AS pname,
                                        m.product_id AS prod_id, pp.ean13 AS ean, lot.name AS lot, 'in' AS type,
                                        SUM(link.qty * u.factor / u2.factor) AS qty,
                                        SUM(link.qty * u.factor / u2.factor * pack.cost) AS cost,
                                        SUM(link.qty * u.factor / u2.factor * pack.list_price) AS amount
                                    FROM stock_transit_order t 
                                        JOIN stock_picking p ON t.id = p.transit_order_id
                                        JOIN stock_move m ON p.id = m.picking_id
                                        LEFT JOIN stock_move_operation_link link ON m.id = link.move_id
                                        LEFT JOIN stock_pack_operation pack ON link.operation_id = pack.id
                                        LEFT JOIN stock_production_lot lot ON pack.lot_id = lot.id
                                        JOIN product_product pp ON m.product_id = pp.id
                                        JOIN product_uom u ON pack.product_uom_id = u.id
                                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                                        JOIN product_uom u2 ON pt.uom_id = u2.id
                                    WHERE m.state = 'done'
                                        AND m.date >= %s AND m.date <= %s
                                        AND t.supply_warehouse_id = %s AND t.id IN %s """+where+"""
                                        AND m.location_id NOT IN %s AND m.location_dest_id IN %s
                                    GROUP BY t.id,t.name,p.id,p.name,m.product_id,pp.ean13,lot.name
                                        """,(wiz['date_from'],wiz['date_to']+' 23:59:59',wiz['warehouse_id'][0],tuple(tids),tuple_location,tuple_location,
                                             wiz['date_from'],wiz['date_to']+' 23:59:59',wiz['warehouse_id'][0],tuple(tids),tuple_location,tuple_location))
                    result = cr.dictfetchall()
                    for r in result:
                        if r['prod_id'] not in prod_ids:
                            prod_ids.append(r['prod_id'])
                    if prod_ids:
                        name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
                    for r in result:
                        if r['id'] not in res:
                            res[r['id']] = {'name': r['name'] or u'Тодорхойгүй',
                                            'qty': 0.0,
                                            'whs': {},
                                            'lines': {}}
                        if r['prod_id'] not in res[r['id']]['lines']:
                            res[r['id']]['lines'][r['prod_id']] = {'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                                                   'ean': r['ean'] or '',
                                                                   'qty': 0.0,
                                                                   'lots':[],
                                                                   'whs': {}}
                        if r['lot'] not in res[r['id']]['lines'][r['prod_id']]['lots']:
                            res[r['id']]['lines'][r['prod_id']]['lots'].append(r['lot'])
                        if wh.id not in res[r['id']]['whs']:
                            res[r['id']]['whs'][wh.id] = {'in_qty': 0.0,
                                                          'in_cost': 0.0,
                                                          'in_amount': 0.0,
                                                          'out_qty': 0.0,
                                                          'out_cost': 0.0,
                                                          'out_amount': 0.0,}
                        if wh.id not in res[r['id']]['lines'][r['prod_id']]['whs']:
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id] = {'in_qty': 0.0,
                                                                                 'in_cost': 0.0,
                                                                                 'in_amount': 0.0,
                                                                                 'out_qty': 0.0,
                                                                                 'out_cost': 0.0,
                                                                                 'out_amount': 0.0,
                                                                                 'lots': {}}
                        if r['lot'] not in res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots']:
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']] = {'name': r['lot'] or '',
                                                                                                   'in_qty': 0.0,
                                                                                                   'in_cost': 0.0,
                                                                                                   'in_amount': 0.0,
                                                                                                   'out_qty': 0.0,
                                                                                                   'out_cost': 0.0,
                                                                                                   'out_amount': 0.0}
                        if r['type'] == 'in':
                            total_dict['whs'][wh.id]['in_qty'] += r['qty']
                            total_dict['whs'][wh.id]['in_cost'] += r['cost']
                            total_dict['whs'][wh.id]['in_amount'] += r['amount']
                            res[r['id']]['whs'][wh.id]['in_qty'] += r['qty']
                            res[r['id']]['whs'][wh.id]['in_cost'] += r['cost']
                            res[r['id']]['whs'][wh.id]['in_amount'] += r['amount']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['in_qty'] += r['qty']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['in_cost'] += r['cost']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['in_amount'] += r['amount']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_qty'] += r['qty']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_cost'] += r['cost']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['in_amount'] += r['amount']
                        else:
                            total_dict['whs'][wh.id]['out_qty'] += r['qty']
                            total_dict['whs'][wh.id]['out_cost'] += r['cost']
                            total_dict['whs'][wh.id]['out_amount'] += r['amount']
                            res[r['id']]['whs'][wh.id]['out_qty'] += r['qty']
                            res[r['id']]['whs'][wh.id]['out_cost'] += r['cost']
                            res[r['id']]['whs'][wh.id]['out_amount'] += r['amount']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['out_qty'] += r['qty']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['out_cost'] += r['cost']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['out_amount'] += r['amount']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_qty'] += r['qty']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_cost'] += r['cost']
                            res[r['id']]['lines'][r['prod_id']]['whs'][wh.id]['lots'][r['lot']]['out_amount'] += r['amount']
        if wiz['report_type'] == 'product':
            row = ['', u'<b><c>НИЙТ</c></b>', '']
        else:
            row = ['', u'<b><c>НИЙТ</c></b>']
            if wiz['type'] == 'detail':
                row += ['']
        row += ['<b>%s</b>' % total_dict['qty']]
        for wh in wids:
            if wiz['lot']:
                row += ['']
            if wh in total_dict['whs']:
                row += ['<b>%s</b>' % total_dict['whs'][wh]['in_qty'],
                        '<b>%s</b>' % total_dict['whs'][wh]['in_amount']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['whs'][wh]['in_cost']]
                row += ['<b>%s</b>' % total_dict['whs'][wh]['out_qty'],
                        '<b>%s</b>' % total_dict['whs'][wh]['out_amount']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['whs'][wh]['out_cost']]
            else:
                row += ['<b>0.0</b>','<b>0.0</b>']
                if wiz['cost']:
                    row += ['<b>0.0</b>']
                row += ['<b>0.0</b>','<b>0.0</b>']
                if wiz['cost']:
                    row += ['<b>0.0</b>']
        data.append(row)
        row_span = {}
        rowx = 1
        
        def to_rowspan(ix,iy):
            if row_span.has_key(ix[1]):
                row_span[ix[1]] += [[ix[0], iy[0], iy[1]]]
            else: 
                row_span.update({ix[1]:[[ix[0], iy[0], iy[1]]]})
                
        if res:
            number = 1
            row = []
            if wiz['report_type'] == 'product':
                for val in sorted(res.values(), key=itemgetter('name')):
                    
                    row.append([
                        '<str><c>%s</c></str>' % number,
                        '%s'%(val['name']),
                        '<str><c>%s</c></str>'%(val['ean']),val['qty']])
                    if len(val['lots']) > 1 and wiz['lot']:
                        for i in range(len(val['lots'])-1):
                            row.append([None,None,None,None])
                        to_rowspan((0,rowx),(0,rowx+len(val['lots'])-1))
                        to_rowspan((1,rowx),(1,rowx+len(val['lots'])-1))
                        to_rowspan((2,rowx),(2,rowx+len(val['lots'])-1))
                        to_rowspan((3,rowx),(3,rowx+len(val['lots'])-1))
                    colx = 4
                    for wh in wids:
                        if wh in val['whs']:
                            if wiz['lot']:
                                lrow = rowx-1
                                if val['whs'][wh]['lots']:
                                    for k,l in val['whs'][wh]['lots'].iteritems():
                                        row[lrow] += [l['name'],l['in_qty'],l['in_amount']]
                                        if wiz['cost']:
                                            row[lrow] += [l['in_cost']]
                                        row[lrow].extend([l['out_qty'],l['out_amount']])
                                        if wiz['cost']:
                                            row[lrow] += [l['out_cost']]
                                        lrow += 1
                                else:
                                    row[lrow] += ['',val['whs'][wh]['in_qty'],val['whs'][wh]['in_amount']]
                                    if wiz['cost']:
                                        row[lrow] += [val['whs'][wh]['in_cost']]
                                    row[lrow] += [val['whs'][wh]['out_qty'],val['whs'][wh]['out_amount']]
                                    if wiz['cost']:
                                        row[lrow] += [val['whs'][wh]['out_cost']]
                                colx += 5
                                if len(val['whs'][wh]['lots']) < len(val['lots']):
                                    for i in range(len(val['lots'])-len(val['whs'][wh]['lots'])):
                                        row[lrow] += [None,None,None,None,None]
                                        if wiz['cost']:
                                            row[lrow] += [None,None]
                                        lrow += 1
                                    to_rowspan((colx,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots']))),(colx,lrow-1))
                                    to_rowspan((colx+1,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots']))),(colx+1,lrow-1))
                                    to_rowspan((colx+2,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots']))),(colx+2,lrow-1))
                                    to_rowspan((colx+3,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots']))),(colx+3,lrow-1))
                                    to_rowspan((colx+4,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots']))),(colx+4,lrow-1))
                                    if wiz['cost']:
                                        to_rowspan((colx,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots'])))),(colx,lrow-1)
                                        to_rowspan((colx+1,(lrow-1-len(val['lots'])-len(val['whs'][wh]['lots'])))),(colx+1,lrow-1)
                                if wiz['cost']:
                                    colx += 2
                            else:
                                row[rowx-1] += [val['whs'][wh]['in_qty'],val['whs'][wh]['in_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += [val['whs'][wh]['in_cost']]
                                    colx += 1
                                row[rowx-1] += [val['whs'][wh]['out_qty'],val['whs'][wh]['out_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += [val['whs'][wh]['out_cost']]
                                    colx += 1
                        else:
                            if wiz['lot']:
                                row[rowx-1] += ['']
                                if len(val['lots']) > 1:
                                    to_rowspan((colx,rowx),(colx,rowx+len(val['lots'])-1))
                                colx += 1
                                if len(val['lots']) > 1:
                                    to_rowspan((colx,rowx),(colx,rowx+len(val['lots'])-1))
                                    to_rowspan((colx+1,rowx),(colx+1,rowx+len(val['lots'])-1))
                                    to_rowspan((colx+2,rowx),(colx+2,rowx+len(val['lots'])-1))
                                    to_rowspan((colx+3,rowx),(colx+3,rowx+len(val['lots'])-1))
                            row[rowx-1] += [0.0,0.0,0.0,0.0]
                            colx += 4
                            if wiz['cost']:
                                row[rowx-1] += [0.0,0.0]
                                if wiz['lot'] and len(val['lots']) > 1:
                                    to_rowspan((colx,rowx),(colx,rowx+len(val['lots'])-1))
                                    to_rowspan((colx+1,rowx),(colx+1,rowx+len(val['lots'])-1))
                                colx += 2
                            if len(val['lots']) > 1 and wiz['lot']:
                                for i in range(len(val['lots'])-1):
                                    row[rowx+i] += [None,None,None,None,None]
                                    if wiz['cost']:
                                        row[rowx+i] += [None,None]
                    if wiz['lot'] and len(val['lots']) > 1:
                        rowx += len(val['lots'])
                    else:
                        rowx += 1
                    number += 1
                data += row
            else:
                for val in sorted(res.values(), key=itemgetter('name')):
                    count = 1
                    row.append([
                        '<str><c>%s</c></str>' % number])
                    colx = 1
                    if wiz['type'] == 'detail':
                        row[rowx-1] += ['<b>%s</b>'%(val['name']),'','<b>%s</b>'%(val['qty'])]
                        colx += 3
                    else:
                        row[rowx-1] += ['%s'%(val['name']),val['qty']]
                        colx += 2
                    for wh in wids:
                        if wh in val['whs']:
                            if wiz['lot'] and wiz['type'] == 'detail':
                                row[rowx-1] += ['']
                                colx += 1
                            if wiz['type'] == 'detail':
                                row[rowx-1] += ['<b>%s</b>'%val['whs'][wh]['in_qty'],
                                              '<b>%s</b>'%val['whs'][wh]['in_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += ['<b>%s</b>'%val['whs'][wh]['in_cost']]
                                    colx += 1
                                row[rowx-1] += ['<b>%s</b>'%val['whs'][wh]['out_qty'],
                                              '<b>%s</b>'%val['whs'][wh]['out_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += ['<b>%s</b>'%val['whs'][wh]['out_cost']]
                                    colx += 1
                            else:
                                row[rowx-1] += [val['whs'][wh]['in_qty'],val['whs'][wh]['in_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += [val['whs'][wh]['in_cost']]
                                    colx += 1
                                row[rowx-1] += [val['whs'][wh]['out_qty'],val['whs'][wh]['out_amount']]
                                colx += 2
                                if wiz['cost']:
                                    row[rowx-1] += [val['whs'][wh]['out_cost']]
                                    colx += 1
                        else:
                            if wiz['lot'] and wiz['type'] == 'detail':
                                row[rowx-1] += ['']
                                colx += 1
                            if wiz['type'] == 'detail':
                                row[rowx-1] += ['<b>0.0</b>','<b>0.0</b>','<b>0.0</b>','<b>0.0</b>']
                                colx += 4
                                if wiz['cost']:
                                    row[rowx-1] += ['<b>0.0</b>','<b>0.0</b>']
                                    colx += 2
                            else:
                                row[rowx-1] += [0.0,0.0,0.0,0.0]
                                colx += 4
                                if wiz['cost']:
                                    row[rowx-1] += [0.0,0.0]
                                    colx += 2
                    rowx += 1
                    if wiz['type'] == 'detail':
                        for v in sorted(val['lines'].values(), key=itemgetter('name')):
                            row.append([
                                '<str><c>%s.%s</c></str>' % (number,count),
                                '%s'%(v['name']),
                                '<str><c>%s</c></str>'%(v['ean']),v['qty']])
                            if len(v['lots']) > 1 and wiz['lot']:
                                for i in range(len(v['lots'])-1):
                                    row.append([None,None,None,None])
                                to_rowspan((0,rowx),(0,rowx+len(v['lots'])-1))
                                to_rowspan((1,rowx),(1,rowx+len(v['lots'])-1))
                                to_rowspan((2,rowx),(2,rowx+len(v['lots'])-1))
                                to_rowspan((3,rowx),(3,rowx+len(v['lots'])-1))
                            colx = 4
                            for wh in wids:
                                if wh in v['whs']:
                                    if wiz['lot']:
                                        lrow = rowx-1
                                        if v['whs'][wh]['lots']:
                                            for k,l in v['whs'][wh]['lots'].iteritems():
                                                row[lrow] += [l['name'],l['in_qty'],l['in_amount']]
                                                if wiz['cost']:
                                                    row[lrow] += [l['in_cost']]
                                                row[lrow].extend([l['out_qty'],l['out_amount']])
                                                if wiz['cost']:
                                                    row[lrow] += [l['out_cost']]
                                                lrow += 1
                                        else:
                                            row[lrow] += ['',v['whs'][wh]['in_qty'],v['whs'][wh]['in_amount']]
                                            if wiz['cost']:
                                                row[lrow] += [v['whs'][wh]['in_cost']]
                                            row[lrow] += [v['whs'][wh]['out_qty'],v['whs'][wh]['out_amount']]
                                            if wiz['cost']:
                                                row[lrow] += [v['whs'][wh]['out_cost']]
                                        colx += 5
                                        if len(v['whs'][wh]['lots']) < len(v['lots']):
                                            for i in range(len(v['lots'])-len(v['whs'][wh]['lots'])):
                                                row[lrow] += [None,None,None,None,None]
                                                if wiz['cost']:
                                                    row[lrow] += [None,None]
                                                lrow += 1
                                            to_rowspan((colx,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots']))),(colx,lrow-1))
                                            to_rowspan((colx+1,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots']))),(colx+1,lrow-1))
                                            to_rowspan((colx+2,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots']))),(colx+2,lrow-1))
                                            to_rowspan((colx+3,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots']))),(colx+3,lrow-1))
                                            to_rowspan((colx+4,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots']))),(colx+4,lrow-1))
                                            if wiz['cost']:
                                                to_rowspan((colx,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots'])))),(colx,lrow-1)
                                                to_rowspan((colx+1,(lrow-1-len(v['lots'])-len(v['whs'][wh]['lots'])))),(colx+1,lrow-1)
                                        if wiz['cost']:
                                            colx += 2
                                    else:
                                        row[rowx-1] += [v['whs'][wh]['in_qty'],v['whs'][wh]['in_amount']]
                                        colx += 2
                                        if wiz['cost']:
                                            row[rowx-1] += [v['whs'][wh]['in_cost']]
                                            colx += 1
                                        row[rowx-1] += [v['whs'][wh]['out_qty'],v['whs'][wh]['out_amount']]
                                        colx += 2
                                        if wiz['cost']:
                                            row[rowx-1] += [v['whs'][wh]['out_cost']]
                                            colx += 1
                                else:
                                    if wiz['lot']:
                                        row[rowx-1] += ['']
                                        if len(v['lots']) > 1:
                                            to_rowspan((colx,rowx),(colx,rowx+len(v['lots'])-1))
                                        colx += 1
                                        if len(v['lots']) > 1:
                                            to_rowspan((colx,rowx),(colx,rowx+len(v['lots'])-1))
                                            to_rowspan((colx+1,rowx),(colx+1,rowx+len(v['lots'])-1))
                                            to_rowspan((colx+2,rowx),(colx+2,rowx+len(v['lots'])-1))
                                            to_rowspan((colx+3,rowx),(colx+3,rowx+len(v['lots'])-1))
                                    row[rowx-1] += [0.0,0.0,0.0,0.0]
                                    colx += 4
                                    if wiz['cost']:
                                        row[rowx-1] += [0.0,0.0]
                                        if wiz['lot'] and len(v['lots']) > 1:
                                            to_rowspan((colx,rowx),(colx,rowx+len(v['lots'])-1))
                                            to_rowspan((colx+1,rowx),(colx+1,rowx+len(v['lots'])-1))
                                        colx += 2
                                    if len(v['lots']) > 1 and wiz['lot']:
                                        for i in range(len(v['lots'])-1):
                                            row[rowx+i] += [None,None,None,None,None]
                                            if wiz['cost']:
                                                row[rowx+i] += [None,None]
                            if wiz['lot'] and len(v['lots']) > 1:
                                rowx += len(v['lots'])
                            else:
                                rowx += 1
                            count += 1
                    number += 1
                data += row
        return data, titles, ware_names, row_span
