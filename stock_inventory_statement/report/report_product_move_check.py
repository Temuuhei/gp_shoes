# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.l10n_mn_report_base.report_helper import comma_me
from time import strptime
from datetime import datetime

class ProductMoveReport(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_product_move_check'
    
    def get_heads(self, cr, uid, ids, prod_id, warehouse_id, context=None):
        context = context or {}
        res = {}
        min_qty = max_qty = 0.0
        prod = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        cr.execute("""SELECT product_max_qty AS max_qty, product_min_qty AS min_qty 
                        FROM stock_warehouse_orderpoint WHERE product_id = %s AND warehouse_id = %s"""%(prod_id,warehouse_id))
        point = cr.dictfetchone()
        if point and point['max_qty']: max_qty = str(point['max_qty'])
        if point and point['min_qty']: min_qty = str(point['min_qty'])
        res = {'ean': prod.ean13 or '',
               'name': prod.name or '',
               'code': prod.default_code or '',
               'uom': prod.uom_id.name or '',
               'min_qty': min_qty,
               'max_qty': max_qty}
        return res
    
    def get_move_data(self, cr, uid, ids, data, company, first_dict, context=None):
        context = context or {}
        res = []
        wiz = {'prod_id': data['form']['product_id'][0],
               'from_date': data['form']['from_date'],
               'to_date': data['form']['to_date'],
               'warehouse_id': data['form']['warehouse_id'][0],
               'company_id': company,
               'report_type': data['form']['report_type'],
               'draft': data['form']['draft'],
               'lot_id': data['form']['prodlot_id'] and data['form']['prodlot_id'][0] or False}
        first_avail = first_dict['first_avail']
        first_price = first_dict['first_price']
        first_cost = first_dict['first_cost']
        result = self.pool['report.product.move.check'].get_move_data(cr, uid, wiz, context=context)
        total_dict = {'in_total': 0.0,
                      'out_total': 0.0,
                      'qty_total': 0.0,
                      'change_total': 0.0,
                      'last_cost': 0.0,
                      'first_avail': first_avail,
                      'first_total': (first_avail > 0 and first_price > 0 and first_avail * first_price) or 0.0,
                      'cost_total': (first_avail > 0 and first_cost > 0 and first_avail * first_cost) or 0.0,
                      'last_total': 0.0,
                      'last_avail': 0.0,
                      'first_price': first_price,
                      'first_cost': first_cost}
        in_total = out_total = 0.0
        change = change_total = 0.0
        last_cost = 0.0
        qty_total = 0.0
        if first_price <> 0:
            change = first_price
        for r in result:
            dugaar = partner = seri = ''
            rep_type = ''
            in_qty = out_qty = 0
            if r['dugaar']: 
                if r['dugaar'] == 'pos':
                    dugaar = r['location']
                else:
                    dugaar = r['dugaar']
            if r['lot'] and r['lot'] <> 'price': 
                seri = r['lot']
            if r['partner']: partner = r['partner']
            if r['rep_type']:
                if r['rep_type'] == 'purchase': rep_type = u'Худалдан авалт'
                elif r['rep_type'] == 'inventory': rep_type = u'Тооллого'
                elif r['rep_type'] == 'swap': rep_type = u'Солилцоо'
                elif r['rep_type'] == 'consume': rep_type = u'Дотоод зарлага'
                elif r['rep_type'] == 'procure': rep_type = u'Нөхөн дүүргэлт'
                elif r['rep_type'] == 'refund_purchase': rep_type = u'Худалдан авалтын буцаалт'
                elif r['rep_type'] == 'refund': rep_type = u'Буцаалт'
                elif r['rep_type'] == 'internal': rep_type = u'Дотоод хөдөлгөөн'
                elif r['rep_type'] == 'pos': rep_type = u'Посын борлуулалт'
                elif r['rep_type'] == 'mrp': rep_type = u'Үйлдвэрлэл'
                elif r['rep_type'] == 'refund_mrp': rep_type = u'Үйлдвэрлэлийн буцаалт'
                elif r['rep_type'] == 'price': rep_type = u'Үнэ өөрчлөлт'
                else: rep_type = r['location']
            if r['rep_type'] in ('pos','internal') and r['partner'] is None:
                move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                partner = move.location_id.name
            if data['form']['report_type'] == 'owner':
                qty = 0.0
                if r['in_qty'] and r['in_qty'] <> 0:
                    in_total += r['in_qty']
                    in_qty = r['in_qty']
                    first_avail += r['in_qty']
                    qty_total += r['in_qty']
                    qty = r['in_qty']
                if r['out_qty'] and r['out_qty'] <> 0: 
                    out_total += r['out_qty']
                    out_qty = r['out_qty']
                    first_avail -= r['out_qty']
                    qty_total += r['out_qty']
                    qty = r['out_qty']
                row = {'date': r['date'],
                       'rep_type': rep_type,
                       'number': dugaar,
                       'seri': seri,
                       'partner': partner,
                       'state': r['state'],
                       'qty': comma_me(qty or 0.0),
                       'in_qty': comma_me(in_qty or 0.0),
                       'out_qty': comma_me(out_qty or 0.0),
                       'first_avail': comma_me(first_avail or 0.0)}
            elif data['form']['report_type'] == 'price':
                price = 0.0
                qty = 0.0
                unit = 0.0
                if r['in_qty'] and r['in_qty'] <> 0:
                    in_qty = r['in_qty']
                    first_avail += r['in_qty']
                    qty  = r['in_qty']
                    qty_total += r['in_qty']
                    if r['price']: in_total += (in_qty * r['price'])
                if r['out_qty'] and r['out_qty'] <> 0:
                    out_qty = r['out_qty']
                    first_avail -= r['out_qty']
                    qty = r['out_qty']
                    qty_total += r['out_qty']
                    if r['price']: out_total += (out_qty * r['price'])
                if r['price']:
                    if change == 0: change = r['price']
                    if change <> r['price']:
                        if r['dugaar'] and r['dugaar'] == 'price':
                            unit = (r['price'] - change)
                            change_total += (unit * first_avail)
                    price = r['price']
                row = {'date': r['date'],
                       'rep_type': rep_type,
                       'number': dugaar,
                       'seri': seri,
                       'partner': partner,
                       'state': r['state'],
                       'qty': comma_me(qty),
                       'price': comma_me(price),
                       'in_qty': comma_me((in_qty > 0 and price > 0 and in_qty * price) or 0.0),
                       'out_qty': comma_me((out_qty > 0 and price > 0 and out_qty * price) or 0.0),
                       'unit': comma_me((first_avail > 0 and unit > 0 and first_avail * unit) or 0.0),
                       'amount': comma_me((first_avail > 0 and price > 0 and first_avail * price) or 0.0),
                       'first_avail': comma_me(first_avail)}
            else:
                last_cost = first_cost
                cost = 0.0
                qty = 0.0
                if r['in_qty'] and r['in_qty'] <> 0:
                    qty = r['in_qty']
                    in_qty = r['in_qty']
                    qty_total += r['in_qty']
                    #last_cost = r['cost']
                    if r['cost']: in_total += (in_qty * r['cost'])
                    tmp_cost = in_qty * r['cost']
                    if last_cost > 0 and first_avail > 0:
                        ftotal = last_cost * first_avail
                        mtotal = r['cost'] * r['in_qty']
                    else:
                        ftotal = 0
                        mtotal = r['cost'] * r['in_qty']
                    first_avail += r['in_qty']
                    if ftotal > 0 and mtotal > 0:
                        last_cost = (ftotal+mtotal)/first_avail
                if r['out_qty'] and r['out_qty'] <> 0:
                    qty = r['out_qty']
                    out_qty = r['out_qty']
                    qty_total += r['out_qty']
                    first_avail -= r['out_qty']
                    #last_cost = r['cost']
                    if r['cost']: out_total += (out_qty * r['cost'])
                    tmp_cost = out_qty * r['cost']
                if r['cost']:
                    cost = r['cost']
                row = {'date': r['date'],
                       'rep_type': rep_type,
                       'number': dugaar,
                       'seri': seri,
                       'partner': partner,
                       'state': r['state'],
                       'qty': comma_me(qty),
                       'cost': comma_me(cost),
                       'in_qty': comma_me((in_qty > 0 and cost > 0 and in_qty * cost) or 0.0),
                       'out_qty': comma_me((out_qty > 0 and cost > 0 and out_qty * cost) or 0.0),
                       'costs': comma_me((first_avail > 0 and cost > 0 and first_avail * cost) or 0.0),
                       'first_avail': comma_me(first_avail)}
            res.append(row)
        total_dict['in_total'] = in_total
        total_dict['out_total'] = out_total
        total_dict['change_total'] = change_total
        total_dict['last_cost'] = last_cost
        total_dict['last_total'] = (first_avail > 0 and last_cost > 0 and first_avail * last_cost) or 0.0
        total_dict['last_avail'] = first_avail
        total_dict['qty_total'] = qty_total
        return res, total_dict
    
    def render_html(self, cr, uid, ids, data=None, context=None):
        context = context or {}
        report_obj = self.pool['report']
        wizard_obj = self.pool['report.product.move.check']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_product_move_check')
        wizards = wizard_obj.browse(cr, uid, data['form']['id'], context=context)
        
        from_date = data['wizard']['from_date']
        to_date = data['wizard']['to_date']
        prod_id = data['wizard']['prod_id']
        wname = data['wizard']['wname']
        warehouse_id = data['wizard']['warehouse_id']
        get_heads = self.get_heads(cr, uid, ids, prod_id, warehouse_id, context=context)
        get_heads['lot'] = data['wizard']['lot_name']
        get_heads['life_date'] = data['wizard']['life_date']
        get_heads['warehouse'] = wname
        first_dict = {'first_avail': data['wizard']['first_avail'],
                      'first_cost': data['wizard']['first_cost'],
                      'first_price': data['wizard']['first_price']}
        lines, total = self.get_move_data(cr, uid, ids, data, data['wizard']['company_id'], first_dict, context=context)
        total['in_total'] = comma_me(total['in_total'])
        total['out_total'] = comma_me(total['out_total'])
        total['change_total'] = comma_me(total['change_total'])
        total['last_cost'] = comma_me(total['last_cost'])
        total['last_total'] = comma_me(total['last_total'])
        total['last_avail'] = comma_me(total['last_avail'])
        total['qty_total'] = comma_me(total['qty_total'])
        total['first_total'] = comma_me(total['first_total'])
        total['cost_total'] = comma_me(total['cost_total'])
        total['first_avail'] = comma_me(total['first_avail'])
        total['first_price'] = comma_me(total['first_price'])
        total['first_cost'] = comma_me(total['first_cost'])
        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': wizards,
            'lines': lines,
            'total': total,
            'type': data['wizard']['report_type'],
            'from_date': from_date,
            'to_date': to_date,
            'company': data['wizard']['company'],
            'head': get_heads
        }
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.report_product_move_check', docargs, context=context)
