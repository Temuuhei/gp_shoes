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
from openerp.addons.l10n_mn_report_base.report_helper import comma_me, verbose_numeric, convert_curr

class PickingDriverReport(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_driver_picking'
    
    def render_html(self, cr, uid, ids, data=None, context=None):
        context = context or {}
        report_obj = self.pool['report']
        delivery_obj = self.pool['stock.delivery.sheet']
        sale_obj = self.pool['sale.order']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_driver_picking')
        deliveries = delivery_obj.browse(cr, uid, ids, context=context)
        verbose_total = {}
        pick_total = {}
        sale_type = {}
        total_dict = {}
        weights = {'volume': 0.0,
                   'weight': 0.0,
                   'weight_net': 0.0}
        address = {}
        currency = ''
        curr = u''
        div_curr = u''
        for sheet in deliveries:
            for pick in sheet.picking_ids:
                sale_id = sale_obj.search(cr, uid, [('name','=',pick.origin)])
                if sale_id:
                    sale = sale_obj.browse(cr, uid, sale_id[0])
                    sale_type[pick.id] = sale.sale_category_id.name
        for sheet in deliveries:
            total = 0.0
            for pick in sheet.picking_ids:
                ptotal = 0.0
                currency = pick.company_id.currency_id.name
                if pick.company_id.currency_id:
                    curr = pick.company_id.currency_id.integer
                    div_curr = pick.company_id.currency_id.divisible
                if pick.partner_id and pick.partner_id.id not in address:
                    addr = ''
                    if pick.partner_id.state_id:
                        addr += pick.partner_id.state_id.name
                        addr +=', '
                    if pick.partner_id.city:
                        addr += pick.partner_id.city
                        addr +=', '
                    if pick.partner_id.street:
                        addr += pick.partner_id.street
                        addr +=', '
                    if pick.partner_id.street2:
                        addr += pick.partner_id.street2
                        addr +=', '
                    if pick.partner_id.phone:
                        addr +=' ('
                        addr += pick.partner_id.phone
                        addr +=')'
                    elif pick.partner_id.mobile:
                        addr +=' ('
                        addr += pick.partner_id.mobile
                        addr +=')'
                    address[pick.partner_id.id] = addr
                    
                for move in pick.move_lines:
                    price = move.list_price
                    unit = move.list_price
                    discount = 0.0
                    volume = 0.0
                    weight = 0.0
                    weight_net = 0.0
                    if move.procurement_id and move.procurement_id.sale_line_id:
                        price = unit = move.procurement_id.sale_line_id.price_unit
                        if move.procurement_id.sale_line_id.discount > 0:
                            discount = move.procurement_id.sale_line_id.discount
                            price = unit - (discount*unit/100)
                    if move.product_id.volume > 0:
                        volume = move.product_qty* move.product_id.volume
                    if move.product_id.weight > 0:
                        volume = move.product_qty* move.product_id.weight
                    if move.product_id.weight_net > 0:
                        volume = move.product_qty* move.product_id.weight_net
                    ptotal += price * move.product_qty
                    weights['volume'] += volume
                    weights['weight'] += weight
                    weights['weight_net'] += weight_net
                if pick.id not in pick_total:
                    pick_total[pick.id] = comma_me(ptotal)
                total += ptotal
            if sheet.id not in total_dict:
                total_dict[sheet.id] = comma_me(total)
            if sheet.id not in verbose_total:
                list = verbose_numeric(abs(total))
                verbose_total[sheet.id] = convert_curr(list, curr, div_curr)
        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': deliveries,
            'address': address,
            'currency': currency,
            'pick_total': pick_total,
            'sale_type': sale_type,
            'verbose_total': verbose_total,
            'weights': weights,
            'total': total_dict,
            'data_report_margin_top': 5,
            'data_report_header_spacing': 5
        }
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.report_driver_picking', docargs, context=context)
