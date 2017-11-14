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

class report_income_ledger(osv.osv_memory):
    _name = 'report.income.ledger'
    _inherit = 'abstract.report.model'
    _description = 'Report Income Ledger'
    
    def _get_pos_install(self, cr, uid, context=None):
        '''
            Пос борлуулалт модуль суусан эсэхийг шалгана.
        '''
        pos_obj = self.pool.get('pos.order')
        if pos_obj:
            return True
        return False
    
    def _get_mrp_install(self, cr, uid, context=None):
        '''
            Үйлдвэрлэлийн модуль суусан эсэхийг шалгана.
        '''
        mrp_obj = self.pool.get('mrp.production')
        if mrp_obj:
            return True
        return False
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_income_ledger_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'product_ids':  fields.many2many('product.product', 'report_income_ledger_product_rel',
                            'wizard_id', 'product_id', 'Product'),
        'partner_ids':  fields.many2many('res.partner', 'report_income_ledger_partner_rel',
                            'wizard_id', 'partner_id', 'Partner'),
        'category_ids': fields.many2many('product.category', 'report_income_ledger_category_rel',
                            'wizard_id', 'category_id', 'Category'),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
        'purchase':     fields.boolean('Purchase'),
        'refund':       fields.boolean('Refund'),
        'procure':      fields.boolean('Replenishment'),
        'pos':          fields.boolean('Pos Refund'),
        'swap':         fields.boolean('Swap'),
        'inventory':    fields.boolean('Inventory'),
        'mrp':          fields.boolean('MRP Production'),
        'type':         fields.selection([('detail','Detail'),('summary','Summary')], 'Type', required=True),
        'cost':         fields.boolean('Show Cost Amount?'),
        'pos_install':  fields.boolean('Pos Install'),
        'mrp_install':  fields.boolean('MRP Install')
        
    }
    
    def _get_warehouse(self, cr, uid, context=None):
        '''
            Боломжит агуулахуудыг олж тодорхойлно.
        '''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wids = (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
        if len(wids) > 1:
            return []
        return wids
    
    _defaults = {
        'company_id': lambda obj,cr,uid,c:obj.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory.report'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'mrp_install': _get_mrp_install,
        'pos_install': _get_pos_install,
        'purchase': True,
        'refund': True,
        'procure': True,
        'pos': True,
        'mrp': True,
        'swap': True,
        'inventory': True,
        'type': 'summary',
        'cost': False,
        'warehouse_ids': _get_warehouse
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        wnames = ''
        for w in form.warehouse_ids:
            wnames += w.name
            wnames += ','
        body = (u"Орлогын товчоо тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
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
        if not wiz['warehouse_ids']:
            wiz['warehouse_ids'] = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
        data, titles = self.mirror_prepare_report_data(cr, uid, wiz, self._name, context=context)
        widths = [2,4,6,6,8]
        headers = [
            [u'Д/д',u'Огноо',u'Баримтын дугаар',u'Эх баримт',u'Харилцагчийн нэр']
        ]
        headers[0] += [u'Тоо хэмжээ',u'Нийт дүн',u'НӨТ',u'НӨТ-гүй дүн']
        widths += [4,4,3,4]
        if wiz['cost']:
            headers[0] += [u'Өртөг дүн']
            widths += [4]
        datas = {
            'title': u'Орлогын товчоо тайлан',
            'headers': headers,
            'header_span': [],
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas':datas}
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        wnames = ''
        TAX_FACTOR = self.pool.get("ir.config_parameter").get_param(cr, uid, 'report.tax') or 0
        location_ids = []
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        for w in warehouses:
            wnames += w.name
            wnames += ','
            location_ids.extend(location_obj.search(cr, uid, 
                                            [('location_id','child_of',[w.view_location_id.id]),
                                             ('usage','=','internal')], context=context))
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'],wiz['date_to']),
                  u'Салбар: %s'%(wnames)]
        data = []
        pick_ids = []
        res = {}
        where = ''
        join = ''
        select_type = ''
        location_tuple = tuple(location_ids)
        any_check = False
        total_dict = {'total': 0,
                      'qty': 0,
                      'taxed': 0,
                      'tax': 0,
                      'cost':0}
        select = ' (select 0) AS tax, '
        select_name = ' p.name AS name, '
        select_origin = ' p.origin AS origin, '
        group_by = ''
        if wiz['product_ids']:
            where += ' AND m.product_id IN ('+','.join(map(str,wiz['product_ids']))+') '
        if wiz['partner_ids']:
            where += ' AND p.partner_id IN ('+','.join(map(str,wiz['partner_ids']))+') '
        if wiz['category_ids']:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',wiz['category_ids'])])
            where += ' AND pt.categ_id IN ('+','.join(map(str,categ_ids))+') '
        if wiz['mrp'] and wiz['mrp_install']:
            any_check = True
            join += ' LEFT JOIN mrp_production AS mrp ON (m.production_id = mrp.id) '
            select_type += " WHEN m.production_id is not null THEN 'mrp' "
            select_name = '(CASE WHEN m.picking_id is not null THEN p.name \
                            WHEN m.production_id is not null THEN mrp.name END) AS name,'
            group_by += 'm.production_id,mrp.name,'
        if wiz['purchase']:
            any_check = True
            join += ' LEFT JOIN purchase_order_line AS pol ON (m.purchase_line_id = pol.id) \
                        LEFT JOIN purchase_order_taxe AS taxes ON (pol.id = taxes.ord_id) '
            select += ' SUM(taxes.tax_id) AS tax, '
        if wiz['refund']:
            any_check = True
        if wiz['pos'] and wiz['pos_install']:
            any_check = True
        if wiz['procure']:
            any_check = True
        if wiz['inventory']:
            any_check = True
            join += ' LEFT JOIN stock_inventory AS i ON (m.inventory_id = i.id) '
            if wiz['mrp'] and wiz['mrp_install']:
                select_name = '(CASE WHEN m.picking_id is not null THEN p.name \
                                WHEN m.production_id is not null THEN mrp.name \
                                WHEN m.inventory_id is not null THEN i.name END) AS name,'
                select_origin = '(CASE WHEN m.picking_id is not null THEN p.origin \
                                    WHEN m.production_id is not null THEN mrp.name \
                                    WHEN m.inventory_id is not null THEN i.name END) AS origin, '
            else:
                select_name = '(CASE WHEN m.picking_id is not null THEN p.name \
                                WHEN m.inventory_id is not null THEN i.name END) AS name,'
                select_origin = '(CASE WHEN m.picking_id is not null THEN p.origin \
                                    WHEN m.inventory_id is not null THEN i.name END) AS origin, '
            group_by += 'i.name,'
        if wiz['swap']:
            any_check = True
            join += ' LEFT JOIN swap_order_line AS swl ON (m.swap_line_id = swl.id) \
                      LEFT JOIN swap_order AS swo ON (swl.order_id = swo.id) \
                      LEFT JOIN swap_order_in_tax_rel AS stax ON (swo.id = stax.ord_id) '
            select += ' SUM(stax.tax_id) AS stax, '
        if any_check:
            prod_ids = []
            name_dict = {}
            cr.execute("SELECT cast(m.date as date) AS date, m.id AS move_id, m.origin_returned_move_id AS return_id, "
                            "(CASE WHEN m.picking_id is not null THEN rp.name WHEN m.warehouse_id is not null "
                                "AND sw.partner_id is not null THEN rp2.name ELSE '' END) AS partner, "
                            "(CASE WHEN m.purchase_line_id is not null THEN 'purchase' "
                                "WHEN m.inventory_id is not null THEN 'inventory' "
                                "WHEN m.picking_id is not null and p.transit_order_id is not null THEN 'procure' "
                                "WHEN m.swap_line_id is not null THEN 'swap' "+select_type+" "
                                "WHEN m.origin_returned_move_id is not null THEN 'refund' ELSE 'pos' END) AS rep_type, "+select_name+" "
                            "m.product_id AS prod_id, "+select_origin+" "
                            "SUM(coalesce((m.product_qty / u.factor * u2.factor),0)) AS qty, "+select+" "
                            "SUM(coalesce((m.price_unit * m.product_qty / u.factor * u2.factor),0)) AS cost, "
                            "SUM(coalesce((m.list_price * m.product_qty / u.factor * u2.factor),0)) AS amount "
                        "FROM stock_move AS m "
                            "LEFT JOIN stock_picking AS p ON (m.picking_id = p.id) "
                            "LEFT JOIN res_partner AS rp ON (p.partner_id = rp.id) "
                            "JOIN product_product AS pp ON (m.product_id = pp.id) "
                            "JOIN product_template AS pt ON (pp.product_tmpl_id = pt.id) "
                            "JOIN product_uom AS u ON (m.product_uom = u.id) "
                            "JOIN product_uom AS u2 ON (pt.uom_id = u2.id) "
                            "LEFT JOIN stock_warehouse AS sw ON (m.warehouse_id = sw.id) "
                            "LEFT JOIN res_partner AS rp2 ON (sw.partner_id = rp2.id) "
                            "LEFT JOIN procurement_order AS po ON (m.procurement_id = po.id) "+join+""
                        "WHERE m.location_id NOT IN %s AND m.location_dest_id IN %s "
                            "AND m.state = 'done' "
                            "AND m.date >= %s AND m.date <= %s "+where+" "
                        "GROUP BY m.id,m.date,m.origin_returned_move_id,m.picking_id,rp.name,m.warehouse_id,sw.partner_id,m.purchase_line_id, "+group_by+" "
                            "rp2.name,m.inventory_id,m.swap_line_id,p.name,m.product_id,p.origin,p.transit_order_id "
                        "ORDER BY m.date "
                            ,(location_tuple,location_tuple,wiz['date_from'],wiz['date_to']+' 23:59:59'))
            result = cr.dictfetchall()
            if wiz['type'] == 'detail':
                for r in result:
                    if r['prod_id'] not in prod_ids:
                        prod_ids.append(r['prod_id'])
                if prod_ids:
                    name_dict  = dict( product_obj.name_get(cr, uid, prod_ids, context=context) )
            for r in result:
                tax = taxed = 0
                if r['rep_type'] == 'mrp' and ((not wiz['mrp_install']) or \
                                               (wiz['mrp_install'] and not wiz['mrp'])):
                    continue
                if r['rep_type'] == 'pos' and ((not wiz['pos_install']) or \
                                               (wiz['pos_install'] and not wiz['pos'])):
                    continue
                if r['rep_type'] == 'procure' and not wiz['procure']:
                    continue
                if r['rep_type'] == 'refund' and not wiz['refund']:
                    continue
                if r['rep_type'] == 'inventory' and not wiz['inventory']:
                    continue
                if r['rep_type'] == 'swap' and not wiz['swap']:
                    continue
                if r['rep_type'] == 'purchase' and not wiz['purchase']:
                    continue
                if r['rep_type'] in ('purchase','swap','pos'):
                    if r['rep_type'] == 'pos':
                        taxed = round(float(r['amount'])/float(1+float(TAX_FACTOR)),4)
                        tax = r['amount'] - taxed
                    elif r['rep_type'] == 'swap':
                        if r['stax'] > 0:
                            taxed = round(float(r['amount'])/float(1+float(TAX_FACTOR)),4)
                            tax = r['amount'] - taxed
                    else:
                        if r['tax'] > 0:
                            taxed = round(float(r['amount'])/float(1+float(TAX_FACTOR)),4)
                            tax = r['amount'] - taxed
                if r['rep_type'] not in res:
                    res[r['rep_type']] = {'name': r['rep_type'],
                                          'lines': {},
                                          'total': 0,
                                          'qty': 0,
                                          'taxed': 0,
                                          'tax': 0,
                                          'cost':0}
                res[r['rep_type']]['qty'] += r['qty']
                res[r['rep_type']]['total'] += r['amount']
                res[r['rep_type']]['cost'] += r['cost']
                res[r['rep_type']]['tax'] += tax
                res[r['rep_type']]['taxed'] += taxed
                if r['name'] not in res[r['rep_type']]['lines']:
                    res[r['rep_type']]['lines'][r['name']] = {'date': r['date'],
                                                              'name': r['name'] or '',
                                                              'origin': r['origin'] or '',
                                                              'partner': r['partner'] or '',
                                                              'total': 0,
                                                              'qty': 0,
                                                              'taxed': 0,
                                                              'tax': 0,
                                                              'cost':0,
                                                              'lines':{}}
                res[r['rep_type']]['lines'][r['name']]['qty'] += r['qty']
                res[r['rep_type']]['lines'][r['name']]['total'] += r['amount']
                res[r['rep_type']]['lines'][r['name']]['cost'] += r['cost']
                res[r['rep_type']]['lines'][r['name']]['tax'] += tax
                res[r['rep_type']]['lines'][r['name']]['taxed'] += taxed
                if wiz['type'] == 'detail':
                    if r['prod_id'] not in res[r['rep_type']]['lines'][r['name']]['lines']:
                        res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']] = {'date': '',
                                                                                         'name': name_dict.get(r['prod_id'],''),
                                                                                         'origin': '',
                                                                                         'partner': '',
                                                                                         'total': 0,
                                                                                         'qty': 0,
                                                                                         'taxed': 0,
                                                                                         'tax': 0,
                                                                                         'cost':0}
                    res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']]['qty'] += r['qty']
                    res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']]['total'] += r['amount']
                    res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']]['cost'] += r['cost']
                    res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']]['tax'] += tax
                    res[r['rep_type']]['lines'][r['name']]['lines'][r['prod_id']]['taxed'] += taxed
                total_dict['qty'] += r['qty']
                total_dict['cost'] += r['cost']
                total_dict['tax'] += tax
                total_dict['taxed'] += taxed
                total_dict['total'] += r['amount']
        row = ['','','','', u'<b><c>НИЙТ ДҮН</c></b>']
        row += ['<b>%s</b>' % total_dict['qty'],'<b>%s</b>' % total_dict['total'],
                '<b>%s</b>' % total_dict['tax'],'<b>%s</b>' % total_dict['taxed']]
        if wiz['cost']:
            row += ['<b>%s</b>' % total_dict['cost']]
        data.append(row)
        if res:
            number = 1
            for val in sorted(res.values(), key=itemgetter('name')):
                name = val['name']
                if val['name'] == 'procure':
                    name = u'Нөхөн дүүргэлт'
                elif val['name'] == 'pos':
                    name = u'Посын буцаалт'
                elif val['name'] == 'purchase':
                    name = u'Худалдан авалт'
                elif val['name'] == 'mrp':
                    name = u'Үйлдвэрлэл'
                elif val['name'] == 'swap':
                    name = u'Солилцоо'
                elif val['name'] == 'refund':
                    name = u'Буцаалт'
                elif val['name'] == 'inventory':
                    name = u'Тооллого'
                row = ['','','','',u'<b><c>%s</c></b>'%name]
                row += ['<b>%s</b>' % val['qty'],'<b>%s</b>' % val['total'],
                        '<b>%s</b>' % val['tax'],'<b>%s</b>' % val['taxed']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % val['cost']]
                data.append(row)
                for v in sorted(val['lines'].values(), key=itemgetter('date')):
                    if wiz['type'] == 'detail':
                        row = ['<c><str>%s</str></c>'%str(number),'<b><c>%s</c></b>'%v['date'],
                               '<b>%s</b>'%v['name'],'<b>%s</b>'%v['origin'],
                               u'<b>%s</b>'%v['partner'],'<b>%s</b>'%v['qty']]
                        row += ['<b>%s</b>'%v['total'],'<b>%s</b>'%v['tax'],'<b>%s</b>'%v['taxed']]
                        if wiz['cost']:
                            row += ['<b>%s</b>'%v['cost']]
                    else:
                        row = ['<c><str>%s</str></c>'%str(number),'<c>%s</c>'%v['date'],
                               '%s'%v['name'],'%s'%v['origin'],
                               u'%s'%v['partner']]
                        row += [v['qty'],v['total'],v['tax'],v['taxed']]
                        if wiz['cost']:
                            row += [v['cost']]
                    number += 1
                    data.append(row)
                    if wiz['type'] == 'detail':
                        for p in sorted(v['lines'].values(), key=itemgetter('name')):
                            row = ['','','','',u'%s'%p['name'],
                                   p['qty'],p['total'],p['tax'],p['taxed']]
                            if wiz['cost']:
                                row += [p['cost']]
                            data.append(row)
        return data, titles
