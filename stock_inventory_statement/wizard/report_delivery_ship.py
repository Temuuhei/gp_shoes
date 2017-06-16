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

class report_delivery_ship(osv.osv_memory):
    _name = 'report.delivery.ship'
    _inherit = 'abstract.report.model'
    _description = 'Report Delivery'
    
    GROUP_BY = [('car','Car'),
                ('employee','Driver'),
                ('team','Sales team')]
    
    _columns = {
        'company_id':   fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'report_delivery_ship_warehouse_rel',
                            'wizard_id', 'warehouse_id', 'Warehouse'),
        'partner_ids':  fields.many2many('res.partner', 'report_delivery_ship_partner_rel', 
                            'wizard_id', 'partner_id', 'Partner'),
        'car_ids':      fields.many2many('stock.car.news', 'report_delivery_ship_car_rel',
                            'wizard_id', 'car_id', 'Cars'),
        'driver_ids':      fields.many2many('hr.employee', 'report_delivery_ship_employee_rel',
                            'wizard_id', 'driver_id', 'Driver'),
        'team_ids':     fields.many2many('crm.case.section', 'report_delivery_ship_team_rel',
                            'wizard_id', 'team_id', 'Sales Team'),
        'date_to':      fields.date('To Date', required=True),
        'date_from':    fields.date('From Date', required=True),
        'group_by':     fields.selection(GROUP_BY, 'Group By'),
        'type':         fields.selection([('detail','Detail'),('summary','Summary')], 'Type', required=True),
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
        'type': 'summary',
        'warehouse_ids': _get_warehouse
    }
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        wnames = ''
        for w in form.warehouse_ids:
            wnames += w.name
            wnames += ','
        body = (u"Түгээлтийн тайлан (Эхлэх='%s', Дуусах='%s', Салбар=%s)") % \
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
        widths = [2]
        headers = [[u'Д/д']]
        if (wiz['group_by'] and wiz['type'] == 'detail') or not wiz['group_by']:
            headers[0] += [u'Эхлэх огноо',u'Дуусах огноо']
            widths += [4,4]
        if not wiz['group_by']:
            headers[0] += [u'Жолоочийн нэр',u'Машин']
            widths += [6,4]
        else:
            group = u'Жолоочийн нэр'
            if wiz['group_by'] == 'team':
                group = u'Борлуулалтын баг'
            elif wiz['group_by'] == 'car':
                group = u'Машин'
            headers[0] += [group]
            widths += [6]
        headers[0] += [u'Захиалгын Тоо']
        widths += [5]
        headers[0] += [u'Эзлэхүүн /Норм/',u'Эзлэхүүн',u'Хувь',u'Жин /Норм/',u'Жин',u'Хувь']
        widths += [5,4,5,4]
        datas = {
            'title': u'Түгээлтийн тайлан',
            'headers': headers,
            'header_span': [],
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
        if wiz['car_ids']:
            where += " AND s.carname in ("+','.join(map(str,wiz['car_ids']))+") "
        if wiz['partner_ids']:
            where += " AND p.partner_id in ("+','.join(map(str,wiz['partner_ids']))+") "
        if wiz['driver_ids']:
            where += " AND s.driver_id in ("+','.join(map(str,wiz['driver_ids']))+") "
        if wiz['team_ids']:
            where += " AND s.sales_team_id in ("+','.join(map(str,wiz['team_ids']))+") "
        cr.execute("SELECT s.id, e.id AS emp_id, e.name_related AS emp, "
                        "c.id AS car_id, c.name AS car, s.date_start AS start,"
                        "t.id AS team_id, t.name AS team, s.date_stop AS stop, "
                        "coalesce(c.volume,0) AS cv, coalesce(c.weight,0) AS cw, "
                        "coalesce(SUM(pt.volume),0) AS pv, "
                        "coalesce(SUM(pt.weight),0) AS pw, "
                        "count(distinct p.id) AS count "
                    "FROM stock_delivery_sheet s "
                        "JOIN stock_car_news c ON s.carname=c.id "
                        "JOIN crm_case_section t ON s.sales_team_id=t.id "
                        "JOIN hr_employee e ON s.driver_id=e.id "
                        "JOIN stock_picking p ON s.id=p.sheet_id "
                        "JOIN stock_move m ON p.id=m.picking_id "
                        "JOIN product_product pp ON m.product_id=pp.id "
                        "JOIN product_template pt ON pp.product_tmpl_id=pt.id "
                   "WHERE p.state = 'done' AND m.state = 'done' "+where+" "
                        "AND s.warehouse_id IN %s "
                        "AND (s.date_start >= %s or s.date_start is null) "
                        "AND (s.date_stop <= %s or s.date_stop is null) "
                    "GROUP BY s.id,e.id,e.name_related,c.id,c.name,t.id,t.name,s.date_start,s.date_stop,"
                        "c.volume,c.weight",
                    (tuple(wiz['warehouse_ids']),wiz['date_from'],wiz['date_to']+' 23:59:59'))
        fetched = cr.dictfetchall()
        
        return fetched
    
    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}
        wnames = ''
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        for w in warehouses:
            wnames += w.name
            wnames += ','
        titles = [u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'],wiz['date_to']),
                  u'Салбар: %s'%(wnames)]
        data = []
        total_dict = {'cv': 0.0, 'cw': 0.0,'pv': 0, 'pw': 0.0,'count': 0}
        data_dict = {}
        fetched = self.get_query(cr, uid, wiz, context=context)
        for f in fetched:
            if wiz['group_by']:
                group = False
                gname = u'Тодорхойгүй'
                if wiz['group_by'] == 'car':
                    group = f['car_id']
                    gname = f['car']
                elif wiz['group_by'] == 'employee':
                    group = f['emp_id']
                    gname = f['emp']
                else:
                    group = f['team_id']
                    gname = f['team']
                if group not in data_dict:
                    data_dict[group] = {'name': gname,
                                        'cv': 0.0,
                                        'cw': 0.0,
                                        'pv': 0.0,
                                        'pw': 0.0,
                                        'count': 0,
                                        'lines': {}}
                if f['id'] not in data_dict[group]['lines']:
                    data_dict[group]['lines'][f['id']] = {'car': f['car'],
                                                          'team': f['team'],
                                                          'emp': f['emp'],
                                                          'start': f['start'] or '',
                                                          'stop': f['stop'] or '',
                                                          'cv': 0.0,
                                                          'cw': 0.0,
                                                          'pv': 0.0,
                                                          'pw': 0.0,
                                                          'count': 0}
                data_dict[group]['count'] += f['count']
                data_dict[group]['cv'] += f['cv']
                data_dict[group]['cw'] += f['cw']
                data_dict[group]['pv'] += f['pv']
                data_dict[group]['pw'] += f['pw']
                data_dict[group]['lines'][f['id']]['count'] += f['count']
                data_dict[group]['lines'][f['id']]['cv'] += f['cv']
                data_dict[group]['lines'][f['id']]['cw'] += f['cw']
                data_dict[group]['lines'][f['id']]['pv'] += f['pv']
                data_dict[group]['lines'][f['id']]['pw'] += f['pw']
            else:
                if f['id'] not in data_dict:
                    data_dict[f['id']] = {'car': f['car'],
                                          'team': f['team'],
                                          'emp': f['emp'],
                                          'start': f['start'] or '',
                                          'stop': f['stop'] or '',
                                          'cv': 0.0,
                                          'cw': 0.0,
                                          'pv': 0.0,
                                          'pw': 0.0,
                                          'count': 0}
                data_dict[f['id']]['count'] += f['count']
                data_dict[f['id']]['cv'] += f['cv']
                data_dict[f['id']]['cw'] += f['cw']
                data_dict[f['id']]['pv'] += f['pv']
                data_dict[f['id']]['pw'] += f['pw']
            total_dict['count'] += f['count']
            total_dict['cv'] += f['cv']
            total_dict['cw'] += f['cw']
            total_dict['pv'] += f['pv']
            total_dict['pw'] += f['pw']
                
                    
        number = 1
        row = ['']
        if (wiz['group_by'] and wiz['type'] == 'detail') or not wiz['group_by']:
            row += ['','']
        if not wiz['group_by']:
            row += [u'<b><c>НИЙТ</c></b>','']
        else:
            row += [u'<b><c>НИЙТ</c></b>']
        row += [u'<b>%s</b>'%total_dict['count']]
        per = '0.0%'
        if total_dict['cv'] > 0 and total_dict['pv'] > 0:
            per = str(round(float(total_dict['pv'])*100/float(total_dict['cv']),2))+'%'
        row += [u'<b>%s</b>'%total_dict['cv'],u'<b>%s</b>'%total_dict['pv'],u'<c>%s</c>'%per]
        per = '0.0%'
        if total_dict['cw'] > 0 and total_dict['pw'] > 0:
            per = str(round(float(total_dict['pw'])*100/float(total_dict['cw']),2))+'%'
        row += [u'<b>%s</b>'%total_dict['cw'],u'<b>%s</b>'%total_dict['pw'],u'<c>%s</c>'%per]
        data.append( row )
        if data_dict:
            if wiz['group_by']:
                for val in sorted(data_dict.values(), key=itemgetter('name')):
                    count = 1
                    row = ['<str>%s</str>' % number]
                    if wiz['type'] == 'detail':
                        row += ['','']
                    if wiz['type'] == 'detail':
                        row += [u'<b>%s</b>'%(val['name']),u'<b>%s</b>'%val['count']]
                        per = '0.0%'
                        if val['cv'] > 0 and val['pv'] > 0:
                            per = str(round(float(val['pv'])*100/float(val['cv']),2))+'%'
                        row += [u'<b>%s</b>'%val['cv'],u'<b>%s</b>'%val['pv'],u'<b><c>%s</c></b>'%per]
                        per = '0.0%'
                        if val['cw'] > 0 and val['pw'] > 0:
                            per = str(round(float(val['pw'])*100/float(val['cw']),2))+'%'
                        row += [u'<b>%s</b>'%val['cw'],u'<b>%s</b>'%val['pw'],u'<b><c>%s</c></b>'%per]
                    else:
                        row += [u'%s'%(val['name']),val['count']]
                        per = '0.0%'
                        if val['cv'] > 0 and val['pv'] > 0:
                            per = str(round(float(val['pv'])*100/float(val['cv']),2))+'%'
                        row += [val['cv'],val['pv'],u'<c>%s</c>'%per]
                        per = '0.0%'
                        if val['cw'] > 0 and val['pw'] > 0:
                            per = str(round(float(val['pw'])*100/float(val['cw']),2))+'%'
                        row += [val['cw'],val['pw'],u'<c>%s</c>'%per]
                    data.append( row )
                    if wiz['type'] == 'detail':
                        for v in sorted(val['lines'].values(), key=itemgetter('emp')):
                            row = ['<str>%s.%s</str>' % (number,count)]
                            
                            row += [u'<c>%s</c>'%(v['start']),u'<c>%s</c>'%(v['stop'])]
                            name = v['emp']
                            if wiz['group_by'] == 'employee':
                                name = v['car']
                            row += [u'<space/><space/>%s'%name,v['count']]
                            per = '0.0%'
                            if v['cv'] > 0 and v['pv'] > 0:
                                per = str(round(float(v['pv'])*100/float(v['cv']),2))+'%'
                            row += [v['cv'],v['pv'],u'<c>%s</c>'%per]
                            per = '0.0%'
                            if v['cw'] > 0 and v['pw'] > 0:
                                per = str(round(float(v['pw'])*100/float(v['cw']),2))+'%'
                            row += [v['cw'],v['pw'],u'<c>%s</c>'%per]
                            count += 1
                            data.append(row)
                    number += 1
            else:
                for val in sorted(data_dict.values(), key=itemgetter('emp')):
                    row = ['<str>%s</str>' % (number)]
                    row += [u'<c>%s</c>'%(val['start']),u'<c>%s</c>'%(val['stop'])]
                    row += [u'%s'%val['emp'],u'%s'%val['car'],val['count']]
                    per = '0.0%'
                    if val['cv'] > 0 and val['pv'] > 0:
                        per = str(round(float(val['pv'])*100/float(val['cv']),2))+'%'
                    row += [val['cv'],val['pv'],u'<c>%s</c>'%per]
                    per = '0.0%'
                    if val['cw'] > 0 and val['pw'] > 0:
                        per = str(round(float(val['pw'])*100/float(val['cw']),2))+'%'
                    row += [val['cw'],val['pw'],u'<c>%s</c>'%per]
                    number += 1
                    data.append(row)
        return data, titles
