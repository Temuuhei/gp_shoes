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

import time
from lxml import etree
from openerp.osv import osv,fields
from openerp.tools.translate import _
from datetime import datetime
from operator import itemgetter
from _ast import Pass

class report_consume_order(osv.osv_memory):
    _name = 'report.consume.order'
    _inherit = 'abstract.report.model'
    _description = 'Report Consume Order'
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_consume_order_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'product_ids':  fields.many2many('product.product', 'report_consume_order_product_rel',
                            'wizard_id', 'product_id', 'Product'),
        'partner_ids':  fields.many2many('res.partner', 'report_consume_order_partner_rel',
                            'wizard_id', 'partner_id', 'Partner'),
        'category_ids':  fields.many2many('product.category', 'report_consume_order_category_rel',
                            'wizard_id', 'category_id', 'Partner Category'),
        'account_ids':  fields.many2many('account.account', 'report_consume_order_account_rel',
                            'wizard_id', 'account_id', 'Expense Account'),
#        'type':         fields.selection([('account','Account'),('analytic_account','Analytic Account')], 'Type', required=True),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
    }
    
    def _get_warehouse(self, cr, uid, context=None):
        '''
            Боломжит агуулахуудыг олж тодорхойлно.
        '''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
    
    _defaults = {
        'company_id': lambda obj, cr, uid, c:obj.pool.get('res.company')._company_default_get(cr, uid, 'report.consume.order'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'warehouse_ids': _get_warehouse,
#        'type': 'account',
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        wnames = ''
        for w in form.warehouse_ids:
            wnames += w.name
            wnames += ','
        body = (u"Дотоод зарлагын тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
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
        data, titles = self.mirror_prepare_report_data(cr, uid, wiz, self._name, context=context)
        widths = [2,4,6,6,6,8]
        headers = [ [_('Seq.'), _('Date'), _('Document Ref'), _('Picking Document Ref'), _('Analytic Account'), _('Partner')]]
        headers[0] += [ _('Quantity'), _('Cost Price'), _('Total Cost')]
        widths += [4,4,4]
        
        datas = {
            'title': _('Report Consume Order'),
            'headers': headers,
            'header_span': [],
            'titles': titles,
            'rows': data,
#            'row_span': rowspan,
            'widths': widths,
        }
        return {'datas':datas}
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        account_obj = self.pool.get('account.account')
        wnames = ''
        location_ids = []
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        for w in warehouses:
            wnames += w.name
            wnames += ','
            location_ids.extend(location_obj.search(cr, uid,
                                            [('location_id', 'child_of', [w.view_location_id.id]),
                                             ('usage', '=', 'internal')], context=context))
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'], wiz['date_to']),
                  u'Салбар: %s' % (wnames)]
        data = []
        pick_ids = []
        res = {}
        where = ''
        location_tuple = tuple(location_ids)
        seq = 0
        total_dict = {'qty': 0,
                      'total_cost':0}
        if wiz['product_ids']:
            where += ' AND m.product_id IN (' + ','.join(map(str, wiz['product_ids'])) + ') '
        if wiz['partner_ids']:
            where += ' AND p.partner_id IN (' + ','.join(map(str, wiz['partner_ids'])) + ') '
        if wiz['category_ids']:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id', 'child_of', wiz['category_ids'])])
            where += ' AND pt.categ_id IN (' + ','.join(map(str, categ_ids)) + ') '
            
        if wiz['account_ids']:
            account_ids = wiz['account_ids']
        else:
#             account_ids = account_obj.search(cr, uid, [('user_type.report_type', '=', 'expense'), ('type', '!=', 'view')])
            account_ids = account_obj.search(cr, uid, [])
        prod_ids = []
        picking_name = ''
        cr.execute("SELECT cast(m.date as date) AS date, p.name AS picking_name, c.name AS name, "
                        "(CASE WHEN m.picking_id is not null THEN rp.name WHEN m.warehouse_id is not null "
                            "AND sw.partner_id is not null THEN rp2.name ELSE '' END) AS partner, "
                        "m.product_id AS prod_id, aa.name AS analytic_account, a.name AS account, a.code AS account_code,  "
                        "SUM(coalesce((m.product_qty / u.factor * u2.factor),0)) AS qty, "
                        "SUM(coalesce((m.price_unit / u.factor * u2.factor),0)) AS cost_price, "
                        "SUM(coalesce((m.price_unit * m.product_qty / u.factor * u2.factor),0)) AS cost "
                    "FROM stock_move AS m "
                        "LEFT JOIN stock_picking AS p ON (m.picking_id = p.id) "
                        "LEFT JOIN stock_consume_order c ON (p.consume_order_id = c.id)"
                        "LEFT JOIN res_partner AS rp ON (p.partner_id = rp.id) "
                        "JOIN product_product AS pp ON (m.product_id = pp.id) "
                        "JOIN product_template AS pt ON (pp.product_tmpl_id = pt.id) "
                        "JOIN product_uom AS u ON (m.product_uom = u.id) "
                        "JOIN product_uom AS u2 ON (pt.uom_id = u2.id) "
                        "LEFT JOIN stock_warehouse AS sw ON (m.warehouse_id = sw.id) "
                        "LEFT JOIN res_partner AS rp2 ON (sw.partner_id = rp2.id) "
                        "LEFT JOIN account_analytic_account AS aa ON (c.analytic_account_id = aa.id) "
                        "LEFT JOIN account_account AS a ON (c.expense_account_id = a.id) "
                    "WHERE m.location_id IN %s AND m.location_dest_id NOT IN %s "
                        "AND m.state = 'done' AND c.expense_account_id in %s"
                        "AND m.date >= %s AND m.date <= %s " + where + " "
                    "GROUP BY m.date,p.name, c.name,m.picking_id,rp.name,m.warehouse_id,sw.partner_id, "
                        "rp2.name,m.product_id,aa.name, c.expense_account_id, a.name, a.code "
                    "ORDER BY m.date, c.name, p.name"
                        , (location_tuple, location_tuple, tuple(account_ids), wiz['date_from'], wiz['date_to'] + ' 23:59:59'))
        result = cr.dictfetchall()
        for r in result:
            if r['prod_id'] not in prod_ids:
                    prod_ids.append(r['prod_id'])
        if prod_ids:
            name_dict = dict(product_obj.name_get(cr, uid, prod_ids, context=context))
        for r in result:
            if r['account'] not in res:
                account = account_obj.browse(cr, uid, r['account'], context=context)
                res[r['account']] = {'name': r['account'] or '',
                                     'account_code': r['account_code'] or '',
                                     'lines': {},
                                     'qty': 0,
                                     'total_cost':0}
            res[r['account']]['qty'] += r['qty']
            res[r['account']]['total_cost'] += r['cost'] 
            if r['name'] not in res[r['account']]['lines']:
                res[r['account']]['lines'][r['name']] = {'date': r['date'],
                                                         'name': r['name'] or '',
                                                         'picking_name': '',
                                                         'analytic_account': r['analytic_account'] or '',
                                                         'partner': r['partner'] or '',
                                                         'qty': 0,
                                                         'total_cost':0,
                                                         'lines':{}}
            if picking_name == '' or picking_name <> r['picking_name']:
                res[r['account']]['lines'][r['name']]['picking_name'] += r['picking_name'] + ' '
            res[r['account']]['lines'][r['name']]['qty'] += r['qty']
            res[r['account']]['lines'][r['name']]['total_cost'] += r['cost']
            picking_name = r['picking_name']
            if r['prod_id'] not in res[r['account']]['lines'][r['name']]['lines']:
                res[r['account']]['lines'][r['name']]['lines'][r['prod_id']] = {'date': '',
                                                                                'partner': '',
                                                                                'picking_name': '',
                                                                                'analytic_account': '',
                                                                                'name': name_dict.get(r['prod_id'], ''),
                                                                                'qty': 0,
                                                                                'cost_price':0,
                                                                                'total_cost':0}
            res[r['account']]['lines'][r['name']]['lines'][r['prod_id']]['qty'] += r['qty']
            res[r['account']]['lines'][r['name']]['lines'][r['prod_id']]['cost_price'] += r['cost_price']
            res[r['account']]['lines'][r['name']]['lines'][r['prod_id']]['total_cost'] += r['cost']
        
            total_dict['qty'] += r['qty']
            total_dict['total_cost'] += r['cost']
        # Нийт дүнг бичих мөр
        row = ['', '', '', '', '', u'<b><c>НИЙТ ДҮН</c></b>']
        row += ['<b>%s</b>' % total_dict['qty'], '',
                '<b>%s</b>' % total_dict['total_cost'], ]
        data.append(row)
        if res:
            # Санхүүгийн данс
            for val in sorted(res.values(), key=itemgetter('name')):
                row = [u'<color><b><right> Данс: </right></b></color>',
                       u'<color><b><right>[%s]</right></b></color>' % val['account_code'],
                       u'<color><b>%s</b></color>' % val['name'], None, None, None,None,None,
                       '<color><b>%s</b></color>' % val['total_cost']]
                data.append(row)
                number = 1
                # Дотоод зарлагын баримт
                for con in sorted(val['lines'].values(), key=itemgetter('name')):
                    row = [u'<c><str>%s</str></c>' % str(number), u'<b><c>%s</c></b>' % con['date'],
                           u'<b><c>%s</c></b>' % con['name'],
                           u'<b><c>%s</c></b>' % con['picking_name'],
                           u'<b><c>%s</c></b>' % con['analytic_account'],
                           u'<b><c>%s</c></b>' % con['partner'],
                           '<b>%s</b>' % con['qty'], '',
                           '<b>%s</b>' % con['total_cost']]
                    data.append(row)
                    seq = 1
                    # Агуулахын хөдөлгөөн
                    for prod in sorted(con['lines'].values(), key=itemgetter('name')):
                        num = str(number) + '.' + str(seq)
                        row = [u'<c><str>%s</str></c>' % str(num), '', '', '', '',
                               u'%s' % prod['name'], prod['qty'],
                               prod['cost_price'], prod['total_cost']]
                        seq += 1
                        data.append(row)
                    number += 1
        return data, titles
    
