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
from operator import itemgetter

class StockInventoryPrint(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.print_stock_inventory'
    
    def render_html(self, cr, uid, ids, data=None, context=None):
        context = context or {}
        report_obj = self.pool['report']
        inventory_obj = self.pool['stock.inventory']
        line_obj = self.pool['stock.inventory.line']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.print_stock_inventory')
        active_ids = context['active_ids']
        if 'ids' in data and data['ids']:
            active_ids = data['ids']
        inventories = inventory_obj.browse(cr, uid, active_ids, context=context)
        verbose_total_dict = {}
        lines = []
        total_dict = {'avail_qty': 0,
                      'avail_amount': 0.0,
                      'check_qty': 0,
                      'check_amount': 0.0,
                      'less_qty': 0,
                      'less_amount': 0.0,
                      'more_qty': 0,
                      'more_amount': 0.0}
        total_avail_qty = 0
        total_avail_amount = 0
        total_check_qty = 0
        total_check_amount = 0
        total_less_qty = 0
        total_less_amount = 0
        total_more_qty = 0
        total_more_amount = 0
        line_dict = {}
        count_dict = {}
        for inv in inventories:
            for i in inv.line_ids:
                lot = i.prod_lot_id.id or False
                if i.product_id.id not in line_dict:
                    line_dict[i.product_id.id] = {}
                if lot not in line_dict[i.product_id.id]:
                    line_dict[i.product_id.id][lot] = i.theoretical_qty
                else:
                    line_dict[i.product_id.id][lot] += i.theoretical_qty
                if i.product_id.id not in count_dict:
                    count_dict[i.product_id.id] = {}
                if lot not in count_dict[i.product_id.id]:
                    count_dict[i.product_id.id][lot] = 0
                count_dict[i.product_id.id][lot] += i.product_qty
                    
            if inv.move_ids:
                for m in inv.move_ids:
                    check_qty = 0.0
                    theoritical_qty = 0.0
                    price = m.list_price
                    name = ''
                    if m.product_id and m.product_id.default_code:
                        name += '['+m.product_id.default_code+']'
                    name += m.product_id.name
                    if 'type' in data['form']:
                        if data['form']['type'] == 'cost':
                            price = m.price_unit
                    if m.product_id.id in line_dict:
                        reslot = m.restrict_lot_id.id or False
                        theoritical_qty = line_dict[m.product_id.id].get(reslot,0)
                        check_qty = count_dict[m.product_id.id].get(reslot,0)
                        
                    line = {'name': name,
                            'categ_id':m.product_id.categ_id.complete_name or '',
                            'ean': m.product_id and m.product_id.ean13 or '',
                            'uom': m.product_uom and m.product_uom.name or '',
                            'prodlot': (m.restrict_lot_id and m.restrict_lot_id.name) or '',
                            'expire': m.restrict_lot_id and m.restrict_lot_id.life_date or '',
                            'avail_qty': theoritical_qty or 0,
                            'avail_amount': (theoritical_qty > 0 and price > 0) and theoritical_qty * price or 0,
                            'check_qty': check_qty,
                            'check_amount': check_qty * (price or 0),
                            'less_qty': 0.0,
                            'less_amount': 0.0,
                            'more_qty': 0.0,
                            'more_amount': 0.0}
                    if check_qty < theoritical_qty:
                        line['less_qty'] += theoritical_qty - check_qty 
                        if (theoritical_qty - check_qty) > 0:
                            line['less_amount'] += (theoritical_qty - check_qty) * price
                    else:
                        line['more_qty'] += check_qty - theoritical_qty
                        if (check_qty - theoritical_qty) > 0:
                            line['more_amount'] += (check_qty - theoritical_qty) * price
                    total_avail_qty += line['avail_qty']
                    total_avail_amount += line['avail_amount']
                    total_check_qty += line['check_qty']
                    total_check_amount += line['check_amount']
                    total_less_qty += line['less_qty']
                    total_less_amount += line['less_amount']
                    total_more_qty += line['more_qty']
                    total_more_amount += line['more_amount']
                    line.update({'avail_qty': comma_me(line['avail_qty'])})
                    line.update({'avail_amount': comma_me(line['avail_amount'])})
                    line.update({'check_qty': comma_me(line['check_qty'])})
                    line.update({'check_amount': comma_me(line['check_amount'])})
                    line.update({'less_qty': comma_me(line['less_qty'])})
                    line.update({'less_amount': comma_me(line['less_amount'])})
                    line.update({'more_qty': comma_me(line['more_qty'])})
                    line.update({'more_amount': comma_me(line['more_amount'])})
                    lines.append(line)
            else:
                for l in inv.line_ids:
                    name = ''
                    price = l.product_id.lst_price
                    if l.product_code:
                        name += '['+l.product_code+']'
                    name += l.product_name
                    if 'type' in data['form']:
                        if data['form']['type'] == 'cost':
                            price = l.product_id.price_get('standard_price', context=context)[l.product_id.id]
                    line = {'name': name,
                            'categ_id': l.product_id.categ_id.complete_name or '',
                            'ean': l.product_id and l.product_id.ean13 or '',
                            'uom': l.product_uom_id and l.product_uom_id.name or '',
                            'prodlot': (l.prodlot_name or (l.prod_lot_id and l.prod_lot_id.name)) or '',
                            'expire': l.prod_lot_id and l.prod_lot_id.life_date or '',
                            'avail_qty': l.theoretical_qty or 0,
                            'avail_amount': (l.theoretical_qty > 0 and price > 0) and l.theoretical_qty * price or 0,
                            'check_qty': l.product_qty or 0,
                            'check_amount': (l.product_qty > 0 and price > 0) and l.product_qty * price or 0,
                            'less_qty': 0.0,
                            'less_amount': 0.0,
                            'more_qty': 0.0,
                            'more_amount': 0.0}
                    if l.theoretical_qty > l.product_qty:
                        line['less_qty'] += l.theoretical_qty - l.product_qty
                        if (l.theoretical_qty - l.product_qty) > 0:
                            line['less_amount'] += (l.theoretical_qty - l.product_qty) * price
                    else:
                        line['more_qty'] += l.product_qty - l.theoretical_qty
                        if (l.product_qty - l.theoretical_qty) > 0:
                            line['more_amount'] += (l.product_qty - l.theoretical_qty) * price
                    total_avail_qty += line['avail_qty']
                    total_avail_amount += line['avail_amount']
                    total_check_qty += line['check_qty']
                    total_check_amount += line['check_amount']
                    total_less_qty += line['less_qty']
                    total_less_amount += line['less_amount']
                    total_more_qty += line['more_qty']
                    total_more_amount += line['more_amount']
                    if line['check_qty'] == 0:
                        line.update({'check_qty': ''})
                    else:
                        line.update({'check_qty': comma_me(line['check_qty'])})
                    if line['check_amount'] == 0:
                        line.update({'check_amount': ''})
                    else:
                        line.update({'check_amount': comma_me(line['check_amount'])})
                    line.update({'avail_qty': comma_me(line['avail_qty'])})
                    line.update({'avail_amount': comma_me(line['avail_amount'])})
                    line.update({'less_qty': comma_me(line['less_qty'])})
                    line.update({'less_amount': comma_me(line['less_amount'])})
                    line.update({'more_qty': comma_me(line['more_qty'])})
                    line.update({'more_amount': comma_me(line['more_amount'])})
                    lines.append(line)
        total_dict['avail_qty'] = comma_me(total_avail_qty)
        total_dict['avail_amount'] = comma_me(total_avail_amount)
        total_dict['check_qty'] = comma_me(total_check_qty)
        total_dict['check_amount'] = comma_me(total_check_amount)
        total_dict['less_qty'] = comma_me(total_less_qty)
        total_dict['less_amount'] = comma_me(total_less_amount)
        total_dict['more_qty'] = comma_me(total_more_qty)
        total_dict['more_amount'] = comma_me(total_more_amount)
        if data['form']['is_groupby_category'] == True:
            docargs = {
                'doc_ids': ids,
                'doc_model': report.model,
                'docs': inventories,
                'lines': sorted(lines, key=itemgetter('categ_id')),
                'seri': data['form']['serial'],
                'is_groupby_category': data['form']['is_groupby_category'],
                'type': data['form']['type'],
                'avail': data['form']['available'],
                'total_dict': total_dict
            }
        else:
            docargs = {
                'doc_ids': ids,
                'doc_model': report.model,
                'docs': inventories,
                'lines': lines,
                'seri': data['form']['serial'],
                'is_groupby_category': data['form']['is_groupby_category'],
                'type': data['form']['type'],
                'avail': data['form']['available'],
                'total_dict': total_dict
            }
        
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.print_stock_inventory', docargs, context=context)

