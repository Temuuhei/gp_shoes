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

class report_refund_ledger(osv.osv_memory):
    _name = 'report.refund.ledger'
    _inherit = 'abstract.report.model'
    _description = 'Report Refund Ledger'
    
    def get_group_by(self, cr, uid, context=None):
        res = [('section',_('Sales Team')),
               ('partner',_('Partner')),
               ('category',_('Category')),
               ('order',_('Order')),
               ('manufacture',_('Manufacturer')),
               ('type',_('Return Type'))]
        pos_obj = self.pool.get('pos.category')
        if pos_obj:
            res += [('pos_categ',_('Pos Category'))]
        return res
    def _get_pos_install(self, cr, uid, context=None):
        '''
            Посын модуль суусан эсэхийг шалгана.
        '''
        pos_obj = self.pool.get('pos.order')
        if pos_obj:
            return True
        return False
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_refund_ledger_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'product_ids':  fields.many2many('product.product', 'report_refund_ledger_product_rel',
                            'wizard_id', 'product_id', 'Product'),
        'category_ids': fields.many2many('product.category', 'report_refund_ledger_category_rel',
                            'wizard_id', 'category_id', 'Category'),
        'partner_ids':  fields.many2many('res.partner', 'report_refund_ledger_partner_rel', 
                            'wizard_id', 'partner_id', 'Partner'),
        'manufacturer_ids':  fields.many2many('res.partner', 'report_refund_ledger_manufacturer_rel', 
                            'wizard_id', 'manufacturer_id', 'Manufacturer'),
        'return_type_ids':fields.many2many('stock.return.type', 'report_refund_ledger_type_rel',
                            'wizard_id', 'type_id', 'Return Type'),
        'team_ids':     fields.many2many('crm.case.section', 'report_refund_ledger_team_rel',
                                         'wizard_id', 'team_id', 'Sales Team'),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
        'grouping':     fields.selection(get_group_by, 'Grouping'),
        'report_type':  fields.selection([('sales','Sales'),('purchase','Purchase')], 'Report Type', required=True),
        'type':         fields.selection([('detail','Detail'),('summary','Summary')], 'Type', required=True),
        'pos_install':  fields.boolean('Pos Install'),
        'cost':         fields.boolean('Show Cost Amount?'),
        'ean':          fields.boolean('Show Barcode'),
        
    }
    
    def _get_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wids = (user.allowed_warehouses and map(lambda x:x.id, user.allowed_warehouses)) or []
        if len(wids) > 1:
            return []
        return wids
    
    def _get_team(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return ([user.default_section_id and user.default_section_id.id]) or []
    
    _defaults = {
        'company_id': lambda obj,cr,uid,c:obj.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory.report'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'report_type': 'sales',
        'type': 'detail',
        'cost': False,
        'ean': True,
        'pos_install': _get_pos_install,
        'warehouse_ids': _get_warehouse,
        'team_ids': _get_team,
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        wnames = ''
        for w in form.warehouse_ids:
            wnames += w.name
            wnames += ','
        body = (u"Буцаалтын товчоо тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
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
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        data, titles = self.mirror_prepare_report_data(cr, uid, wiz, self._name, context=context)
        widths = [2,10]
        headers = [
            [u'Д/д',u'Бараа материал'],
            [None,None]
        ]
        header_span = [((0,0),(0,1)), ((1,0),(1,1))]
        colx = 2
        if wiz['ean'] and ((wiz['grouping'] and wiz['type']=='detail') or not wiz['grouping']):
            headers[0] += [u'Бар код']
            headers[1] += [None]
            header_span += [((colx,0),(colx,1))]
            widths += [4]
            colx += 1
        if wiz['grouping'] == 'order':
            headers[0] += [u'Эх баримт']
            headers[1] += [None]
            header_span += [((colx,0),(colx,1))]
            widths += [4]
            colx += 1
        if len(warehouses) > 1:
            """Буцаалт"""
            headers[0] += [u'НИЙТ',None,None,None]
            headers[1] += [u'Тоо ширхэг',u'Худалдах үнийн дүн',u'Үнийн дүн',u'Хөнгөлөлт',u'Цэвэр дүн']
            widths += [3,4,4,4,4]
            rcolx = colx
            colx += 5
            if wiz['cost']:
                headers[0] += [None]
                headers[1] += [u'Өртөг дүн']
                widths += [4]
                colx += 1
            header_span += [((rcolx,0),(colx-1,0))]
        for wh in warehouses:
            """Буцаалт"""
            headers[0] += [wh.name,None,None,None]
            headers[1] += [u'Тоо ширхэг',u'Худалдах үнийн дүн', u'Үнийн дүн',u'Хөнгөлөлт',u'Цэвэр дүн']
            widths += [3,4,4,4,4]
            rcolx = colx
            colx += 5
            if wiz['cost']:
                headers[0] += [None]
                headers[1] += [u'Өртөг дүн']
                widths += [4]
                colx += 1
            header_span += [((rcolx,0),(colx-1,0))]
        datas = {
            'title': u'Буцаалтын товчоо тайлан',
            'headers': headers,
            'header_span': header_span,
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas':datas}
    
    def get_query(self, cr, uid, wiz, context=None):
        # Борлуулалтын буцаалт
        where = ""
        select = ""
        join = ""
        groupby = ""
        locations = tuple(wiz['locations'])
        if wiz['category_ids']:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',wiz['category_ids'])], context=context)
            where += " AND pt.categ_id in ("+','.join(map(str,categ_ids))+") "
        if wiz['product_ids']:
            where += " AND pp.id in ("+','.join(map(str,wiz['product_ids']))+") "
        if wiz['manufacturer_ids']:
            where += " AND pt.manufacturer in ("+','.join(map(str,wiz['manufacturer_ids']))+") "
        if wiz['partner_ids']:
            where += " AND m.partner_id in ("+','.join(map(str,wiz['partner_ids']))+") "
        if wiz['return_type_ids']:
            where += " AND p.stock_return_type_id in ("+','.join(map(str,wiz['return_type_ids']))+") "
        if wiz['team_ids']:
            where += " AND s.section_id IN ("+','.join(map(str,wiz['team_ids']))+") "
        if wiz['grouping'] == 'manufacture':
            select = "rp.id AS group_id,rp.name AS gname, "
            join =" LEFT JOIN res_partner rp ON pt.manufacturer = rp.id "
            groupby = ",rp.id,rp.name "
        if wiz['grouping'] == 'partner':
            select = "rp.id AS group_id,rp.name AS gname, "
            join =" LEFT JOIN res_partner rp ON m.partner_id = rp.id "
            groupby = ",rp.id,rp.name "
        if wiz['grouping'] == 'section':
            select = "rp.id AS group_id,rp.name AS gname, "
            join =" LEFT JOIN crm_case_section rp ON s.section_id = rp.id "
            groupby = ",rp.id,rp.name "
        if wiz['grouping'] == 'category':
            select = "pc.id AS group_id,pc.name AS gname, "
            join =" LEFT JOIN product_category pc ON pt.categ_id = pc.id "
            groupby = ",pc.id,pc.name "
        if wiz['grouping'] == 'pos_categ':
            select = "pos.id AS group_id,pos.name AS gname, "
            join =" LEFT JOIN pos_category pos ON pt.pos_categ_id = pos.id "
            groupby = ",pos.id,pos.name "
        if wiz['grouping'] == 'type':
            select = "srt.id AS group_id,srt.name AS gname, "
            join =" LEFT JOIN stock_return_type srt ON p.stock_return_type_id = srt.id "
            groupby = ",srt.id,srt.name "
        if wiz['grouping'] == 'order':
            select = "p.id AS group_id,p.name AS gname, p.origin, "
            groupby = ",p.id,p.name,p.origin "
        cr.execute("SELECT m.product_id AS prod, "+select+" "
                        "coalesce(SUM(m.product_qty/u.factor*u2.factor),0) AS q, "
                        "coalesce(SUM(l.price_unit*m.product_qty/u.factor*u2.factor),0) AS s, "
                        "coalesce(SUM(m.list_price*m.product_qty/u.factor*u2.factor),0) AS l, "
                        "coalesce(SUM(m.product_qty * l.price_unit * (l.discount / 100)/u.factor*u2.factor),0) AS d, "
                        "coalesce(SUM(m.price_unit*m.product_qty),0) AS c "
                    "FROM stock_picking p "
                        "JOIN stock_move m ON p.id=m.picking_id "
                        "JOIN product_product pp ON m.product_id=pp.id "
                        "JOIN product_template pt ON pp.product_tmpl_id=pt.id "
                        "JOIN product_uom u ON (u.id=m.product_uom) "
                        "JOIN product_uom u2 ON (u2.id=pt.uom_id) "
                        "JOIN procurement_order o ON (o.id=m.procurement_id) "
                        "JOIN sale_order_line l ON (o.sale_line_id=l.id) "
                        "JOIN sale_order s ON (l.order_id=s.id) "+join+
                   "WHERE m.state = 'done' "+where+" "
                        "AND m.location_id NOT IN %s AND m.location_dest_id IN %s "
                        "AND m.date >= %s AND m.date <= %s "
                    "GROUP BY m.product_id"+groupby,
                    (locations,locations,wiz['date_from']+' 00:00:00',wiz['date_to']+' 23:59:59'))
        fetched = cr.dictfetchall()
        
        return fetched
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        location_obj = self.pool.get('stock.location')
        wnames = ''
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        for w in warehouses:
            wnames += w.name
            wnames += ','
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'],wiz['date_to']),
                  u'Салбар: %s'%(wnames)]
        if wiz['team_ids']:
            teams = self.pool.get('crm.case.section').browse(cr, uid, wiz['team_ids'], context=context)
            for tm in teams:
                titles += [u'Борлуулалтын баг : %s,'%tm.name]
        data = []
        total_dict = {'qty': 0, 'amt': 0.0,'cost': 0, 'dis': 0.0, 'list':0.0,'whs': {}}
        data_dict = {}
        prod_ids = []
        for wh in warehouses:
            locations = location_obj.search(cr, uid, [('usage','=','internal'),
                                                      ('location_id','child_of',[wh.view_location_id.id])], context=context)
            wiz['locations'] = locations
            if wh.id not in total_dict['whs']:
                total_dict['whs'][wh.id] = {'qty': 0, 'amt': 0.0,'list': 0.0,
                                            'cost': 0, 'dis': 0.0}
            fetched = self.get_query(cr, uid, wiz, context=context)
            for f in fetched:
                origin = ''
                if wiz['grouping'] == 'order':
                    origin = f['origin'] or ''
                if f['prod'] not in prod_ids:
                    prod_ids.append(f['prod'])
                if wiz['grouping']:
                    if f['group_id'] not in data_dict:
                        data_dict[f['group_id']] = {'name': f['gname'] or u'Тодорхойгүй',
                                                    'origin': origin,
                                                    'qty': 0, 'amt': 0.0,'list': 0.0,
                                                    'cost': 0, 'dis': 0.0,
                                                    'lines': {},'whs': {}}
                    if wh.id not in data_dict[f['group_id']]['whs']:
                        data_dict[f['group_id']]['whs'][wh.id] = {'qty': 0, 'amt': 0.0,'list': 0.0,
                                                                  'cost': 0, 'dis': 0.0}
                    if f['prod'] not in data_dict[f['group_id']]['lines']:
                        data_dict[f['group_id']]['lines'][f['prod']] = {'qty': 0, 'amt': 0.0,
                                                                        'cost': 0, 'dis': 0.0,
                                                                        'list':0.0,'whs': {}}
                    if wh.id not in data_dict[f['group_id']]['lines'][f['prod']]['whs']:
                        data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id] = {'qty': 0, 'amt': 0.0,'list':0.0,
                                                                                      'cost': 0, 'dis': 0.0}
                    data_dict[f['group_id']]['qty'] += f['q']
                    data_dict[f['group_id']]['dis'] += f['d']
                    data_dict[f['group_id']]['cost'] += f['c']
                    data_dict[f['group_id']]['amt'] += f['s']
                    data_dict[f['group_id']]['list'] += f['l']
                    data_dict[f['group_id']]['whs'][wh.id]['qty'] += f['q']
                    data_dict[f['group_id']]['whs'][wh.id]['dis'] += f['d']
                    data_dict[f['group_id']]['whs'][wh.id]['cost'] += f['c']
                    data_dict[f['group_id']]['whs'][wh.id]['amt'] += f['s']
                    data_dict[f['group_id']]['whs'][wh.id]['list'] += f['l']
                    data_dict[f['group_id']]['lines'][f['prod']]['qty'] += f['q']
                    data_dict[f['group_id']]['lines'][f['prod']]['dis'] += f['d']
                    data_dict[f['group_id']]['lines'][f['prod']]['cost'] += f['c']
                    data_dict[f['group_id']]['lines'][f['prod']]['amt'] += f['s']
                    data_dict[f['group_id']]['lines'][f['prod']]['list'] += f['l']
                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['qty'] += f['q']
                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['dis'] += f['d']
                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['cost'] += f['c']
                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['amt'] += f['s']
                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['list'] += f['l']
                else:
                    if f['prod'] not in data_dict:
                        data_dict[f['prod']] = {'qty': 0, 'amt': 0.0,
                                                'cost': 0, 'dis': 0.0,
                                                'list': 0.0,'whs': {}}
                    if wh.id not in data_dict[f['prod']]['whs']:
                        data_dict[f['prod']]['whs'][wh.id] = {'qty': 0, 'amt': 0.0,'list':0.0,
                                                              'cost': 0, 'dis': 0.0}
                    data_dict[f['prod']]['qty'] += f['q']
                    data_dict[f['prod']]['dis'] += f['d']
                    data_dict[f['prod']]['cost'] += f['c']
                    data_dict[f['prod']]['amt'] += f['s']
                    data_dict[f['prod']]['list'] += f['l']
                    data_dict[f['prod']]['whs'][wh.id]['qty'] += f['q']
                    data_dict[f['prod']]['whs'][wh.id]['dis'] += f['d']
                    data_dict[f['prod']]['whs'][wh.id]['cost'] += f['c']
                    data_dict[f['prod']]['whs'][wh.id]['amt'] += f['s']
                    data_dict[f['prod']]['whs'][wh.id]['list'] += f['l']
                total_dict['qty'] += f['q']
                total_dict['dis'] += f['d']
                total_dict['cost'] += f['c']
                total_dict['amt'] += f['s']
                total_dict['list'] += f['l']
                total_dict['whs'][wh.id]['qty'] += f['q']
                total_dict['whs'][wh.id]['dis'] += f['d']
                total_dict['whs'][wh.id]['cost'] += f['c']
                total_dict['whs'][wh.id]['amt'] += f['s']
                total_dict['whs'][wh.id]['list'] += f['l']
                
                    
        number = 1
        prods = dict([(x['id'], x) for x in product_obj.read(cr, uid, prod_ids, 
                                    ['ean13','name','default_code'], context=context)])
        row = ['']
        row += [u'<b><c>НИЙТ</c></b>']
        if wiz['ean'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
            row += ['']
        if wiz['grouping'] == 'order':
            row += ['']
        if len(warehouses) > 1:
            row += ['<b>%s</b>'%total_dict['qty'],'<b>%s</b>'%total_dict['list'],'<b>%s</b>'%total_dict['amt'],
                    '<b>%s</b>'%total_dict['dis'],'<b>%s</b>'%(total_dict['amt']-total_dict['dis'])]
            if wiz['cost']:
                row +=['<b>%s</b>'%total_dict['cost']]
        for wh in warehouses:
            if wh.id in total_dict['whs']:
                row += ['<b>%s</b>'%total_dict['whs'][wh.id]['qty'],'<b>%s</b>'%total_dict['whs'][wh.id]['list'],
                        '<b>%s</b>'%total_dict['whs'][wh.id]['amt'],'<b>%s</b>'%total_dict['whs'][wh.id]['dis'],
                        '<b>%s</b>'%(total_dict['whs'][wh.id]['amt']-total_dict['whs'][wh.id]['dis'])]
                if wiz['cost']:
                    row +=['<b>%s</b>'%total_dict['whs'][wh.id]['cost']]
            else:
                row += ['<b>0.0</b>','<b>0.0</b>','<b>0.0</b>','<b>0.0</b>','<b>0.0</b>']
                if wiz['cost']:
                    row += ['<b>0.0</b>']
        data.append( row )
        rowx = 1
        if data_dict:
            if wiz['grouping']:
                for val in sorted(data_dict.values(), key=itemgetter('name')):
                    count = 1
                    row = ['<str>%s</str>' % number]
                    if wiz['type'] == 'detail':
                        row += [u'<b>%s</b>'%(val['name'])]
                        if wiz['ean']:
                            row += ['']
                    else:
                        row += [u'%s'%(val['name'])]
                    if wiz['grouping'] == 'order':
                        row += [u'%s'%(val['origin'])]
                    if len(warehouses) > 1:
                        row += ['<b>%s</b>'%val['qty'],'<b>%s</b>'%val['list'],'<b>%s</b>'%val['amt'],
                                '<b>%s</b>'%val['dis'],'<b>%s</b>'%(val['amt']-val['dis'])]
                        if wiz['cost']:
                            row +=['<b>%s</b>'%val['cost']]
                    for wh in warehouses:
                        if wh.id in val['whs']:
                            if wiz['type'] == 'detail':
                                row += ['<b>%s</b>'%val['whs'][wh.id]['qty'],
                                        '<b>%s</b>'%val['whs'][wh.id]['list'],
                                        '<b>%s</b>'%val['whs'][wh.id]['amt'],
                                        '<b>%s</b>'%val['whs'][wh.id]['dis'],
                                        '<b>%s</b>'%(val['whs'][wh.id]['amt']-val['whs'][wh.id]['dis'])]
                                if wiz['cost']:
                                    row +=['<b>%s</b>'%val['whs'][wh.id]['cost']]
                            else:
                                row += [val['whs'][wh.id]['qty'],
                                        val['whs'][wh.id]['list'],
                                        val['whs'][wh.id]['amt'],
                                        val['whs'][wh.id]['dis'],
                                        (val['whs'][wh.id]['amt']-val['whs'][wh.id]['dis'])]
                                if wiz['cost']:
                                    row +=[val['whs'][wh.id]['cost']]
                        else:
                            if wiz['type'] == 'detail':
                                row += ['<b>0.0</b>','<b>0.0</b>','<b>0.0</b>','<b>0.0</b>','<b>0.0</b>']
                                if wiz['cost']:
                                    row += ['<b>0.0</b>']
                            else:
                                row += [0.0,0.0,0.0,0.0,0.0]
                                if wiz['cost']:
                                    row += [0.0]
                    data.append( row )
                    rowx += 1
                    if wiz['type'] == 'detail':
                        for prod in sorted(prods.values(), key=itemgetter('name')):
                            if prod['id'] in val['lines']:
                                row = ['<str>%s.%s</str>' % (number,count)]
                                
                                row += [u'<space/><space/>[%s] %s'%((prod['default_code'] or ''),(prod['name'] or ''))]
                                if wiz['ean']:
                                    row += [u'<str>%s</str>'%(prod['ean13'] or '')]
                                if wiz['grouping'] == 'order':
                                    row += ['']
                            
                                line = val['lines'][prod['id']]
                                if len(warehouses) > 1:
                                    row += [line['qty'],line['list'],line['amt'],
                                            line['dis'],(line['amt']-line['dis'])]
                                    if wiz['cost']:
                                        row += [line['cost']]
                                for wh in warehouses:
                                    if wh.id in line['whs']:
                                        row += [line['whs'][wh.id]['qty'],line['whs'][wh.id]['list'],
                                                line['whs'][wh.id]['amt'],line['whs'][wh.id]['dis'],
                                                (line['whs'][wh.id]['amt']-line['whs'][wh.id]['dis'])]
                                        if wiz['cost']:
                                            row += [line['whs'][wh.id]['cost']]
                                    else:
                                        row += [0.0,0.0,0.0,0.0,0.0]
                                        if wiz['cost']:
                                            row += [0.0]
                                count += 1
                                data.append(row)
                    number += 1
            else:
                for prod in sorted(prods.values(), key=itemgetter('name')):
                    if prod['id'] in data_dict:
                        row = ['<str>%s</str>' % (number)]
                        row += [u'<space/><space/>[%s] %s'%((prod['default_code'] or ''),(prod['name'] or ''))]
                        if wiz['ean']:
                            row += [u'<str>%s</str>'%(prod['ean13'] or '')]
                    
                        line = data_dict[prod['id']]
                        if len(warehouses) > 1:
                            row += [line['qty'],line['list'],
                                    line['amt'],line['dis'],
                                    (line['amt']-line['dis'])]
                            if wiz['cost']:
                                row += [line['cost']]
                        for wh in warehouses:
                            if wh.id in line['whs']:
                                row += [line['whs'][wh.id]['qty'],line['whs'][wh.id]['list'],
                                        line['whs'][wh.id]['amt'],line['whs'][wh.id]['dis'],
                                        (line['whs'][wh.id]['amt']-line['whs'][wh.id]['dis'])]
                                if wiz['cost']:
                                    row += [line['whs'][wh.id]['cost']]
                            else:
                                row += [0.0,0.0,0.0,0.0,0.0]
                                if wiz['cost']:
                                    row += [0.0]
                        number += 1
                        data.append( row )
        return data, titles
