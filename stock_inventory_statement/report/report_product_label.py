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

class ProductLabelPrint(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_product_label'
    
    def render_html(self, cr, uid, ids, data=None, context=None):
        context = context or {}
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_product_label')
        active_ids = context['active_ids']
        if 'ids' in data and data['ids']:
            active_ids = data['ids']
        if not active_ids and 'root_type' in data['form']:
            if data['form']['root_type'] == 'location':
                active_ids = data['form']['location_ids']
            else:
                active_ids = data['form']['product_ids']
        if data['form']['root_type'] == 'location':
            labels = self.pool.get('stock.location').browse(cr, uid, active_ids, context=context)
        else:
            labels = self.pool.get('product.product').browse(cr, uid, active_ids, context=context)
        verbose_total_dict = {}
        lines = []
        line_dict = {}
        for l in labels:
            barcode = ''
            if data['form']['root_type'] == 'product':
                code = l.default_code or ''
                if l.ean13:
                    barcode = str(l.ean13)
                line = {'name': l.name_get(context=context)[0][1],
                        'code': code,
                        'barcode': barcode}
                if data['form']['type'] == 'price':
                    line.update({'price': l.lst_price})
            else:
                if l.loc_barcode:
                    barcode = str(l.loc_barcode)
                line = {'name': l.name,
                        'barcode': barcode}
            lines.append(line)
        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': labels,
            'lines': lines,
            'root_type': data['form']['root_type'],
            'type': data['form']['type'],
            'report_type': data['form']['report_type']
        }
        return report_obj.render(cr, uid, ids, 'l10n_mn_stock.report_product_label', docargs, context=context)
