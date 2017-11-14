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

class report_inventory_ledger(osv.osv_memory):
    _name = 'report.inventory.ledger'
    _inherit = 'abstract.report.model'
    _description = 'Report Inventory Ledger'
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_inventory_ledger_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'product_ids':  fields.many2many('product.product', 'report_inventory_ledger_product_rel',
                            'wizard_id', 'product_id', 'Product'),
        'category_ids': fields.many2many('product.category', 'report_inventory_ledger_category_rel',
                            'wizard_id', 'category_id', 'Category'),
        'partner_ids':  fields.many2many('res.partner', 'report_inventory_ledger_partner_rel', 
                            'wizard_id', 'partner_id', 'Partner'),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
        'income_view':  fields.boolean('Income Inventory'),
        'expense_view': fields.boolean('Expense Inventory'),
        'report_type':  fields.selection([('order','Orders'),('product','Products')], 'Report Type', required=True),
        'type':         fields.selection([('detail','Detail'),('summary','Summary')], 'Type', required=True),
        'cost': fields.boolean('Show Cost Amount?'),
        
    }
    
    def _get_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wids = (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
        if len(wids) > 1:
            return []
        return wids
    
    _defaults = {
        'company_id': lambda obj,cr,uid,c:obj.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory.report'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'income_view': True,
        'expense_view': True,
        'report_type': 'product',
        'type': 'detail',
        'cost': False,
        'warehouse_ids': _get_warehouse
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        wnames = ''
        for w in form.warehouse_ids:
            wnames += w.name
            wnames += ','
        body = (u"Тооллогын товчоо тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
          (form.date_from, form.date_to, wnames)
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
        if not wiz['income_view'] and not wiz['expense_view']:
            raise osv.except_osv(_('Warning !'), _("You don't checked any check field"))
        wids = []
        if wiz['warehouse_ids']:
            wids = wiz['warehouse_ids']
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wids, context=context)
        location_ids = []
        for w in warehouses:
            location_ids.extend(self.pool.get('stock.location').search(cr, uid, 
                                            [('location_id','child_of',[w.view_location_id.id]),
                                             ('usage','=','internal')], context=context))
        wiz['location_ids'] = location_ids
        data, titles = self.mirror_prepare_report_data(cr, uid, wiz, self._name, context=context)
        if wiz['report_type'] == 'product':
            widths = [2,10,4,4]
            headers = [
                [u'Д/д',u'Бараа материалын нэрс',u'Бар код',u'Сери дугаар'],
                [None,None,None,None]
            ]
            header_span = [((0,0),(0,1)), ((1,0),(1,1)), 
                           ((2,0),(2,1)), ((3,0),(3,1))]
            colx = 4
        else:
            widths = [2,10,4,4]
            headers = [
                [u'Д/д',u'Огноо',u'Баримт'],
                [None,None,None]
            ]
            header_span = [((0,0),(0,1)), ((1,0),(1,1)), ((2,0),(2,1))]
            colx = 3
            if wiz['type'] == 'detail':
                widths += [4]
                headers[0] += [u'Бар код']
                headers[1] += [None]
                header_span += [((3,0),(3,1))]
                colx += 1
        if wiz['income_view']:
            headers[0] += [u'Орлого',None]
            if wiz['cost']:
                headers[0] += [None]
                headers[1] += [u'Тоо ширхэг',u'Өртөг дүн',u'Үнийн дүн']
                header_span += [((colx,0),(colx+2,0))]
                widths += [3,4,4]
                colx += 3
            else:
                headers[1] += [u'Тоо ширхэг',u'Үнийн дүн']
                header_span += [((colx,0),(colx+1,0))]
                widths += [3,4]
                colx += 2
        if wiz['expense_view']:
            headers[0] += [u'Зарлага',None]
            if wiz['cost']:
                headers[0] += [None]
                headers[1] += [u'Тоо ширхэг',u'Өртөг дүн',u'Үнийн дүн']
                header_span += [((colx,0),(colx+2,0))]
                widths += [3,4,4]
                colx += 3
            else:
                headers[1] += [u'Тоо ширхэг',u'Үнийн дүн']
                header_span += [((colx,0),(colx+1,0))]
                widths += [3,4]
                colx += 2
        if wiz['income_view'] and wiz['expense_view']:
            headers[0] += [u'Зөрүү',None]
            if wiz['cost']:
                headers[0] += [None]
                headers[1] += [u'Тоо ширхэг',u'Өртөг дүн',u'Үнийн дүн']
                header_span += [((colx,0),(colx+2,0))]
                widths += [3,4,4]
                colx += 3
            else:
                headers[1] += [u'Тоо ширхэг',u'Үнийн дүн']
                header_span += [((colx,0),(colx+1,0))]
                widths += [3,4]
                colx += 2
        datas = {
            'title': u'Тооллогын товчоо тайлан',
            'headers': headers,
            'header_span': header_span,
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas':datas}
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        wnames = ''
        ware_names = {}
        wids = []
        if wiz['warehouse_ids']:
            wids = wiz['warehouse_ids']
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wids, context=context)
        for w in warehouses:
            wnames += w.name
            wnames += ','
            ware_names.update({w.id: w.name})
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'],wiz['date_to']),
                  u'Салбар: %s'%(wnames)]
        data = []
        res = {}
        where = ''
        location_tuple = tuple(wiz['location_ids'])
        total_dict = {}
        if wiz['report_type'] == 'product':
            total_dict = {'qty': 0, 'amount': 0.0,'cost': 0,
                          'income': {'qty': 0, 'cost': 0,'amount': 0},
                          'outcome': {'qty': 0, 'cost': 0,'amount': 0}}
        else:
            total_dict = {'amount': {'income': 0, 'outcome': 0,'amount': 0},
                          'qty': {'income': 0, 'outcome': 0, 'qty': 0},
                          'cost': {'income': 0, 'outcome': 0, 'cost': 0}}
        if wiz['product_ids']:
            where = " AND m.product_id in ("+",".join(map(str,wiz['product_ids']))+") "
        if wiz['category_ids']:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',wiz['category_ids'])])
            where += " AND pt.categ_id in ("+",".join(map(str,categ_ids))+") "
        if wiz['partner_ids']:
            where = " AND pt.manufacturer in ("+",".join(map(str,wiz['partner_ids']))+") "
        if wiz['report_type'] == 'product':
            if wiz['income_view']:
                prod_ids = []
                name_dict = {}
                
                cr.execute("""SELECT m.product_id AS prod_id,pp.ean13 AS ean, lot.id AS lot_id, lot.name AS lot, 
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor), 0)) AS qty,
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor * m.price_unit), 0)) AS cost,
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor * m.list_price), 0)) AS amount
                               FROM stock_inventory i
                                   JOIN stock_move m ON (m.inventory_id=i.id) 
                                   LEFT JOIN stock_production_lot lot ON (m.restrict_lot_id = lot.id)
                                   JOIN product_uom u ON (u.id=m.product_uom) 
                                   JOIN product_product AS pp ON m.product_id = pp.id 
                                   JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                                   JOIN product_uom AS muom ON pt.uom_id = muom.id 
                               WHERE i.state IN ('counted','done') 
                                   AND m.state = 'done' AND m.company_id = %s"""+where+"""
                                   AND m.location_id not in %s AND m.location_dest_id in %s  
                                   AND m.date >= %s AND m.date <= %s 
                               GROUP BY m.product_id,lot.id,lot.name,pp.ean13
                        """,(wiz['company_id'][0],location_tuple,location_tuple,wiz['date_from'],wiz['date_to']+' 23:59:59'))
                result1 = cr.dictfetchall()
                for r in result1:
                    if r['prod_id'] not in prod_ids:
                        prod_ids.append(r['prod_id'])
                if prod_ids:
                    name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
                for r in result1:
                    key = '%s.%s' % (r['prod_id'], r['lot_id'])
                    if key not in res:
                        res.update({key: {'in_qty': 0,
                                          'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                          'in_amount': 0.0,
                                          'in_cost': 0.0,
                                          'lot': r['lot'] or '',
                                          'ean': r['ean'] or '',
                                          'out_qty': 0,
                                          'out_cost': 0.0,
                                          'out_amount': 0.0,
                                          'qty': 0.0,
                                          'cost': 0.0,
                                          'amount': 0.0,
                                          }})
                    total_dict['qty'] += r['qty']
                    total_dict['cost'] += r['cost']
                    total_dict['amount'] += r['amount']
                    total_dict['income']['qty'] += r['qty']
                    total_dict['income']['cost'] += r['cost']
                    total_dict['income']['amount'] += r['amount']
                    res[key]['in_qty'] += r['qty']
                    res[key]['in_cost'] += r['cost']
                    res[key]['in_amount'] += r['amount']
                    res[key]['qty'] += r['qty']
                    res[key]['cost'] += r['cost']
                    res[key]['amount'] += r['amount']
            if wiz['expense_view']:
                prod_ids = []
                name_dict = {}
                cr.execute("""SELECT m.product_id AS prod_id,pp.ean13 AS ean, lot.id AS lot_id, lot.name AS lot,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor), 0)) AS qty,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor * m.price_unit), 0)) AS cost,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor * m.list_price), 0)) AS amount
                                FROM stock_inventory i 
                                    JOIN stock_move m ON (m.inventory_id=i.id)
                                    JOIN product_uom u ON (u.id=m.product_uom)
                                    LEFT JOIN stock_production_lot lot ON (m.restrict_lot_id=lot.id)
                                    JOIN product_product AS pp ON m.product_id = pp.id 
                                    JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                                    JOIN product_uom AS muom ON pt.uom_id = muom.id 
                                WHERE i.state IN ('counted','done') 
                                    AND m.state = 'done' AND m.company_id = %s """+where+"""
                                    AND m.location_id in %s AND m.location_dest_id not in %s  
                                    AND m.date >= %s AND m.date <= %s 
                                GROUP BY m.product_id,lot.id,lot.name,pp.ean13""",
                        (wiz['company_id'][0],location_tuple,location_tuple,wiz['date_from'],wiz['date_to']+' 23:59:59'))
                result2 = cr.dictfetchall()
                for r in result2:
                    if r['prod_id'] not in prod_ids:
                        prod_ids.append(r['prod_id'])
                if prod_ids:
                    name_dict  = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
                for r in result2:
                    key = '%s.%s' % (r['prod_id'], r['lot_id'])
                    if key not in res:
                        res.update({key: {'in_qty': 0,
                                          'name': name_dict.get(r['prod_id'],u'Тодорхойгүй'),
                                          'in_amount': 0.0,
                                          'in_cost': 0.0,
                                          'lot': r['lot'] or '',
                                          'ean': r['ean'] or '',
                                          'out_qty': 0,
                                          'out_cost': 0,
                                          'out_amount': 0.0,
                                          'qty': 0,
                                          'cost': 0.0,
                                          'amount': 0.0}})
                    total_dict['qty'] -= r['qty']
                    total_dict['cost'] -= r['cost']
                    total_dict['amount'] -= r['amount']
                    total_dict['outcome']['qty'] += r['qty']
                    total_dict['outcome']['cost'] += r['cost']
                    total_dict['outcome']['amount'] += r['amount']
                    res[key]['out_qty'] += r['qty']
                    res[key]['out_cost'] += r['cost']
                    res[key]['out_amount'] += r['amount']
                    res[key]['qty'] -= r['qty']
                    res[key]['cost'] -= r['cost']
                    res[key]['amount'] -= r['amount']
        else:
            if wiz['income_view']:
                cr.execute("""SELECT i.id, i.warehouse_id, i.name, i.specification,
                                   (CASE WHEN i.state = 'done' THEN i.date_done ELSE i.date END) AS date,
                                   m.product_id AS prod_id, pp.ean13,
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor), 0)) AS qty,
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor * m.price_unit), 0)) AS cost,
                                   SUM(coalesce((m.product_qty / u.factor * muom.factor * m.list_price), 0)) AS amount
                               FROM stock_inventory i
                                   JOIN stock_move m ON (m.inventory_id=i.id) 
                                   LEFT JOIN stock_production_lot lot ON (m.restrict_lot_id = lot.id)
                                   JOIN product_uom u ON (u.id=m.product_uom) 
                                   JOIN product_product AS pp ON m.product_id = pp.id 
                                   JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                                   JOIN product_uom AS muom ON pt.uom_id = muom.id 
                               WHERE i.state IN ('counted','done') 
                                   AND m.state = 'done' AND m.company_id = %s """+where+"""
                                   AND m.location_id not in %s AND m.location_dest_id in %s  
                                   AND m.date >= %s AND m.date <= %s 
                               GROUP BY i.date_done,i.id, i.warehouse_id, i.name, i.specification,m.product_id,pp.ean13
                               ORDER BY i.date_done""",
                               (wiz['company_id'][0],location_tuple,location_tuple,wiz['date_from'],wiz['date_to']+' 23:59:59'))
                result = cr.fetchall()
                if result:
                    name_dict = {}
                    prod_ids = map(lambda x:x[5], result)
                    if prod_ids:
                        name_dict = dict( self.pool.get('product.product').name_get(cr, uid, prod_ids, context={'display_ean': True}) )
                    for pid, wid, iname, spec, dates, prod, ean, qty, cost, amount in result:
                        idates = ''
                        if dates:
                            idates = dates.split(' ')[0]
                        if spec:
                            iname += ' %s'%spec
                        if wid not in res:
                            res[wid] = {'name': ware_names.get(wid,u'Тодорхойгүй'),
                                            'in_qty': 0.0,
                                            'out_qty': 0.0,
                                            'in_cost': 0.0,
                                            'out_cost': 0.0,
                                            'in_amount': 0.0,
                                            'out_amount': 0.0,
                                            'qty': 0,
                                            'cost': 0,
                                            'amount': 0,
                                            'lines': {}}
                        if pid not in res[wid]['lines']:
                            res[wid]['lines'][pid] = {'name': iname,
                                                      'date': idates,
                                                      'qty': 0,
                                                      'cost': 0.0,
                                                      'amount': 0.0,
                                                      'in_qty': 0.0,
                                                      'out_qty': 0.0,
                                                      'in_cost': 0.0,
                                                      'out_cost': 0.0,
                                                      'in_amount': 0.0,
                                                      'out_amount': 0.0,
                                                      'lines': {}}
                        if prod not in res[wid]['lines'][pid]['lines']:
                            res[wid]['lines'][pid]['lines'][prod] = {'name': name_dict.get(prod,u'Тодорхойгүй'),
                                                                     'ean': ean or '',
                                                                     'qty': 0,
                                                                     'cost': 0.0,
                                                                     'amount': 0.0,
                                                                     'in_qty': 0.0,
                                                                     'out_qty': 0.0,
                                                                     'in_cost': 0.0,
                                                                     'out_cost': 0.0,
                                                                     'in_amount': 0.0,
                                                                     'out_amount': 0.0}
                        res[wid]['cost'] += cost
                        res[wid]['qty'] += qty
                        res[wid]['amount'] += amount
                        res[wid]['in_cost'] += cost
                        res[wid]['in_qty'] += qty
                        res[wid]['in_amount'] += amount
                        res[wid]['lines'][pid]['cost'] += cost
                        res[wid]['lines'][pid]['qty'] += qty
                        res[wid]['lines'][pid]['amount'] += amount
                        res[wid]['lines'][pid]['in_cost'] += cost
                        res[wid]['lines'][pid]['in_qty'] += qty
                        res[wid]['lines'][pid]['in_amount'] += amount
                        res[wid]['lines'][pid]['lines'][prod]['cost'] += cost
                        res[wid]['lines'][pid]['lines'][prod]['qty'] += qty
                        res[wid]['lines'][pid]['lines'][prod]['amount'] += amount
                        res[wid]['lines'][pid]['lines'][prod]['in_cost'] += cost
                        res[wid]['lines'][pid]['lines'][prod]['in_qty'] += qty
                        res[wid]['lines'][pid]['lines'][prod]['in_amount'] += amount
                        total_dict['cost']['income'] += cost
                        total_dict['qty']['income'] += qty
                        total_dict['amount']['income'] += amount
                        total_dict['cost']['cost'] += cost
                        total_dict['qty']['qty'] += qty
                        total_dict['amount']['amount'] += amount
            if wiz['expense_view']:
                cr.execute("""SELECT i.id, i.warehouse_id, i.name, i.specification, 
                                    (CASE WHEN i.state = 'done' THEN i.date_done ELSE i.date END) as date,
                                    m.product_id AS prod_id,pp.ean13,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor), 0)) AS qty,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor * m.price_unit), 0)) AS cost,
                                    SUM(coalesce((m.product_qty / u.factor * muom.factor * m.list_price), 0)) AS amount
                                FROM stock_inventory i
                                    JOIN stock_move m ON (m.inventory_id=i.id) 
                                    JOIN product_uom u ON (u.id=m.product_uom)
                                    LEFT JOIN stock_production_lot lot ON (m.restrict_lot_id=lot.id)
                                    JOIN product_product AS pp ON m.product_id = pp.id 
                                    JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                                    JOIN product_uom AS muom ON pt.uom_id = muom.id 
                                WHERE i.state IN ('counted','done') 
                                    AND m.state = 'done' AND m.company_id = %s """+where+"""
                                    AND m.location_id in %s AND m.location_dest_id not in %s  
                                    AND m.date >= %s AND m.date <= %s
                                GROUP BY i.date_done,i.id, i.warehouse_id, i.name, i.specification,m.product_id,pp.ean13""",
                               (wiz['company_id'][0],location_tuple,location_tuple,wiz['date_from'],wiz['date_to']+' 23:59:59'))
                result = cr.fetchall()
                if result:
                    name_dict = {}
                    prod_ids = map(lambda x:x[5], result)
                    if prod_ids:
                        name_dict = dict( self.pool.get('product.product').name_get(cr, uid, prod_ids, context={'display_ean': True}) )
                    for pid, wid, iname, spec, dates, prod, ean, qty, cost, amount in result:
                        idates = ''
                        if dates:
                            idates = dates.split(' ')[0]
                        if spec:
                            iname += ' %s'%spec
                        if wid not in res:
                            res[wid] = {'name': ware_names.get(wid,u'Тодорхойгүй'),
                                            'in_qty': 0.0,
                                            'out_qty': 0.0,
                                            'in_cost': 0.0,
                                            'out_cost': 0.0,
                                            'in_amount': 0.0,
                                            'out_amount': 0.0,
                                            'qty': 0.0,
                                            'cost': 0.0,
                                            'amount': 0.0,
                                            'lines': {}}
                        if pid not in res[wid]['lines']:
                            res[wid]['lines'][pid] = {'name': iname,
                                                      'date': idates,
                                                      'qty': 0.0,
                                                      'cost': 0.0,
                                                      'amount': 0.0,
                                                      'in_qty': 0.0,
                                                      'out_qty': 0.0,
                                                      'in_cost': 0.0,
                                                      'out_cost': 0.0,
                                                      'in_amount': 0.0,
                                                      'out_amount': 0.0,
                                                      'lines': {}}
                        if prod not in res[wid]['lines'][pid]['lines']:
                            res[wid]['lines'][pid]['lines'][prod] = {'name': name_dict.get(prod,u'Тодорхойгүй'),
                                                                     'ean': ean or '',
                                                                     'qty': 0.0,
                                                                     'cost': 0.0,
                                                                     'amount': 0.0,
                                                                     'in_qty': 0.0,
                                                                     'out_qty': 0.0,
                                                                     'in_cost': 0.0,
                                                                     'out_cost': 0.0,
                                                                     'in_amount': 0.0,
                                                                     'out_amount': 0.0}
                        res[wid]['cost'] -= cost
                        res[wid]['qty'] -= qty
                        res[wid]['amount'] -= amount
                        res[wid]['out_cost'] += cost
                        res[wid]['out_qty'] += qty
                        res[wid]['out_amount'] += amount
                        res[wid]['lines'][pid]['cost'] -= cost
                        res[wid]['lines'][pid]['qty'] -= qty
                        res[wid]['lines'][pid]['amount'] -= amount
                        res[wid]['lines'][pid]['out_cost'] += cost
                        res[wid]['lines'][pid]['out_qty'] += qty
                        res[wid]['lines'][pid]['out_amount'] += amount
                        res[wid]['lines'][pid]['lines'][prod]['cost'] -= cost
                        res[wid]['lines'][pid]['lines'][prod]['qty'] -= qty
                        res[wid]['lines'][pid]['lines'][prod]['amount'] -= amount
                        res[wid]['lines'][pid]['lines'][prod]['out_cost'] += cost
                        res[wid]['lines'][pid]['lines'][prod]['out_qty'] += qty
                        res[wid]['lines'][pid]['lines'][prod]['out_amount'] += amount
                        total_dict['cost']['outcome'] += cost
                        total_dict['qty']['outcome'] += qty
                        total_dict['amount']['outcome'] += amount
                        total_dict['cost']['cost'] -= cost
                        total_dict['qty']['qty'] -= qty
                        total_dict['amount']['amount'] -= amount
        if wiz['report_type'] == 'product':
            row = ['', u'<b><c>НИЙТ</c></b>', '','']
        else:
            row = ['', '',u'<b><c>НИЙТ</c></b>']
        if wiz['type'] == 'detail':
            row += ['']
        if wiz['income_view']:
            if wiz['report_type'] == 'product':
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['income']['qty'],
                            '<b>%s</b>' % total_dict['income']['cost'],
                            '<b>%s</b>' % total_dict['income']['amount']]
                else:
                    row += ['<b>%s</b>' % total_dict['income']['qty'],
                            '<b>%s</b>' % total_dict['income']['amount']]
            else:
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['qty']['income'],
                            '<b>%s</b>' % total_dict['cost']['income'],
                            '<b>%s</b>' % total_dict['amount']['income']]
                else:
                    row += ['<b>%s</b>' % total_dict['qty']['income'],
                            '<b>%s</b>' % total_dict['amount']['income']]
        if wiz['expense_view']:
            if wiz['report_type'] == 'product':
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['outcome']['qty'],
                            '<b>%s</b>' % total_dict['outcome']['cost'],
                            '<b>%s</b>' % total_dict['outcome']['amount']]
                else:
                    row += ['<b>%s</b>' % total_dict['outcome']['qty'],
                            '<b>%s</b>' % total_dict['outcome']['amount']]
            else:
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['qty']['outcome'],
                            '<b>%s</b>' % total_dict['cost']['outcome'],
                            '<b>%s</b>' % total_dict['amount']['outcome']]
                else:
                    row += ['<b>%s</b>' % total_dict['qty']['outcome'],
                            '<b>%s</b>' % total_dict['amount']['outcome']]
        if wiz['report_type'] == 'product':
            if wiz['cost']:
                row += ['<b>%s</b>' % total_dict['qty'],
                        '<b>%s</b>' % total_dict['cost'],
                        '<b>%s</b>' % total_dict['amount']]
            else:
                row += ['<b>%s</b>' % total_dict['qty'],
                        '<b>%s</b>' % total_dict['amount']]
        else:
            if wiz['cost']:
                row += ['<b>%s</b>' % total_dict['qty']['qty'],
                        '<b>%s</b>' % total_dict['cost']['cost'],
                        '<b>%s</b>' % total_dict['amount']['amount']]
            else:
                row += ['<b>%s</b>' % total_dict['qty']['qty'],
                        '<b>%s</b>' % total_dict['amount']['amount']]
        data.append(row)
        if res:
            number = 1
            if wiz['report_type'] == 'product':
                for val in sorted(res.values(), key=itemgetter('name')):
                    row = [
                        '<str>%s</str>' % number,
                        '%s'%(val['name']),
                        '<str><c>%s</c></str>'%(val['ean']),
                        '<c>%s</c>'%(val['lot'])]
                    if wiz['income_view']:
                        if wiz['cost']:
                            row += [val['in_qty'],val['in_cost'],val['in_amount']]
                        else:
                            row += [val['in_qty'],val['in_amount']]
                    if wiz['expense_view']:
                        if wiz['cost']:
                            row += [val['out_qty'],val['out_cost'],val['out_amount']]
                        else:
                            row += [val['out_qty'],val['out_amount']]
                    if wiz['income_view'] and wiz['expense_view']:
                        if wiz['cost']:
                            row += [val['qty'],val['cost'],val['amount']]
                        else:
                            row += [val['qty'],val['amount']]
                    number += 1
                    data.append(row)
            else:
                for val in sorted(res.values(), key=itemgetter('name')):
                    count = 1
                    row = [
                        '<str>%s</str>' % number,
                        '',
                        '<c><b>%s</b></c>'%(val['name'])]
                    if wiz['type'] == 'detail':
                            row += ['']
                    if wiz['income_view']:
                        if wiz['cost']:
                            row += ['<b>%s</b>'%val['in_qty'],'<b>%s</b>'%val['in_cost'],'<b>%s</b>'%val['in_amount']]
                        else:
                            row += ['<b>%s</b>'%val['in_qty'],'<b>%s</b>'%val['in_amount']]
                    if wiz['expense_view']:
                        if wiz['cost']:
                            row += ['<b>%s</b>'%val['out_qty'],'<b>%s</b>'%val['out_cost'],'<b>%s</b>'%val['out_amount']]
                        else:
                            row += ['<b>%s</b>'%val['out_qty'],'<b>%s</b>'%val['out_amount']]
                    if wiz['income_view'] and wiz['expense_view']:
                        if wiz['cost']:
                            row += ['<b>%s</b>'%val['qty'],'<b>%s</b>'%val['cost'],'<b>%s</b>'%val['amount']]
                        else:
                            row += ['<b>%s</b>'%val['qty'],'<b>%s</b>'%val['amount']]
                    data.append(row)
                    for v in sorted(val['lines'].values(), key=itemgetter('name')):
                        if wiz['type'] == 'detail':
                            row = [
                                '<str>%s.%s</str>' % (number,count),
                                '<c>%s</c>'%(v['date']),'<b>%s</b>'%v['name'],'']
                            if wiz['income_view']:
                                if wiz['cost']:
                                    row += ['<b>%s</b>'%v['in_qty'],'<b>%s</b>'%v['in_cost'],'<b>%s</b>'%v['in_amount']]
                                else:
                                    row += ['<b>%s</b>'%v['in_qty'],'<b>%s</b>'%v['in_amount']]
                            if wiz['expense_view']:
                                if wiz['cost']:
                                    row += ['<b>%s</b>'%v['out_qty'],'<b>%s</b>'%v['out_cost'],'<b>%s</b>'%v['out_amount']]
                                else:
                                    row += ['<b>%s</b>'%v['out_qty'],'<b>%s</b>'%v['out_amount']]
                            if wiz['income_view'] and wiz['expense_view']:
                                if wiz['cost']:
                                    row += ['<b>%s</b>'%v['qty'],'<b>%s</b>'%v['cost'],'<b>%s</b>'%v['amount']]
                                else:
                                    row += ['<b>%s</b>'%v['qty'],'<b>%s</b>'%v['amount']]
                        else:
                            row = [
                                '<str>%s.%s</str>' % (number,count),
                                '<c>%s</c>'%(v['date']),
                                v['name']]
                            if wiz['income_view']:
                                if wiz['cost']:
                                    row += [v['in_qty'],v['in_cost'],v['in_amount']]
                                else:
                                    row += [v['in_qty'],v['in_amount']]
                            if wiz['expense_view']:
                                if wiz['cost']:
                                    row += [v['out_qty'],v['out_cost'],v['out_amount']]
                                else:
                                    row += [v['out_qty'],v['out_amount']]
                            if wiz['income_view'] and wiz['expense_view']:
                                if wiz['cost']:
                                    row += [v['qty'],v['cost'],v['amount']]
                                else:
                                    row += [v['qty'],v['amount']]
                        data.append(row)
                        if wiz['type'] == 'detail':
                            rcount = 1
                            for l in sorted(v['lines'].values(), key=itemgetter('name')):
                                row = [
                                    '<str><c>%s.%s.%s</c></str>' % (number,count,rcount),
                                    '',
                                    l['name'],'<str><c>%s</c></str>'%(l['ean'])]
                                if wiz['income_view']:
                                    if wiz['cost']:
                                        row += [l['in_qty'],l['in_cost'],l['in_amount']]
                                    else:
                                        row += [l['in_qty'],l['in_amount']]
                                if wiz['expense_view']:
                                    if wiz['cost']:
                                        row += [l['out_qty'],l['out_cost'],l['out_amount']]
                                    else:
                                        row += [l['out_qty'],l['out_amount']]
                                if wiz['income_view'] and wiz['expense_view']:
                                    if wiz['cost']:
                                        row += [l['qty'],l['cost'],l['amount']]
                                    else:
                                        row += [l['qty'],l['amount']]
                                data.append(row)
                                rcount += 1
                        count += 1
                    number += 1
        return data, titles
