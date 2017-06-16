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
from openerp.addons.l10n_mn_report_base.report_helper import verbose_numeric,comma_me, convert_curr
from operator import itemgetter

class ReportPickingAll(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_picking_all'

    def render_html(self, cr, uid, ids, data=None, context=None):
        if context is None:
            context = {}
        report_obj = self.pool['report']
        picking_obj = self.pool['stock.picking']
        tax_obj = self.pool['account.tax']
        uom_obj = self.pool['product.uom']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_picking_all')
        if data and not ids:
            ids = data['ids']
        pickings = picking_obj.browse(cr, uid, ids, context=context)
        verbose_total_dict = {}
        TAX_FACTOR = self.pool.get("ir.config_parameter").get_param(cr, uid, 'report.tax') or 0.0
        pick_names = ''
        lines = {}
        total = {}
        lot = False
        type = 'in'
        sales_type = {}
        incount = count = 0
        outcount = 0
        currency = ''
        operation_ids = []
        address = {}
        owners = {}
        pack_datas = {}
        curr = u''
        div_curr = u''      
        driver = {'yes': 'False',
                  'name': ''}
        if data and 'driver_id' in data and data['driver_id']:
            emp = self.pool.get('hr.employee').browse(cr, uid, data['driver_id'], context=context)
            driver['yes'] = 'True'
            driver['name'] = emp.name
            if emp.mobile_phone:
                driver['name'] += ' ('
                driver['name'] += emp.mobile_phone
                driver['name'] += ')'
        for pick in pickings:
            if pick.state in ('cancel','draft'):
                raise osv.except_osv(_('Warning!'), _('Ноорог болон Цуцалсан баримтыг хэвлэх боломжгүй!'))
            if pick.picking_type_id.code == 'outgoing':
                outcount += 1
            elif pick.picking_type_id.code == 'incoming':
                incount += 1
            else:
                count += 1
            owners[pick.id] = ''
            if pick.section_id:
                owners[pick.id] += pick.section_id.name
                if pick.section_id.user_id:
                    owners[pick.id] += ' - '
                    owners[pick.id] += pick.section_id.user_id.name
                    if pick.section_id.user_id.mobile:
                        owners[pick.id] += ' ('
                        owners[pick.id] += pick.section_id.user_id.mobile
                        owners[pick.id] += ')'
                    elif pick.section_id.user_id.phone:
                        owners[pick.id] += ' ('
                        owners[pick.id] += pick.section_id.user_id.phone
                        owners[pick.id] += ')'
            address[pick.partner_id.id] = ''
            if pick.partner_id.country_id:
                address[pick.partner_id.id] += pick.partner_id.country_id.name
                address[pick.partner_id.id] += ', '
            if pick.partner_id.city:
                address[pick.partner_id.id] += pick.partner_id.city
                address[pick.partner_id.id] += ', '
            if pick.partner_id.street:
                address[pick.partner_id.id] += pick.partner_id.street
                address[pick.partner_id.id] += ', '
            if pick.partner_id.street2:
                address[pick.partner_id.id] += pick.partner_id.street2
                address[pick.partner_id.id] += ', '
            if pick.partner_id.phone:
                address[pick.partner_id.id] += ' ('
                address[pick.partner_id.id] += pick.partner_id.phone
                address[pick.partner_id.id] += ')'
            elif pick.partner_id.mobile:
                address[pick.partner_id.id] += ' ('
                address[pick.partner_id.id] += pick.partner_id.mobile
                address[pick.partner_id.id] += ')'
            currency = pick.company_id.currency_id.name
            if pick.company_id.currency_id:
                curr = pick.company_id.currency_id.integer
                div_curr = pick.company_id.currency_id.divisible
        if incount > 0 and outcount > 0 and count > 0:
            raise osv.except_osv(_('Warning!'), _('Баримтын төрөл өөр байж болохгүй!'))
        
        document_name = u"Бараа материалын орлогын баримт" 
        for pick in pickings:
            line = {}
            total.update({pick.id:{'qty': 0.0,
                                   'amount': 0.0,
                                   'discount': 0.0,
                                   'total': 0.0,
                                   'total1': 0.0,
                                   'vat': 0.0,
                                   'novat': 0.0,
                                   'pack': 0.0,
                                   'loose': 0.0,
                                   'pack_total': 0.0}})
            if pick.picking_type_id.code == 'outgoing':
                type = 'out'
                document_name = u"Бараа материалын зарлагын баримт"
            sales_type.update({pick.id: ''})
#             if pick.pack_operation_ids:
#                 for oper in pick.pack_operation_ids:
#                     move = False
#                     if oper.linked_move_operation_ids:
#                         move = oper.linked_move_operation_ids[0].move_id
#                     price = oper.list_price
#                     unit = oper.list_price
#                     discount = 0.0
#                     if move:
#                         if move.procurement_id and move.procurement_id.sale_line_id and pick.picking_type_id.code == 'outgoing':
#                             sales_type[pick.id] = move.procurement_id.sale_line_id.order_id.sale_category_id.name
#                             price = unit = move.procurement_id.sale_line_id.price_unit
#                             if move.procurement_id.sale_line_id.discount > 0:
#                                 discount = move.procurement_id.sale_line_id.discount
#                                 unit = price - (discount*price/100)
#                         if move.origin_returned_move_id and move.origin_returned_move_id.procurement_id and\
#                                   move.origin_returned_move_id.procurement_id.sale_line_id and pick.picking_type_id.code == 'incoming':
#                             sales_type[pick.id] = move.origin_returned_move_id.procurement_id.sale_line_id.order_id.sale_category_id.name
#                             type = 'out'
#                             document_name = u"Бараа материалын буцаалтын орлогын баримт"
#                             price = unit = move.origin_returned_move_id.procurement_id.sale_line_id.price_unit
#                             if move.origin_returned_move_id.procurement_id.sale_line_id.discount > 0:
#                                 discount = move.origin_returned_move_id.procurement_id.sale_line_id.discount
#                                 unit = price - (discount*price/100.0)
#                     if oper.lot_id:
#                         lot = True
#                     if oper.id not in line:
#                         line[oper.id] = {'name': oper.product_id.name,
#                                           'ean': oper.product_id.ean13 or '',
#                                           'uom': oper.product_uom_id.name,
#                                           'lot': oper.lot_id and oper.lot_id.name or '',
#                                           'qty': comma_me(oper.product_qty) or 0.0,
#                                           'price': comma_me(price) or 0.0,
#                                           'unit': comma_me(unit) or 0.0,
#                                           'discount': comma_me(discount),
#                                           'amount': comma_me(price * oper.product_qty) or 0.0,
#                                           'total': comma_me(unit * oper.product_qty) or 0.0}
#                     total[pick.id]['qty'] += oper.product_qty
#                     total[pick.id]['amount'] += price * oper.product_qty
#                     total[pick.id]['discount'] += (price * oper.product_qty) * discount/100
#                     total[pick.id]['total'] += unit * oper.product_qty
#                     novat = round(float(unit * oper.product_qty)/float(1+float(TAX_FACTOR)),4)
#                     total[pick.id]['novat'] += novat
#                     total[pick.id]['vat'] += (unit * oper.product_qty) - novat
#                     
#             else:

            pack_datas[pick.id] = {}
            for move in pick.move_lines:
                cr.execute("select tx.id from account_tax tx " 
                           "join sale_order_tax stx on stx.tax_id = tx.id "
                           "left join sale_order_line sol on sol.id = stx.order_line_id " 
                           "left join procurement_order proc on proc.sale_line_id = sol.id " 
                           "left join stock_move move on move.procurement_id = proc.id " 
                           "where move.id='"+str(move.id)+"' ")
                
                fetched = cr.fetchall()
                tax_ids = []
                acc_move = 0.0
                price_include = False
                amount = 0.0
                if fetched != []:
                    for i in fetched:
                        tax_ids.append(i[0])
                if tax_ids != []:
                    for tax in tax_obj.browse(cr, uid, tax_ids):
                        if tax.price_include:
                           price_include = True 
                        amount = tax.amount
                
                list_price = self.pool.get("product.product").price_get(cr, uid, move.product_id.id, 
                    ptype='list_price', context=dict(context.items(),
                    warehouse=move.warehouse_id.id,company_id=move.company_id.id))
                price = move.list_price
                unit = move.list_price
                if price >= 1.0 and unit>= 1.0 :
                    price = list_price[move.product_id.id]
                    unit = list_price[move.product_id.id]
                discount = 0.0
                lot = ''
                pack_qty = 0.0
                product_qty = move.product_qty
                packaging = (move.product_id.packaging_ids and move.product_id.packaging_ids[0]) or False
                if packaging:                    
                    pack_qty = packaging.qty
                if move.product_id.uom_id.id <> move.product_uom.id:
                    product_qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)
                if move.product_id.id not in pack_datas[pick.id]:
                    pack_datas[pick.id].update({move.product_id.id:{'package': pack_qty,
                                                      'qty': 0.0,
                                                      'count': 0}})

                if move.linked_move_operation_ids:
                    for oper in move.linked_move_operation_ids:
                        op = oper.operation_id
#                         lot += op.lot_id and op.lot_id.name or ''
                        lot = op.lot_id and op.lot_id.name or ''
                if move.procurement_id and move.procurement_id.sale_line_id and pick.picking_type_id.code == 'outgoing':
                    sales_type[pick.id] = move.procurement_id.sale_line_id.order_id.sale_category_id.name
                    price = unit = move.procurement_id.sale_line_id.price_unit
                    if move.procurement_id.sale_line_id.discount > 0:
                        discount = move.procurement_id.sale_line_id.discount
                        unit = price - (discount*price/100.0)
                if move.origin_returned_move_id and move.origin_returned_move_id.procurement_id and\
                          move.origin_returned_move_id.procurement_id.sale_line_id and pick.picking_type_id.code == 'incoming':
                    sales_type[pick.id] = move.origin_returned_move_id.procurement_id.sale_line_id.order_id.sale_category_id.name
                    type = 'out'
                    document_name = u"Бараа материалын буцаалтын орлогын баримт"
                    price = unit = move.origin_returned_move_id.procurement_id.sale_line_id.price_unit
                    if move.origin_returned_move_id.procurement_id.sale_line_id.discount > 0:
                        discount = move.origin_returned_move_id.procurement_id.sale_line_id.discount
                        unit = price - (discount*price/100.0)
                if price_include == True:  
                    total1 =  unit * move.product_qty
                else:
                    total1 = (unit * move.product_qty) + round(float(unit * move.product_qty)*float(amount),4)
                    
                if move.id not in line:
                    line[move.id] = {'name': move.product_id.name_get(context=context)[0][1],
                                      'id': move.product_id.id,
                                      'ean': move.product_id.ean13 or '',
                                      'uom': move.product_uom.name,
                                      'lot': lot,
                                      'qty': comma_me(move.product_qty),
                                      'price': comma_me(price),
                                      'unit': comma_me(unit),
                                      'discount': comma_me(discount),
                                      'amount': comma_me(price * move.product_qty),
                                      'total1': comma_me(total1),
                                      'total': comma_me(unit * move.product_qty)}
                pack_datas[pick.id][move.product_id.id]['qty'] += product_qty
                total[pick.id]['qty'] += move.product_qty
                total[pick.id]['amount'] += price * move.product_qty
#                 total[pick.id]['total1'] += unit * move.product_qty
                total[pick.id]['discount'] += (price * move.product_qty) * discount/100
                if price_include == True:     
                    novat = round(float(unit * move.product_qty)/float(1+float(amount)),4)
                    total[pick.id]['vat'] += (unit * move.product_qty) - novat
                    total[pick.id]['total'] += (unit * move.product_qty) - float(unit * move.product_qty)*float(amount) 
                    total[pick.id]['total1'] += unit * move.product_qty
                else:                    
                    novat =float(unit * move.product_qty)
                    total[pick.id]['total'] += (unit * move.product_qty) + float(unit * move.product_qty)*float(amount)
                    total[pick.id]['vat'] += round(float(unit * move.product_qty)*float(amount),4)#(unit * move.product_qty) + novat
                    total[pick.id]['total1'] += (unit * move.product_qty) + round(float(unit * move.product_qty)*float(amount),4)
                total[pick.id]['novat'] += novat
            
            list = verbose_numeric(abs(total[pick.id]['total']))
            list = verbose_numeric(abs(total[pick.id]['total1']))
            verbose_total_dict[pick.id] = convert_curr(list, curr, div_curr)
            total[pick.id]['qty'] = comma_me(total[pick.id]['qty'])
            total[pick.id]['amount'] = comma_me(total[pick.id]['amount'])
            total[pick.id]['discount'] = comma_me(total[pick.id]['discount'])
            total[pick.id]['total'] = comma_me(total[pick.id]['total'])
            total[pick.id]['total1'] = comma_me(total[pick.id]['total1'])
            total[pick.id]['vat'] = comma_me(total[pick.id]['vat'])
            total[pick.id]['novat'] = comma_me(total[pick.id]['novat'])
            lines[pick.id] = sorted(line.values(), key=itemgetter('name'))
        pick_ids = []
        #vat_list = {}
        for line in pickings:
            pick_ids.append(str(line.id))
        
        pick_ids = tuple(pick_ids)
        if len(pick_ids) == 1:
            pick_ids = str(pick_ids).replace(',','')

        '''cr.execute("select i.vat_bill_id, i.vat_lottery, i.vat_qr_data, i.vat_register_no, sp.id from account_invoice i "
                "join sale_order_invoice_rel so on so.invoice_id = i.id "
                "left join sale_order s on s.id = so.order_id "
                "left join stock_picking sp on sp.group_id = s.procurement_group_id "
                "where i.vat_bill_id is not null and sp.id in %s " % str(pick_ids))
        vat_datas = cr.fetchall()
        
        if vat_datas != []:
            for bill_id, lottery, qr_data, register, pid in vat_datas:
                vat_list[pid] = {
                    'bill_id': bill_id,
                    'lottery': lottery,
                    'qr_data': qr_data,
                    'register': register or '',
                }   '''         

        pdatas = {}
        sum_pack = 0.0
        sum_loose = 0.0
        sum_pack_total = 0.0
        if pack_datas:
            for pick in pickings:
                for k,v in pack_datas.iteritems():
                    pdatas[k] = {}
                    for i,j in v.iteritems():                
                        pack = 0.0
                        loose = v[i]['qty']
                        if v[i]['package'] > 0:
                            pack = (v[i]['qty'] <> 0 and int(int(v[i]['qty'])/ int(v[i]['package']))) or 0
                            loose = (v[i]['qty'] <> 0 and v[i]['qty'] % v[i]['package']) or 0
                        if i not in pdatas[k]:
                            pdatas[k].update({i:{'pack': comma_me(pack),
                                         'loose': comma_me(loose),
                                         'total': comma_me(v[i]['qty']),
                                         'count': v[i]['count']}})
                            sum_pack += pack
                            sum_loose += loose
                            sum_pack_total += v[i]['qty']
                    if total[k]['pack'] == 0.0 and total[k]['loose'] == 0.0 and total[k]['pack_total'] == 0.0:
                        total[k]['pack'] += sum_pack
                        total[k]['loose'] += sum_loose
                        total[k]['pack_total'] += sum_pack_total
                    sum_pack = 0.0
                    sum_loose = 0.0
                    sum_pack_total = 0.0
        
        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': pickings,
            'lines': lines,
            'pack_datas': pdatas,
            'total': total,
            #'vat_list': vat_list,
            'sales_type':sales_type,
            'driver': driver,
            'address':address,
            'owners':owners,
            'type': type,
            'currency': currency,
            'lot': lot,
            'verbose_total': verbose_total_dict,
            'document_name': document_name,
            'data_report_margin_top': 5,
            'data_report_header_spacing': 5
        }
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.report_picking_all', docargs, context=context)

class ReportPickingCost(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_picking_cost'

    def render_html(self, cr, uid, ids, data=None, context=None):
        if context is None:
            context = {}
        report_obj = self.pool['report']
        picking_obj = self.pool['stock.picking']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_picking_cost')
        pickings = picking_obj.browse(cr, uid, ids, context=context)
        verbose_total_dict = ''
        pick_names = ''
        pick_type = 'one'
        curr = u''
        div_curr = u''   
        lines = {}
        total = {'qty': 0.0,
                 'amount': 0.0}
        lot = False
        type = 'in'
        incount = count = 0
        outcount = 0
        currency = ''
        for pick in pickings:
            if pick.state in ('cancel','draft'):
                raise osv.except_osv(_('Warning!'), _('Ноорог болон Цуцалсан баримтыг хэвлэх боломжгүй!'))
            if pick.picking_type_id.code == 'outgoing':
                outcount += 1
            elif pick.picking_type_id.code == 'incoming':
                incount += 1
            else:
                count += 1
            currency = pick.company_id.currency_id.name
            if pick.company_id.currency_id:
                curr = pick.company_id.currency_id.integer
                div_curr = pick.company_id.currency_id.divisible
        if incount > 0 and outcount > 0 and count > 0:
            raise osv.except_osv(_('Warning!'), _('Баримтын төрөл өөр байж болохгүй!'))
            
        for pick in pickings:
            pick_names += pick.name
            pick_names += ', '
            if pick.picking_type_id.code == 'outgoing':
                type = 'out'
            if pick.pack_operation_ids:
                for oper in pick.pack_operation_ids:
                    if oper.lot_id:
                        lot = True
                    if oper.id not in lines:
                        lines[oper.id] = {'name': oper.product_id.name,
                                          'ean': oper.product_id.ean13 or '',
                                          'uom': oper.product_uom_id.name,
                                          'lot': oper.lot_id and oper.lot_id.name or '',
                                          'qty': comma_me(oper.product_qty) or 0.0,
                                          'cost': comma_me(oper.cost) or 0.0,
                                          'amount': comma_me(oper.cost * oper.product_qty) or 0.0}
                    total['qty'] += oper.product_qty
                    total['amount'] += oper.cost * oper.product_qty
            else:
                for move in pick.move_lines:
                    if move.id not in lines:
                        lines[move.id] = {'name': move.product_id.name,
                                          'ean': move.product_id.ean13 or '',
                                          'uom': move.product_uom.name,
                                          'lot': '',
                                          'qty': comma_me(move.product_qty),
                                          'cost': comma_me(move.price_unit),
                                          'amount': comma_me(move.price_unit * move.product_qty)}
                    total['qty'] += move.product_qty
                    total['amount'] += move.price_unit * move.product_qty
        if len(pickings) > 1:
            pick_type = 'many'
            pickings = [pickings[0]]
        list = verbose_numeric(abs(total['amount']))
        verbose_total_dict = convert_curr(list, curr, div_curr)
        total['qty'] = comma_me(total['qty'])
        total['amount'] = comma_me(total['amount'])
        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': pickings,
            'lines': sorted(lines.values(), key=itemgetter('name')),
            'pick_type': pick_type,
            'pick_names': pick_names,
            'total': total,
            'type': type,
            'currency': currency,
            'lot': lot,
            'verbose_total': verbose_total_dict,
            'data_report_margin_top': 5,
            'data_report_header_spacing': 5
        }
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.report_picking_cost', docargs, context=context)
