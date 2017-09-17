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

from odoo import osv, fields, models
from openerp.tools.translate import _
import time
from operator import itemgetter

class stock_inventory_statement(models.Model):
    _name = 'stock.inventory.statement'
    _inherit = 'abstract.report.model'
    _description = 'Stock Inventory Statement'
    def get_group_by(self):
        res = [
               ('category', _('Category'))]
        pos_obj = self.pool.get('pos.category')
        if pos_obj:
            res += [('pos_categ', _('Pos Category'))]
        return res

    def _get_pos_install(self):
        '''
            Посын модуль суусан эсэхийг шалгана.
        '''
        pos_obj = self.pool.get('pos.order')
        if pos_obj:
            return True
        return False

    company_id = fields.Many2one('res.company', 'Company', readonly=True,default=lambda self: self.env['res.company']._company_default_get('account.account'))
    warehouse_ids = fields.Many2many('stock.warehouse', 'stock_inventory_statement_warehouse_rel', 'wizard_id', 'warehouse_id', 'Warehouse')
    prod_categ_ids = fields.Many2many('product.category', 'stock_inventory_statement_prod_categ_rel', 'wizard_id', 'prod_categ_id', 'Product Category')  # domain=['|',('parent_id','=',False),('parent_id.parent_id','=',False)]),
    product_ids = fields.Many2many('product.product', 'stock_inventory_statement_product_rel', 'wizard_id', 'product_id', 'Product')
    income_expense = fields.Boolean('Show Income and Expenditure?')
    partner_ids = fields.Many2many('res.partner', 'stock_inventory_statement_partner_rel', 'wizard_id', 'partner_id', 'Partner')
    grouping = fields.Selection(get_group_by, 'Grouping')
    sorting = fields.Selection([('default_code', 'Default Code'),
                                ('name', 'Product Name')], 'Sorting', required=True, default = 'default_code')
    type = fields.Selection([('detail', 'Detail'), ('summary', 'Summary')], 'Type', required=True, default = 'detail')
    date_to = fields.Date('To Date', required=True, default=fields.Datetime.now)
    date_from = fields.Date('From Date',default=time.strftime('%Y-%m-01'))
    pos_install = fields.Boolean(compute = _get_pos_install, string = 'Pos Install')
    cost = fields.Boolean(u'Өртөг харах', default = False)
    ean = fields.Boolean('Show Barcode', default = False, invisible= True)
    lot = fields.Boolean('Show Serial',invisible= True)
    currently_cost = fields.Boolean('Currently Cost?')


    def _get_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return (user.allowed_warehouses and map(lambda x: x.id, user.allowed_warehouses)) or []
    #
    # _defaults = {
    #     'company_id': lambda obj, cr, uid, c: obj.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory.report'),
    #     'date_to': lambda *a: time.strftime('%Y-%m-%d'),
    #     'date_from': lambda *a: time.strftime('%Y-%m-01'),
    #     'income_expense': False,
    #     'sorting': 'default_code',
    #     'pos_install': _get_pos_install,
    #     'cost': False,
    #     'ean': True,
    #     # 'warehouse_ids': _get_warehouse,
    #     'type': 'detail'
    # }

    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids[0], context=context)
        extra_name = ''
        wnames = u''
        if form.income_expense:
            extra_name = u'Орлого зарлагын тайлан'
        if form.warehouse_ids:
            for w in form.warehouse_ids:
                wnames += w.name
                wnames += ','
        else:
            wnames = u'Бүгд'
        body = (u"Агуулахын нөөцийн тайлан (Эхлэх='%s', Дуусах='%s', Салбар='%s', '%s')") % \
          (form.date_from, form.date_to, wnames, extra_name)
        return body

    def get_print_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        data = {
            'ids': ids,
            'model': self._name,
            'form': {}
        }

        return self.pool['report'].get_action(cr, uid, [], 'l10n_mn_report_base.abstract_report_builder', data=data, context=context)

    def get_export_data(self,report_code):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        wiz = self.read()
        data, titles, row_span = self.prepare_report_data(wiz)
        wiz = wiz[0]
        warehouses = self.env['stock.warehouse'].browse(wiz['warehouse_ids'])
        widths = [2]
        if wiz['income_expense']:
            headers = [
                [u'№'],
                [None],
                [None]
            ]
            header_span = [((0, 0), (0, 2))]
            colx = 1
            if wiz['ean'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                headers[0] += [u'Бар код']
                headers[1] += [None]
                headers[2] += [None]
                widths += [5]
                header_span += [((colx, 0), (colx, 2))]
                colx += 1
            headers[0] += [u'Бараа материал']
            headers[1] += [None]
            headers[2] += [None]
            header_span += [((colx, 0), (colx, 2))]
            widths += [10]
            colx += 1
            if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                # Размер болгож өөрчлөв
                # headers[0] += [u'Х.нэгж']
                headers[0] += [u'Размер']
                headers[1] += [None]
                headers[2] += [None]
                header_span += [((colx, 0), (colx, 2))]
                widths += [3]
                colx += 1
            if wiz['cost']:
                if len(warehouses) > 1:
                    headers[0] += [u'НИЙТ', None, None, None, None, None, None, None, None, None, None, None, None]
                    headers[1] += [u'Эхний үлдэгдэл', None, None, u'Нэмэлт', None, None, u'Хасалт', None, None, u'Үнэ өөрчлөлт', u'Эцсийн үлдэгдэл', None, None]
                    headers[2] += [u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн', u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн',
                                   u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн', None, u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн']
                    header_span += [((colx, 0), (colx + 12, 0)), ((colx, 1), (colx + 2, 1)),
                                    ((colx + 3, 1), (colx + 5, 1)), ((colx + 6, 1), (colx + 8, 1)), ((colx + 9, 1), (colx + 9, 2)), ((colx + 10, 1), (colx + 12, 1))]
                    colx += 13
                    widths += [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
                for wh in warehouses:
                    headers[0] += [wh.name, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
                    headers[1] += [u'Худалдах үнэ', u'Эхний үлдэгдэл', None, None, u'Нэмэлт', None, None, u'Хасалт', None, None, u'Үнэ өөрчлөлт', u'Эцсийн үлдэгдэл', None, None]
                    headers[2] += [None, u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн', u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн',
                                   u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн', None, u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Өртөгийн дүн']
                    header_span += [((colx, 0), (colx + 13, 0)), ((colx, 1), (colx, 2)), ((colx + 1, 1), (colx + 3, 1)),
                                    ((colx + 4, 1), (colx + 6, 1)), ((colx + 7, 1), (colx + 9, 1)), ((colx + 10, 1), (colx + 10, 2)), ((colx + 11, 1), (colx + 13, 1))]
                    colx += 14
                    widths += [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
            else:
                if len(warehouses) > 1:
                    headers[0] += [u'НИЙТ', None, None, None, None, None, None, None, None]
                    headers[1] += [u'Эхний үлдэгдэл', None, u'Нэмэлт', None, u'Хасалт', None, u'Үнэ өөрчлөлт', u'Эцсийн үлдэгдэл', None]
                    headers[2] += [u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Тоо хэмжээ', u'Зарах үнийн дүн',
                                   u'Тоо хэмжээ', u'Зарах үнийн дүн', None, u'Тоо хэмжээ', u'Зарах үнийн дүн']
                    header_span += [((colx, 0), (colx + 8, 0)), ((colx, 1), (colx + 1, 1)), ((colx + 2, 1), (colx + 3, 1)), ((colx + 4, 1), (colx + 5, 1)),
                                    ((colx + 6, 1), (colx + 6, 2)), ((colx + 7, 1), (colx + 8, 1))]
                    colx += 9
                    widths += [4, 4, 4, 4, 4, 4, 4, 4, 4]
                for wh in warehouses:
                    headers[0] += [wh.name, None, None, None, None, None, None, None, None, None]
                    headers[1] += [u'Худалдах үнэ', u'Эхний үлдэгдэл', None, u'Нэмэлт', None, u'Хасалт', None, u'Үнэ өөрчлөлт', u'Эцсийн үлдэгдэл', None]
                    headers[2] += [None, u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Тоо хэмжээ', u'Зарах үнийн дүн',
                                   u'Тоо хэмжээ', u'Зарах үнийн дүн', None, u'Тоо хэмжээ', u'Зарах үнийн дүн']
                    header_span += [((colx, 0), (colx + 9, 0)), ((colx, 1), (colx, 2)), ((colx + 1, 1), (colx + 2, 1)), ((colx + 3, 1), (colx + 4, 1)),
                                    ((colx + 5, 1), (colx + 6, 1)), ((colx + 7, 1), (colx + 7, 2)), ((colx + 8, 1), (colx + 9, 1))]
                    colx += 10
                    widths += [4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
        else:
            headers = [
                [u'№'],
                [None]
            ]
            header_span = [((0, 0), (0, 1))]
            colx = 1
            if wiz['ean'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                headers[0] += [u'Бар код']
                headers[1] += [None]
                widths += [5]
                header_span += [((colx, 0), (colx, 1))]
                colx += 1
            headers[0] += [u'Бараа материал']
            headers[1] += [None]
            widths += [10]
            header_span += [((colx, 0), (colx, 1))]
            colx += 1
            if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                # Размер болгож өөрчлөв
                # headers[0] += [u'Х.нэгж']
                headers[0] += [u'Размер']
                headers[1] += [None]
                widths += [3]
                header_span += [((colx, 0), (colx, 1))]
                colx += 1
            if wiz['cost']:
                if len(warehouses) > 1:
                    total = u'НИЙТ'
                    tcolx = colx
                    if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                        headers[0] += [total]
                        headers[1] += [u'Серийн дугаар']
                        widths += [4]
                        colx += 1
                        total = None
                    headers[0] += [total, None, None]
                    headers[1] += [u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Нийт өртөг']
                    header_span += [((tcolx, 0), (colx + 2, 0))]
                    colx += 3
                    widths += [4, 4, 4]
                for wh in warehouses:
                    wname = wh.name
                    wcolx = colx
                    if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                        headers[0] += [wname]
                        headers[1] += [u'Серийн дугаар']
                        widths += [4]
                        colx += 1
                        wname = None
                    headers[0] += [wname, None, None, None, None]
                    headers[1] += [u'Худалдах үнэ', u'Тоо хэмжээ', u'Зарах үнийн дүн', u'Нэгж өртөг', u'Нийт өртөг']
                    header_span += [((wcolx, 0), (colx + 4, 0))]
                    colx += 5
                    widths += [4, 4, 4, 4, 4]
            else:
                if len(warehouses) > 1:
                    total = u'НИЙТ'
                    tcolx = colx
                    if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                        headers[0] += [total]
                        headers[1] += [u'Серийн дугаар']
                        widths += [4]
                        colx += 1
                        total = None
                    headers[0] += [total, None]
                    headers[1] += [u'Тоо хэмжээ', u'Зарах үнийн дүн']
                    header_span += [((tcolx, 0), (colx + 1, 0))]
                    colx += 2
                    widths += [5, 5]
                for wh in warehouses:
                    wname = wh.name
                    wcolx = colx
                    if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                        headers[0] += [wname]
                        headers[1] += [u'Серийн дугаар']
                        widths += [4]
                        colx += 1
                        wname = None
                    headers[0] += [wname, None, None]
                    headers[1] += [u'Худалдах үнэ', u'Тоо хэмжээ', u'Зарах үнийн дүн']
                    header_span += [((wcolx, 0), (colx + 2, 0))]
                    colx += 3
                    widths += [5, 5, 5]

        datas = {
            'title': u'Агуулахын нөөцийн тайлан',
            'headers': headers,
            'header_span': header_span,
            'row_span': row_span,
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas': datas}

    def prepare_report_data(self,wiz):
        wiz = wiz[0]
        context = self._context or {}
        location_obj = self.env['stock.location']
        product_obj = self.env['product.product']
        warehouses = self.env['stock.warehouse'].browse(wiz['warehouse_ids'])
        company = self.env['res.company'].browse(wiz['company_id'][0])
        attributes = self.env['product.attribute']
        titles = []
        data = []
        row_span = {}
        prices = {}
        total_dict = {}

        def to_rowspan(ix, iy):
            if row_span.has_key(ix[1]):
                row_span[ix[1]] += [[ix[0], iy[0], iy[1]]]
            else:
                row_span.update({ix[1]: [[ix[0], iy[0], iy[1]]]})

        if wiz['income_expense']:
            titles.append(u'Хугацаа : %s аас %s хүртэл' % (wiz['date_from'], wiz['date_to']))
            initial_date_where = " and m.date < '%s' " % (wiz['date_from'] + ' 00:00:00')
            total_dict = {'start_qty': 0,
                          'start_cost': 0, 'start_price': 0, 'start': 0,
                          'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                          'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                          'end_qty': 0, 'end_cost': 0, 'end_price': 0,
                          'whs': {}}
            data_dict = {}
            prod_ids = []
            wids = []
            where = ""
            select = ""
            join = ""
            groupby = ""
            parent_select = ""
            parent_groupby = ""
            if wiz['prod_categ_ids']:
                categ_ids = self.pool.get('product.category').search([('parent_id', 'child_of', wiz['prod_categ_ids'])], context=context)
                where += " AND pt.categ_id in (" + ','.join(map(str, categ_ids)) + ") "
            if wiz['product_ids']:
                where += " AND pp.id in (" + ','.join(map(str, wiz['product_ids'])) + ") "

            if wiz['partner_ids']:
                where += " AND pt.manufacturer in (" + ','.join(map(str, wiz['partner_ids'])) + ") "
            if wiz['grouping'] == 'manufacture':
                select = "rp.id AS group_id,rp.name AS gname, "
                join = " LEFT JOIN res_partner rp ON pt.manufacturer = rp.id "
                groupby = ",rp.id,rp.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            if wiz['grouping'] == 'category':
                select = "pc.id AS group_id,pc.name AS gname, "
                join = " LEFT JOIN product_category pc ON pt.categ_id = pc.id "
                groupby = ",pc.id,pc.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            if wiz['grouping'] == 'pos_categ':
                select = "pos.id AS group_id,pos.name AS gname, "
                join = " LEFT JOIN pos_category pos ON pt.pos_categ_id = pos.id "
                groupby = ",pos.id,pos.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            for wh in warehouses:
                ctx = context.copy()
                # if company.store_cost_per_warehouse:
                #     ctx.update({'warehouse': wh.id})
                wids.append(wh.id)
                locations = location_obj.search([('usage', '=', 'internal'),
                                                          ('location_id', 'child_of', [wh.view_location_id.id])])
                locations = tuple(locations.ids)
                if wh.id not in total_dict['whs']:
                    total_dict['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                # Тайлант хугацааны эхний үлдэгдэл
                self._cr.execute("SELECT myquery.product_id AS prod, " + parent_select + ""
                                "sum(myquery.q) AS q, sum(myquery.c) AS c, sum(myquery.price) AS l "
                            "FROM ( "
                           "(SELECT m.product_id, " + select + ""
                                "coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                "coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                "coalesce(sum(m.price_unit* (m.product_qty/u.factor*u2.factor)), 0) as price "
                           "FROM stock_move m "
                                "FULL JOIN product_product pp ON (pp.id=m.product_id) "
                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                "JOIN product_uom u2 ON (u2.id=pt.uom_id) " + join + ""
                           "WHERE m.state = 'done' " + where + " "
                                "AND m.location_id NOT IN %s AND m.location_dest_id IN %s "
                            + initial_date_where +
                           "GROUP BY m.product_id" + groupby + ") UNION "
                           "(SELECT m.product_id, " + select + ""
                                "-coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                "-coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                "-coalesce(sum(m.price_unit* (m.product_qty/u.factor*u2.factor)), 0) as price "
                           "FROM stock_move m "
                                "FULL JOIN product_product pp ON (pp.id=m.product_id) "
                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                "JOIN product_uom u2 ON (u2.id=pt.uom_id) " + join + ""
                           "WHERE m.state = 'done' " + where + " "
                                "AND m.location_id IN %s AND m.location_dest_id NOT IN %s "
                           + initial_date_where +
                           "GROUP BY m.product_id" + groupby + ") ) as myquery "
                           "GROUP BY myquery.product_id " + parent_groupby + ""
                                "having sum(myquery.q)::decimal(16,4) <> 0",
                        (locations, locations, locations, locations))
                fetched = self._cr.dictfetchall()
                if fetched:
                    for f in fetched:
#                         if wiz['currently_cost'] is True:
#                             standard_price_display = product_obj.price_get(cr, uid, f['prod'], 'standard_price', context=ctx)[f['prod']]
#                             f['c'] = f['q'] * standard_price_display
                        price = 0
                        if f['prod']:
                            product = product_obj.browse(f['prod'])
                            price = product.price_get('list_price')[f['prod']]
                        if f['prod'] not in prod_ids:
                            prod_ids.append(f['prod'])
                        if wiz['grouping']:
                            if f['group_id'] not in data_dict:
                                data_dict[f['group_id']] = {'name': f['gname'] or u'Тодорхойгүй',
                                                            'group_id': f['group_id'] or None,
                                                            'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                            'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                            'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                            'end_qty': 0, 'end_cost': 0, 'end_price': 0,
                                                            'lines': {}, 'whs': {}}
                            if wh.id not in data_dict[f['group_id']]['whs']:
                                data_dict[f['group_id']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                          'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                          'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                          'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                            if f['prod'] not in data_dict[f['group_id']]['lines']:
                                data_dict[f['group_id']]['lines'][f['prod']] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                                'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                                'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                                'end_qty': 0, 'end_cost': 0, 'end_price': 0, 'whs': {}}
                            if wh.id not in data_dict[f['group_id']]['lines'][f['prod']]['whs']:
                                data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                                              'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                                              'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                                              'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                            data_dict[f['group_id']]['start_qty'] += f['q']
                            data_dict[f['group_id']]['start_cost'] += f['c']
                            data_dict[f['group_id']]['start_price'] += f['l']
                            data_dict[f['group_id']]['start'] += f['q'] * price
                            data_dict[f['group_id']]['whs'][wh.id]['start_qty'] += f['q']
                            data_dict[f['group_id']]['whs'][wh.id]['start_cost'] += f['c']
                            data_dict[f['group_id']]['whs'][wh.id]['start_price'] += f['l']
                            data_dict[f['group_id']]['whs'][wh.id]['start'] += f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['start_qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['start_cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['start_price'] += f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['start_qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['start_cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['start_price'] += f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['start'] += f['q'] * price
                        else:
                            if f['prod'] not in data_dict:
                                data_dict[f['prod']] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                        'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                        'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                        'end_qty': 0, 'end_cost': 0, 'end_price': 0, 'whs': {}}
                            if wh.id not in data_dict[f['prod']]['whs']:
                                data_dict[f['prod']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                      'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                      'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                      'end_qty': 0, 'end_cost': 0, 'end_price': 0}

                            data_dict[f['prod']]['start_qty'] += f['q']
                            data_dict[f['prod']]['start_cost'] += f['c']
                            data_dict[f['prod']]['start_price'] += f['l']
                            data_dict[f['prod']]['start'] += f['q'] * price
                            data_dict[f['prod']]['whs'][wh.id]['start_qty'] += f['q']
                            data_dict[f['prod']]['whs'][wh.id]['start_cost'] += f['c']
                            data_dict[f['prod']]['whs'][wh.id]['start_price'] += f['l']
                            data_dict[f['prod']]['whs'][wh.id]['start'] += f['q'] * price
                        total_dict['start_qty'] += f['q']
                        total_dict['start_cost'] += f['c']
                        total_dict['start_price'] += f['l']
                        total_dict['start'] += f['q'] * price
                        total_dict['whs'][wh.id]['start_qty'] += f['q']
                        total_dict['whs'][wh.id]['start_cost'] += f['c']
                        total_dict['whs'][wh.id]['start_price'] += f['l']
                        total_dict['whs'][wh.id]['start'] += f['q'] * price
                # Тайлант хугацааны орлого
                self._cr.execute("(SELECT m.product_id AS prod, " + select + ""
                                "coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                "coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                "coalesce(sum(m.price_unit* (m.product_qty/u.factor*u2.factor)), 0) as l "
                           "FROM stock_move m "
                                "JOIN product_product pp ON (pp.id=m.product_id) "
                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                "JOIN product_uom u2 ON (u2.id=pt.uom_id) " + join +
                           "WHERE m.state = 'done' " + where + " "
                                "AND m.location_id NOT IN %s AND m.location_dest_id IN %s "
                                "AND m.date >= %s AND m.date <= %s "
                           "GROUP BY m.product_id" + groupby + ") UNION "
                           "(SELECT m.product_id AS prod, " + select + ""
                                "-coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                "-coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                "-coalesce(sum(m.price_unit* (m.product_qty/u.factor*u2.factor)), 0) as l "
                           "FROM stock_move m "
                                "JOIN product_product pp ON (pp.id=m.product_id) "
                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                "JOIN product_uom u2 on (u2.id=pt.uom_id) " + join +
                           "WHERE m.state = 'done' " + where + " "
                                "AND m.location_id IN %s AND m.location_dest_id NOT IN %s "
                                "AND m.date >= %s AND m.date <= %s "
                           "GROUP BY m.product_id " + groupby + " )",
                        (locations, locations, wiz['date_from'] + ' 00:00:00', wiz['date_to'] + ' 23:59:59',
                         locations, locations, wiz['date_from'] + ' 00:00:00', wiz['date_to'] + ' 23:59:59'))
                fetched = self._cr.dictfetchall()
                for f in fetched:
#                         if wiz['currently_cost'] is True:
#                             standard_price_display = product_obj.price_get(cr, uid, f['prod'], 'standard_price', context=ctx)[f['prod']]
#                             f['c'] = f['q'] * standard_price_display
                    price = 0
                    if f['prod']:
                        product = product_obj.browse(f['prod'])
                        price = product.price_get('list_price')[f['prod']]
                    if f['prod'] not in prod_ids:
                        prod_ids.append(f['prod'])
                    if wiz['grouping']:
                        if f['group_id'] not in data_dict:
                            data_dict[f['group_id']] = {'name': f['gname'] or u'Тодорхойгүй',
                                                        'group_id': f['group_id'] or None,
                                                        'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                        'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                        'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                        'end_qty': 0, 'end_cost': 0, 'end_price': 0,
                                                        'whs': {}, 'lines': {}}
                        if wh.id not in data_dict[f['group_id']]['whs']:
                            data_dict[f['group_id']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                      'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                      'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                      'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                        if f['prod'] not in data_dict[f['group_id']]['lines']:
                            data_dict[f['group_id']]['lines'][f['prod']] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                            'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                            'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                            'end_qty': 0, 'end_cost': 0, 'end_price': 0, 'whs': {}}
                        if wh.id not in data_dict[f['group_id']]['lines'][f['prod']]['whs']:
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                                          'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                                          'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                                          'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                        if f['q'] > 0:
                            data_dict[f['group_id']]['in_qty'] += f['q']
                            data_dict[f['group_id']]['in_cost'] += f['c']
                            data_dict[f['group_id']]['in_price'] += f['l']
                            data_dict[f['group_id']]['in'] += f['q'] * price
                            data_dict[f['group_id']]['whs'][wh.id]['in_qty'] += f['q']
                            data_dict[f['group_id']]['whs'][wh.id]['in_cost'] += f['c']
                            data_dict[f['group_id']]['whs'][wh.id]['in_price'] += f['l']
                            data_dict[f['group_id']]['whs'][wh.id]['in'] += f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['in_qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['in_cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['in_price'] += f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['in'] += f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['in_qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['in_cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['in_price'] += f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['in'] += f['q'] * price
                        else:
                            data_dict[f['group_id']]['out_qty'] += -f['q']
                            data_dict[f['group_id']]['out_cost'] += -f['c']
                            data_dict[f['group_id']]['out_price'] += -f['l']
                            data_dict[f['group_id']]['out'] += f['q'] * price
                            data_dict[f['group_id']]['whs'][wh.id]['out_qty'] += -f['q']
                            data_dict[f['group_id']]['whs'][wh.id]['out_cost'] += -f['c']
                            data_dict[f['group_id']]['whs'][wh.id]['out_price'] += -f['l']
                            data_dict[f['group_id']]['whs'][wh.id]['out'] += -f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['out_qty'] += -f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['out_cost'] += -f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['out_price'] += -f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['out'] += -f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['out_qty'] += -f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['out_cost'] += -f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['out_price'] += -f['l']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['out'] += -f['q'] * price
                    else:
                        if f['prod'] not in data_dict:
                            data_dict[f['prod']] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                    'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                    'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                    'end_qty': 0, 'end_cost': 0, 'end_price': 0, 'whs': {}}
                        if wh.id not in data_dict[f['prod']]['whs']:
                            data_dict[f['prod']]['whs'][wh.id] = {'start_qty': 0, 'start_cost': 0, 'start_price': 0, 'start': 0,
                                                                  'in_qty': 0, 'in_cost': 0, 'in_price': 0, 'in': 0,
                                                                  'out_qty': 0, 'out_cost': 0, 'out_price': 0, 'out': 0,
                                                                  'end_qty': 0, 'end_cost': 0, 'end_price': 0}
                        if f['q'] > 0:
                            data_dict[f['prod']]['in_qty'] += f['q']
                            data_dict[f['prod']]['in_cost'] += f['c']
                            data_dict[f['prod']]['in_price'] += f['l']
                            data_dict[f['prod']]['in'] += f['q'] * price
                            data_dict[f['prod']]['whs'][wh.id]['in_qty'] += f['q']
                            data_dict[f['prod']]['whs'][wh.id]['in_cost'] += f['c']
                            data_dict[f['prod']]['whs'][wh.id]['in_price'] += f['l']
                            data_dict[f['prod']]['whs'][wh.id]['in'] += f['q'] * price
                        else:
                            data_dict[f['prod']]['out_qty'] += -f['q']
                            data_dict[f['prod']]['out_cost'] += -f['c']
                            data_dict[f['prod']]['out_price'] += -f['l']
                            data_dict[f['prod']]['out'] += -f['q'] * price
                            data_dict[f['prod']]['whs'][wh.id]['out_qty'] += -f['q']
                            data_dict[f['prod']]['whs'][wh.id]['out_cost'] += -f['c']
                            data_dict[f['prod']]['whs'][wh.id]['out_price'] += -f['l']
                            data_dict[f['prod']]['whs'][wh.id]['out'] += -f['q'] * price
                    if f['q'] > 0:
                        total_dict['in_qty'] += f['q']
                        total_dict['in_cost'] += f['c']
                        total_dict['in_price'] += f['l']
                        total_dict['in'] += f['q'] * price
                        total_dict['whs'][wh.id]['in_qty'] += f['q']
                        total_dict['whs'][wh.id]['in_cost'] += f['c']
                        total_dict['whs'][wh.id]['in_price'] += f['l']
                        total_dict['whs'][wh.id]['in'] += f['q'] * price
                    else:
                        total_dict['out_qty'] += -f['q']
                        total_dict['out_cost'] += -f['c']
                        total_dict['out_price'] += -f['l']
                        total_dict['out'] += -f['q'] * price
                        total_dict['whs'][wh.id]['out_qty'] += -f['q']
                        total_dict['whs'][wh.id]['out_cost'] += -f['c']
                        total_dict['whs'][wh.id]['out_price'] += -f['l']
                        total_dict['whs'][wh.id]['out'] += -f['q'] * price
            change_dict = {'total': 0.0,
                           'whs': {},
                           'prods': {}}
            """Product Change Price"""
            # self._cr.execute("select d.warehouse_id,d.product_id,sum(d.amount) "
            #            "from product_price_history h "
            #            "join product_price_history_detail d on h.id = d.history_id "
            #            "where h.datetime >= %s and h.datetime <= %s and d.warehouse_id in %s "
            #            "and d.product_id in %s and h.price_type in ('list_price','retail_price') "
            #            "group by d.warehouse_id,d.product_id ",
            #            (wiz['date_from'] + ' 00:00:00', wiz['date_to'] + ' 23:59:59',
            #             tuple(wids), tuple(prod_ids)))
            # fetched = self._cr.fetchall()
            # for wid, prod, amt in fetched:
            #     if wid not in change_dict['whs']:
            #         change_dict['whs'][wid] = {'total': 0.0}
            #     if prod not in change_dict['whs'][wid]:
            #         change_dict['whs'][wid][prod] = 0.0
            #     if prod not in change_dict['prods']:
            #         change_dict['prods'][prod] = 0.0
            #     change_dict['total'] += amt
            #     change_dict['whs'][wid]['total'] += amt
            #     change_dict['whs'][wid][prod] += amt
            #     change_dict['prods'][prod] += amt
            number = 1
            warehouse_cost_dict = {}
            for wh in warehouses:
                ctx = context.copy()
                if company:
                    ctx.update({'warehouse': wh.id})
                if wiz['cost']:
                    warehouse_cost_dict[wh.id] = product_obj.price_get(prod_ids, ptype='standard_price')
                prices[wh.id] = product_obj.price_get(prod_ids)

            row = ['']
            if wiz['ean'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                row += ['']
            row += [u'<b><c>НИЙТ</c></b>']
            if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                row += ['']
            if len(warehouses) > 1:
                row += ['<b>%s</b>' % total_dict['start_qty']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['start_cost']]
                row += ['<b>%s</b>' % total_dict['start_price']]
                row += ['<b>%s</b>' % total_dict['in_qty']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['in_cost']]
                row += ['<b>%s</b>' % total_dict['in_price']]
                row += ['<b>%s</b>' % total_dict['out_qty']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['out_cost']]
                row += ['<b>%s</b>' % total_dict['out_price']]
                row += ['<b>%s</b>' % change_dict['total']]
                row += ['<b>%s</b>' % (total_dict['start_qty'] + total_dict['in_qty'] - total_dict['out_qty'])]
                if wiz['cost']:
                    row += ['<b>%s</b>' % (total_dict['start_cost'] + total_dict['in_cost'] - total_dict['out_cost'])]
                row += ['<b>%s</b>' % (total_dict['start'] + total_dict['in'] - total_dict['out'])]
            for wh in warehouses:
                if wh.id in total_dict['whs']:
                    if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                        row += ['']
                    row += ['<b>%s</b>' % total_dict['whs'][wh.id]['start_qty'],
                           '<b>%s</b>' % total_dict['whs'][wh.id]['start_price']]
                    if wiz['cost']:
                        row += ['<b>%s</b>' % total_dict['whs'][wh.id]['start_cost']]
                    row += ['<b>%s</b>' % total_dict['whs'][wh.id]['in_qty'],
                           '<b>%s</b>' % total_dict['whs'][wh.id]['in_price']]
                    if wiz['cost']:
                        row += ['<b>%s</b>' % total_dict['whs'][wh.id]['in_cost']]
                    row += ['<b>%s</b>' % total_dict['whs'][wh.id]['out_qty'],
                           '<b>%s</b>' % total_dict['whs'][wh.id]['out_price']]
                    if wiz['cost']:
                        row += ['<b>%s</b>' % total_dict['whs'][wh.id]['out_cost']]
                    if wh.id in change_dict['whs']:
                        row += ['<b>%s</b>' % change_dict['whs'][wh.id]['total']]
                    else:
                        row += ['<b>0.0</b>']
                    row += ['<b>%s</b>' % (total_dict['whs'][wh.id]['start_qty'] + total_dict['whs'][wh.id]['in_qty'] - total_dict['whs'][wh.id]['out_qty']),
                           '<b>%s</b>' % (total_dict['whs'][wh.id]['start'] + total_dict['whs'][wh.id]['in'] - total_dict['whs'][wh.id]['out'])]
                    if wiz['cost']:
                        row += ['<b>%s</b>' % (total_dict['whs'][wh.id]['start_cost'] + total_dict['whs'][wh.id]['in_cost'] - total_dict['whs'][wh.id]['out_cost'])]
                else:
                    if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                        row += ['']
                    row += ['<b>0.0</b>', '<b>0.0</b>']
                    if wiz['cost']:
                        row += ['<b>0.0</b>']
                    row += ['<b>0.0</b>', '<b>0.0</b>']
                    if wiz['cost']:
                        row += ['<b>0.0</b>']
                    row += ['<b>0.0</b>', '<b>0.0</b>']
                    if wiz['cost']:
                        row += ['<b>0.0</b>']
                    if wh.id in change_dict['whs']:
                        row += ['<b>%s</b>' % change_dict['whs'][wh.id]['total']]
                    else:
                        row += ['<b>0.0</b>']
                    row += ['<b>0.0</b>', '<b>0.0</b>']
                    if wiz['cost']:
                        row += ['<b>0.0</b>']
            data.append(row)
            if data_dict:
                if wiz['grouping']:
                    for val in sorted(data_dict.values()):
                        count = 1
                        row = ['<str>%s</str>' % number]
                        if wiz['type'] == 'detail' and wiz['ean']:
                            row += ['']
                        # row += ['']
                        row += ['<b>%s</b>' % (val['name'])]
                        if wiz['type'] == 'detail':
                            row += ['']
                        if len(warehouses) > 1:
                            if wiz['type'] == 'detail':
                                row += ['<b>%s</b>' % (val['start_qty']), '<b>%s</b>' % (val['start_price'])]
                                if wiz['cost']:
                                    row += ['<b>%s</b>' % (val['start_cost'])]
                                row += ['<b>%s</b>' % (val['in_qty']), '<b>%s</b>' % (val['in_price'])]
                                if wiz['cost']:
                                    row += ['<b>%s</b>' % (val['in_cost'])]
                                row += ['<b>%s</b>' % (val['out_qty']), '<b>%s</b>' % (val['out_price'])]
                                if wiz['cost']:
                                    row += ['<b>%s</b>' % (val['out_cost'])]
                                row += ['']
                                row += ['<b>%s</b>' % (val['start_qty'] + val['in_qty'] - val['out_qty']),
                                        '<b>%s</b>' % (val['start'] + val['in'] - val['out'])]
                                if wiz['cost']:
                                    row += ['<b>%s</b>' % (val['start_cost'] + val['in_cost'] - val['out_cost'])]
                            else:
                                row += [val['start_qty'], val['start_price']]
                                if wiz['cost']:
                                    row += [val['start_cost']]
                                row += [val['in_qty'], val['in_price']]
                                if wiz['cost']:
                                    row += [val['in_cost']]
                                row += [val['out_qty'], val['out_price']]
                                if wiz['cost']:
                                    row += [val['out_cost']]
                                row += ['']
                                row += [(val['start_qty'] + val['in_qty'] - val['out_qty']),
                                        (val['start'] + val['in'] - val['out'])]
                                if wiz['cost']:
                                    row += [(val['start_cost'] + val['in_cost'] - val['out_cost'])]
                        for wh in warehouses:
                            if wiz['type'] == 'detail':
                                row += ['']
                                if wh.id in val['whs']:
                                    row += ['<b>%s</b>' % (val['whs'][wh.id]['start_qty']),
                                            '<b>%s</b>' % (val['whs'][wh.id]['start_price'])]
                                    if wiz['cost']:
                                        row += ['<b>%s</b>' % (val['whs'][wh.id]['start_cost'])]
                                    row += ['<b>%s</b>' % (val['whs'][wh.id]['in_qty']),
                                            '<b>%s</b>' % (val['whs'][wh.id]['in_price'])]
                                    if wiz['cost']:
                                        row += ['<b>%s</b>' % (val['whs'][wh.id]['in_cost'])]
                                    row += ['<b>%s</b>' % (val['whs'][wh.id]['out_qty']),
                                            '<b>%s</b>' % (val['whs'][wh.id]['out_price'])]
                                    if wiz['cost']:
                                        row += ['<b>%s</b>' % (val['whs'][wh.id]['out_cost'])]
                                    row += ['']
                                    row += ['<b>%s</b>' % (val['whs'][wh.id]['start_qty'] + val['whs'][wh.id]['in_qty'] - val['whs'][wh.id]['out_qty']),
                                            '<b>%s</b>' % (val['whs'][wh.id]['start'] + val['whs'][wh.id]['in'] - val['whs'][wh.id]['out'])]
                                    if wiz['cost']:
                                        row += ['<b>%s</b>' % (val['whs'][wh.id]['start_cost'] + val['whs'][wh.id]['in_cost'] - val['whs'][wh.id]['out_cost'])]
                                else:
                                    row += ['<b>0.0</b>', '<b>0.0</b>']
                                    if wiz['cost']:
                                        row += ['<b>0.0</b>']
                                    row += ['<b>0.0</b>', '<b>0.0</b>']
                                    if wiz['cost']:
                                        row += ['<b>0.0</b>']
                                    row += ['<b>0.0</b>', '<b>0.0</b>']
                                    if wiz['cost']:
                                        row += ['<b>0.0</b>']
                                    row += ['']
                                    row += ['<b>0.0</b>',
                                            '<b>0.0</b>']
                                    if wiz['cost']:
                                        row += ['<b>0.0</b>']
                            else:
                                if wh.id in val['whs']:
                                    row += [val['whs'][wh.id]['start_qty'], val['whs'][wh.id]['start_price']]
                                    if wiz['cost']:
                                        row += [val['whs'][wh.id]['start_cost']]
                                    row += [val['whs'][wh.id]['in_qty'], val['whs'][wh.id]['in_price']]
                                    if wiz['cost']:
                                        row += [val['whs'][wh.id]['in_cost']]
                                    row += [val['whs'][wh.id]['out_qty'], val['whs'][wh.id]['out_price']]
                                    if wiz['cost']:
                                        row += [val['whs'][wh.id]['out_cost']]
                                    row += ['']
                                    row += [(val['whs'][wh.id]['start_qty'] + val['whs'][wh.id]['in_qty'] - val['whs'][wh.id]['out_qty']),
                                            (val['whs'][wh.id]['start'] + val['whs'][wh.id]['in'] - val['whs'][wh.id]['out'])]
                                    if wiz['cost']:
                                        row += [(val['whs'][wh.id]['start_cost'] + val['whs'][wh.id]['in_cost'] - val['whs'][wh.id]['out_cost'])]
                                else:
                                    row += [0.0, 0.0]
                                    if wiz['cost']:
                                        row += [0.0]
                                    row += [0.0, 0.0]
                                    if wiz['cost']:
                                        row += [0.0]
                                    row += [0.0, 0.0]
                                    if wiz['cost']:
                                        row += [0.0]
                                    row += ['']
                                    row += [0.0, 0.0]
                                    if wiz['cost']:
                                        row += [0.0]
                        data.append(row)
                        if wiz['type'] == 'detail':
                            prods = prod_ids
                            if wiz['grouping'] == 'manufacture' and val['group_id']:
                                prods = product_obj.search([('id', 'in', prod_ids), ('manufacturer', '=', val['group_id'])])
                            elif wiz['grouping'] == 'category':
                                prods = product_obj.search([('id', 'in', prod_ids), ('categ_id', '=', val['group_id'])])
                            elif wiz['grouping'] == 'pos_categ':
                                prods = product_obj.search([('id', 'in', prod_ids), ('pos_categ_id', '=', val['group_id'])])
                            pro = product_obj.browse(prod_ids)
                            prods = dict([(x['id'], x) for x in pro.read(['name', 'default_code', 'uom_id','attribute_value_ids'])])

                            for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):
                                row = ['<str>%s.%s</str>' % (number, count)]
                                if wiz['ean']:
                                    row += [u'<str>%s</str>' % (prod['ean13'] or '')]
                                temka = []
                                value = self.env['product.attribute.value'].browse(prod['attribute_value_ids'])
                                if value:
                                    for a in value:
                                        if len(a.name) <= 4:
                                            temka.append(a.name.encode("utf-8"))

                                row += [
                                    u'<space/><space/>%s [%s]' % ((prod['name'] or ''), (prod['default_code'] or '')),
                                    u'<c>%s</c>' % (str(temka).strip('[]'))]
                                if prod['id'] in val['lines']:
                                    line = val['lines'][prod['id']]
                                    if len(warehouses) > 1:
                                        row += [line['start_qty'], line['start_price']]
                                        if wiz['cost']:
                                            row += [line['start_cost']]
                                        row += [line['in_qty'], line['in_price']]
                                        if wiz['cost']:
                                            row += [line['in_cost']]
                                        row += [line['out_qty'], line['out_price']]
                                        if wiz['cost']:
                                            row += [line['out_cost']]
                                        if prod['id'] in change_dict['prods']:
                                            row += [change_dict['prods'][prod['id']]]
                                        else:
                                            row += ['']
                                        ent_qty = line['start_qty'] + line['in_qty'] - line['out_qty']
                                        row += [(line['start_qty'] + line['in_qty'] - line['out_qty']),
                                                (line['start'] + line['in'] - line['out'])]
                                        if wiz['cost']:
                                            row += [(line['start_cost'] + line['in_cost'] - line['out_cost'])]
                                    for wh in warehouses:
                                        price = 0.0
                                        if wh.id in prices and prod['id'] in prices[wh.id]:
                                            price = prices[wh.id][prod['id']]
                                        row += [price]
                                        if wh.id in line['whs']:
                                            row += [line['whs'][wh.id]['start_qty'], line['whs'][wh.id]['start_price']]
                                            if wiz['cost']:
                                                row += [line['whs'][wh.id]['start_cost']]
                                            row += [line['whs'][wh.id]['in_qty'], line['whs'][wh.id]['in_price']]
                                            if wiz['cost']:
                                                row += [line['whs'][wh.id]['in_cost']]
                                            row += [line['whs'][wh.id]['out_qty'], line['whs'][wh.id]['out_price']]
                                            if wiz['cost']:
                                                row += [line['whs'][wh.id]['out_cost']]
                                            if wh.id in change_dict['whs'] and prod['id'] in change_dict['whs'][wh.id]:
                                                row += [change_dict['whs'][wh.id][prod['id']]]
                                            else:
                                                row += [0.0]
                                            ent_qty = line['whs'][wh.id]['start_qty'] + line['whs'][wh.id]['in_qty'] - line['whs'][wh.id]['out_qty']
                                            row += [ent_qty, (price * ent_qty)]
                                            if wiz['cost']:
                                                row += [(line['whs'][wh.id]['start_cost'] + line['whs'][wh.id]['in_cost'] - line['whs'][wh.id]['out_cost'])]
                                        else:
                                            row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                            if wiz['cost']:
                                                row += [0.0, 0.0, 0.0]
                                            if wh.id in change_dict and prod['id'] in change_dict[wh.id]:
                                                row += [change_dict[wh.id][prod['id']]]
                                            else:
                                                row += [0.0]
                                            row += [0.0, 0.0]
                                            if wiz['cost']:
                                                row += [0.0]
                                else:
                                    if len(warehouses) > 1:
                                        row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                        if wiz['cost']:
                                            row += [0.0, 0.0, 0.0, 0.0]
                                    for wh in warehouses:
                                        row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                        if wiz['cost']:
                                            row += [0.0, 0.0, 0.0, 0.0]
                                data.append(row)
                                count += 1
                        number += 1
                else:
                    pro = product_obj.browse(prod_ids)
                    prods = dict([(x['id'], x) for x in pro.read(['name', 'default_code', 'uom_id','attribute_value_ids'])])
                    for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):
                        row = ['<str>%s</str>' % (number)]
                        if wiz['ean']:
                            row += [u'<str>%s</str>' % (prod['ean13'] or '')]
                        temka = []
                        value = self.env['product.attribute.value'].browse(prod['attribute_value_ids'])
                        if value:
                            for a in value:
                                if len(a.name) <= 4:
                                    temka.append(a.name.encode("utf-8"))

                        row += [u'<space/><space/>%s [%s]' % ((prod['name'] or ''), (prod['default_code'] or '')),
                            u'<c>%s</c>' % (str(temka).strip('[]'))]
                        if prod['id'] in data_dict:
                            line = data_dict[prod['id']]
                            if len(warehouses) > 1:
                                row += [line['start_qty'], line['start_price']]
                                if wiz['cost']:
                                    row += [line['start_cost']]
                                row += [line['in_qty'], line['in_price']]
                                if wiz['cost']:
                                    row += [line['in_cost']]
                                row += [line['out_qty'], line['out_price']]
                                if wiz['cost']:
                                    row += [line['out_cost']]
                                if prod['id'] in change_dict['prods']:
                                    row += [change_dict['prods'][prod['id']]]
                                else:
                                    row += ['']
                                row += [(line['start_qty'] + line['in_qty'] - line['out_qty']),
                                        (line['start'] + line['in'] - line['out'])]
                                if wiz['cost']:
                                    row += [(line['start_cost'] + line['in_cost'] - line['out_cost'])]
                            for wh in warehouses:
                                price = 0.0
                                if wh.id in prices and prod['id'] in prices[wh.id]:
                                    price = prices[wh.id][prod['id']]
                                row += [price]
                                if wh.id in line['whs']:
                                    row += [line['whs'][wh.id]['start_qty'], line['whs'][wh.id]['start_price']]
                                    if wiz['cost']:
                                        row += [line['whs'][wh.id]['start_cost']]
                                    row += [line['whs'][wh.id]['in_qty'], line['whs'][wh.id]['in_price']]
                                    if wiz['cost']:
                                        row += [line['whs'][wh.id]['in_cost']]
                                    row += [line['whs'][wh.id]['out_qty'], line['whs'][wh.id]['out_price']]
                                    if wiz['cost']:
                                        row += [line['whs'][wh.id]['out_cost']]
                                    if wh.id in change_dict['whs'] and prod['id'] in change_dict['whs'][wh.id]:
                                        row += [change_dict['whs'][wh.id][prod['id']]]
                                    else:
                                        row += [0.0]
                                    ent_qty = line['whs'][wh.id]['start_qty'] + line['whs'][wh.id]['in_qty'] - line['whs'][wh.id]['out_qty']
                                    row += [ent_qty, (price * ent_qty)]
                                    if wiz['cost']:
                                        row += [(line['whs'][wh.id]['start_cost'] + line['whs'][wh.id]['in_cost'] - line['whs'][wh.id]['out_cost'])]
                                else:
                                    row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                    if wiz['cost']:
                                        row += [0.0, 0.0, 0.0, 0.0]
                        else:
                            if len(warehouses) > 1:
                                row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                if wiz['cost']:
                                    row += [0.0, 0.0, 0.0, 0.0]
                            for wh in warehouses:
                                row += [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                                if wiz['cost']:
                                    row += [0.0, 0.0, 0.0, 0.0]
                        data.append(row)
                        number += 1

        else:  # Зөвхөн үлдэгдэл харуулах
            titles.append(u'Хугацаа: %s' % wiz['date_to'])
            initial_date_where = " and m.date <= '%s' " % (wiz['date_to'] + ' 23:59:59')
            total_dict = {'qty': 0,
                          'cost': 0,
                          'price': 0,
                          'whs': {}}
            data_dict = {}
            prod_ids = []
            where = ""
            select = ""
            join = ""
            groupby = ""
            parent_select = ""
            parent_groupby = ""
            if wiz['prod_categ_ids']:
                categ_ids = []
                cat = self.env['product.category'].search([('parent_id', 'child_of', wiz['prod_categ_ids'])])
                for i in cat:
                    categ_ids.append(i.id)
                where += " AND pt.categ_id in (" + ','.join(map(str, categ_ids)) + ") "
            if wiz['product_ids']:
                where += " AND pp.id in (" + ','.join(map(str, wiz['product_ids'])) + ") "
            if wiz['partner_ids']:
                where += " AND pt.manufacturer in (" + ','.join(map(str, wiz['partner_ids'])) + ") "
            if wiz['grouping'] == 'manufacture':
                select = "rp.id AS group_id,rp.name AS gname, "
                join = " LEFT JOIN res_partner rp ON pt.manufacturer = rp.id "
                groupby = ",rp.id,rp.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            if wiz['grouping'] == 'category':
                select = "pc.id AS group_id,pc.name AS gname, "
                join = " LEFT JOIN product_category pc ON pt.categ_id = pc.id "
                groupby = ",pc.id,pc.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            if wiz['grouping'] == 'pos_categ':
                select = "pos.id AS group_id,pos.name AS gname, "
                join = " LEFT JOIN pos_category pos ON pt.pos_categ_id = pos.id "
                groupby = ",pos.id,pos.name "
                parent_select = "myquery.group_id,myquery.gname, "
                parent_groupby = ",myquery.group_id,myquery.gname "
            for wh in warehouses:
                ctx = context.copy()
                # if company.store_cost_per_warehouse:
                #     ctx.update({'warehouse': wh.id})
                locations = location_obj.search([('usage', '=', 'internal'),
                                                          ('location_id', 'child_of', [wh.view_location_id.id])])
                location2 = []
                for i in locations:
                    location2.append(i.id)

                locations = location2
                locations = tuple(locations)
                if wh.id not in total_dict['whs']:
                    total_dict['whs'][wh.id] = {'qty': 0,
                                                'cost': 0,
                                                'price': 0}
                # Тайлант хугацааны эхний үлдэгдэл
                if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                    self._cr.execute("(SELECT m.product_id AS prod,  lot.id AS lot, lot.life_date AS ldate,lot.name AS lname, " + select + ""
                                    "coalesce(sum(m.product_qty),0) as q, "
                                    "coalesce(sum(m.cost),0) as c, "
                                    "coalesce(sum(m.price),0) as l "
                               "FROM report_stock_inventory m "
                                    "JOIN product_product pp ON (pp.id=m.product_id) "
                                    "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                    "LEFT JOIN stock_production_lot lot ON (m.prodlot_id=lot.id)" + join + ""
                               "WHERE m.location_id IN %s  " + where + " " + initial_date_where + 
                               "GROUP BY m.product_id,lot.id,lot.life_date,lot.name" + groupby + " having sum(m.product_qty)::decimal(16,4) <> 0) ",
                            (locations,))
                else:
                    self._cr.execute("SELECT myquery.product_id as prod, " + parent_select + ""
                                    "sum(myquery.q) as q, sum(myquery.c) as c, sum(myquery.price) as l "
                               "FROM ( "
                                        "(SELECT m.product_id, " + select + ""
                                                "coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                                "coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                                "coalesce(sum(pt.list_price*(m.product_qty/u.factor*u2.factor)),0) as price "
                                           "FROM stock_move m "
                                                "JOIN product_product pp ON (pp.id=m.product_id) "
                                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                                "JOIN product_uom u2 ON (u2.id=pt.uom_id) " + join + ""
                                           "WHERE m.state = 'done' " + where + " "
                                                "AND m.location_id NOT IN %s AND m.location_dest_id IN %s "
                                           + initial_date_where + 
                                           "GROUP BY m.product_id,m.price_unit " + groupby + " ) UNION "
                                       "(SELECT m.product_id, " + select + ""
                                                "-coalesce(sum(m.product_qty/u.factor*u2.factor),0) as q, "
                                                "-coalesce(sum(m.price_unit*m.product_qty),0) as c, "
                                                "-coalesce(sum(pt.list_price*(m.product_qty/u.factor*u2.factor)),0) as price "
                                           "FROM stock_move m "
                                                "JOIN product_product pp ON (pp.id=m.product_id) "
                                                "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                                "JOIN product_uom u ON (u.id=m.product_uom) "
                                                "JOIN product_uom u2 ON (u2.id=pt.uom_id) " + join + ""
                                           "WHERE m.state = 'done' " + where + " "
                                            "AND m.location_id in %s and m.location_dest_id not in %s "
                                               + initial_date_where + 
                                               "GROUP BY m.product_id, m.price_unit " + groupby + " ) ) as myquery GROUP BY myquery.product_id " + parent_groupby + ""
                                            "having sum(myquery.q)::decimal(16,4) <> 0 ", (locations, locations, locations, locations))

                fetched = self._cr.dictfetchall()
                # print'\n\n\n Temka \n\n\n', fetched
                for f in fetched:
                    # if wiz['currently_cost'] is True:
                    product_pro = product_obj.browse(f['prod'])
                    standard_price_display = product_pro.list_price
                    # print'\n\n\n Price \n\n\n', standard_price_display
                    f['c'] = f['q'] * standard_price_display
                    price = 0
                    if f['prod']:
                        product = product_obj.browse(f['prod'])
                        price = product.price_get('list_price')[f['prod']]
                    if f['prod'] not in prod_ids:
                        prod_ids.append(f['prod'])
                    if f['q'] != 0:
                        if wiz['grouping']:
                            if f['group_id'] not in data_dict:
                                data_dict[f['group_id']] = {'name': f['gname'] or u'Тодорхойгүй',
                                                            'group_id': f['group_id'] or None,
                                                            'qty': 0.0,
                                                            'cost': 0.0,
                                                            'price': 0.0,
                                                            'lines': {},
                                                            'whs': {}}
                            if wh.id not in data_dict[f['group_id']]['whs']:
                                data_dict[f['group_id']]['whs'][wh.id] = {'qty': 0.0,
                                                                          'cost': 0.0,
                                                                          'price': 0.0}
                            if f['prod'] not in data_dict[f['group_id']]['lines']:
                                data_dict[f['group_id']]['lines'][f['prod']] = {'qty': 0.0,
                                                                                'cost': 0.0,
                                                                                'price': 0.0,
                                                                                'lots': {},
                                                                                'whs': {}}
                            if wh.id not in data_dict[f['group_id']]['lines'][f['prod']]['whs']:
                                data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id] = {'qty': 0.0,
                                                                                              'cost': 0.0,
                                                                                              'price': 0.0,
                                                                                              'lots': {}}
                            if wiz['lot'] and wiz['type'] == 'detail':
                                lname = f['lname'] or u'Тодорхойгүй'
                                if f['ldate']:
                                    lname = '%s - (%s)' % (f['lname'] or u'Тодорхойгүй', f['ldate'])
                                if f['lot'] not in data_dict[f['group_id']]['lines'][f['prod']]['lots']:
                                    data_dict[f['group_id']]['lines'][f['prod']]['lots'][f['lot']] = {'name': lname,
                                                                                                      'qty': 0.0,
                                                                                                      'cost': 0.0,
                                                                                                      'price': 0.0}
                                if f['lot'] not in data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['lots']:
                                    data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['lots'][f['lot']] = {'name': lname,
                                                                                                                    'qty': 0.0,
                                                                                                                    'cost': 0.0,
                                                                                                                    'price': 0.0}
                                data_dict[f['group_id']]['lines'][f['prod']]['lots'][f['lot']]['qty'] += f['q']
                                data_dict[f['group_id']]['lines'][f['prod']]['lots'][f['lot']]['cost'] += f['c']
                                data_dict[f['group_id']]['lines'][f['prod']]['lots'][f['lot']]['price'] += f['q'] * price
                                data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['lots'][f['lot']]['qty'] += f['q']
                                data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['lots'][f['lot']]['cost'] += f['c']
                                data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['lots'][f['lot']]['price'] += f['q'] * price
                            data_dict[f['group_id']]['qty'] += f['q']
                            data_dict[f['group_id']]['cost'] += f['c']
                            data_dict[f['group_id']]['price'] += f['l']
                            data_dict[f['group_id']]['whs'][wh.id]['qty'] += f['q']
                            data_dict[f['group_id']]['whs'][wh.id]['cost'] += f['c']
                            data_dict[f['group_id']]['whs'][wh.id]['price'] += f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['price'] += f['q'] * price
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['qty'] += f['q']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['cost'] += f['c']
                            data_dict[f['group_id']]['lines'][f['prod']]['whs'][wh.id]['price'] += f['q'] * price
                        else:
                            if f['prod'] not in data_dict:
                                data_dict[f['prod']] = {'qty': 0.0,
                                                        'cost': 0.0,
                                                        'price': 0.0,
                                                        'lots': {},
                                                        'whs': {}}
                            if wh.id not in data_dict[f['prod']]['whs']:
                                data_dict[f['prod']]['whs'][wh.id] = {'qty': 0.0,
                                                                      'cost': 0.0,
                                                                      'price': 0.0,
                                                                      'lots': {}}
                            if wiz['lot']:
                                lname = f['lname'] or u'Тодорхойгүй'
                                if f['ldate']:
                                    lname = '%s - (%s)' % (f['lname'] or u'Тодорхойгүй', f['ldate'])
                                if f['lot'] not in data_dict[f['prod']]['lots']:
                                    data_dict[f['prod']]['lots'][f['lot']] = {'name': lname,
                                                                              'qty': 0.0,
                                                                              'cost': 0.0,
                                                                              'price': 0.0}
                                if f['lot'] not in data_dict[f['prod']]['whs'][wh.id]['lots']:
                                    data_dict[f['prod']]['whs'][wh.id]['lots'][f['lot']] = {'name': lname,
                                                                                            'qty': 0.0,
                                                                                            'cost': 0.0,
                                                                                            'price': 0.0}
                                data_dict[f['prod']]['lots'][f['lot']]['qty'] += f['q']
                                data_dict[f['prod']]['lots'][f['lot']]['cost'] += f['c']
                                data_dict[f['prod']]['lots'][f['lot']]['price'] += f['q'] * price
                                data_dict[f['prod']]['whs'][wh.id]['lots'][f['lot']]['qty'] += f['q']
                                data_dict[f['prod']]['whs'][wh.id]['lots'][f['lot']]['cost'] += f['c']
                                data_dict[f['prod']]['whs'][wh.id]['lots'][f['lot']]['price'] += f['q'] * price
                            data_dict[f['prod']]['qty'] += f['q']
                            data_dict[f['prod']]['cost'] += f['c']
                            data_dict[f['prod']]['price'] += f['q'] * price
                            data_dict[f['prod']]['whs'][wh.id]['qty'] += f['q']
                            data_dict[f['prod']]['whs'][wh.id]['cost'] += f['c']
                            data_dict[f['prod']]['whs'][wh.id]['price'] += f['q'] * price
                        total_dict['qty'] += f['q']
                        total_dict['cost'] += f['c']
                        total_dict['price'] += f['q'] * price
                        total_dict['whs'][wh.id]['qty'] += f['q']
                        total_dict['whs'][wh.id]['cost'] += f['c']
                        total_dict['whs'][wh.id]['price'] += f['q'] * price

            number = 1
            warehouse_cost_dict = {}
            # for wh in warehouses:
            #     ctx = context.copy()
            #     # if company.store_cost_per_warehouse:
            #     #     ctx.update({'warehouse': wh.id})
            #     if wiz['cost']:
            #         warehouse_cost_dict[wh.id] = product_obj.price_get(prod_ids, ptype='standard_price')
            #     product = product_obj.browse(f['prod'])
            #     prices[wh.id] = product.price_get('list_price')
            row = ['']
            if wiz['ean'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                row += ['']
            row += [u'<b><c>НИЙТ</c></b>']
            if (wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']:
                row += ['']
            if len(warehouses) > 1:
                if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                    row += ['']
                row += ['<b>%s</b>' % total_dict['qty']]
                if wiz['cost']:
                    row += ['<b>%s</b>' % total_dict['cost']]
                row += ['<b>%s</b>' % total_dict['price']]
            for wh in warehouses:
                if wiz['lot'] and ((wiz['grouping'] and wiz['type'] == 'detail') or not wiz['grouping']):
                    row += ['']
                if wh.id in total_dict['whs']:
                    row += ['', '<b>%s</b>' % total_dict['whs'][wh.id]['qty'],
                            '<b>%s</b>' % total_dict['whs'][wh.id]['price']]
                    if wiz['cost']:
                        row += ['', '<b>%s</b>' % total_dict['whs'][wh.id]['cost']]
                else:
                    row += ['', '<b>0.0</b>', '<b>0.0</b>']
                    if wiz['cost']:
                        row += ['', '<b>0.0</b>']
            data.append(row)
            rowx = 1
            if data_dict:
                if wiz['grouping']:
                    for val in sorted(data_dict.values(), key=itemgetter('name')):
                        count = 1
                        row = ['<str>%s</str>' % number]
                        if wiz['type'] == 'detail':
                            if wiz['ean']:
                                row += ['']
                            row += [u'<b>%s</b>' % (val['name']), '']
                        else:
                            row += [u'%s' % (val['name'])]
                        if len(warehouses) > 1:
                            if wiz['lot']:
                                row += ['']
                            row += ['<b>%s</b>' % (val['qty'])]
                            if wiz['cost']:
                                row += ['<b>%s</b>' % (val['cost'])]
                            row += ['<b>%s</b>' % (val['price'])]
                        for wh in warehouses:
                            if wh.id in val['whs']:
                                if wiz['type'] == 'detail':
                                    if wiz['lot']:
                                        row += ['']
                                    row += ['', '<b>%s</b>' % (val['whs'][wh.id]['qty']),
                                            '<b>%s</b>' % (val['whs'][wh.id]['price'])]
                                    if wiz['cost']:
                                        row += ['', '<b>%s</b>' % (val['whs'][wh.id]['cost'])]
                                else:
                                    row += ['', val['whs'][wh.id]['qty'], val['whs'][wh.id]['price']]
                                    if wiz['cost']:
                                        row += ['', val['whs'][wh.id]['cost']]
                            else:
                                if wiz['type'] == 'detail':
                                    if wiz['lot']:
                                        row += ['']
                                    row += ['', '<b>0.0</b>', '<b>0.0</b>']
                                    if wiz['cost']:
                                        row += ['', '<b>0.0</b>']
                                else:
                                    row += ['', 0.0, 0.0]
                                    if wiz['cost']:
                                        row += ['', 0.0]
                        data.append(row)
                        rowx += 1
                        if wiz['type'] == 'detail':
                            row = []
                            prowx = 0
                            prods = prod_ids
                            if wiz['grouping'] == 'manufacture':
                                prods = product_obj.search([('id', 'in', prod_ids), ('manufacturer', '=', val['group_id'])])
                            elif wiz['grouping'] == 'category':
                                prods = product_obj.search([('id', 'in', prod_ids), ('categ_id', '=', val['group_id'])])
                            else:
                                prods = product_obj.search([('id', 'in', prod_ids), ('pos_categ_id', '=', val['group_id'])])
                            prods = dict([(x['id'], x) for x in prods.read(['ean13', 'name', 'default_code', 'uom_id', 'standard_price','attribute_value_ids'])])
                            for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):
                                row.append(['<str>%s.%s</str>' % (number, count)])
                                temka=[]
                                if wiz['ean']:
                                    row[prowx] += [u'<str>%s</str>' % (prod['ean13'] or '')]
                                #Агуулахын нөөцийн тайлан дээр размер гаргах код тухайн аттрибутыг хэвлэх
                                value = self.env['product.attribute.value'].browse(prod['attribute_value_ids'])
                                if value:
                                    for a in value:
                                        if len(a.name) <= 4:
                                            temka.append(a.name.encode("utf-8"))
                                row[prowx] += [u'<space/><space/>%s [%s]' % ((prod['name'] or ''), (prod['default_code'] or '')),
                                               u'<c>%s</c>' % (str(temka).strip('[]'))]
                                #         Хэмжих нэгж хэрэггүй барааны шинж харна гэсэн болохоор доорх мөрийг коммент болгож өөрчлөлт хийв
                                # row[prowx] += [u'<space/><space/>%s [%s] [%s]' % ((prod['name'] or ''), (prod['default_code'] or ''), (str(temka).strip('[]'))),
                                #                u'<c>%s</c>' % (prod['uom_id'][1])]

                                if prod['id'] in val['lines']:
                                    line = val['lines'][prod['id']]
                                    colx = 1
                                    if len(line['lots']) > 1 and wiz['lot']:
                                        for i in range(len(line['lots']) - 1):
                                            if wiz['ean']:
                                                row.append([None, None, None, None])
                                            else:
                                                row.append([None, None, None])
                                        to_rowspan((0, rowx), (0, rowx + len(line['lots']) - 1))
                                        if wiz['ean']:
                                            to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                            colx += 1
                                        to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                        to_rowspan((colx + 1, rowx), (colx + 1, rowx + len(line['lots']) - 1))
                                        colx += 2
                                    if len(warehouses) > 1:
                                        if wiz['lot']:
                                            lrow = prowx
                                            colx += 3
                                            for l in sorted(line['lots'].values(), key=itemgetter('name')):
                                                row[lrow] += ['<str>%s</str>' % l['name'], '<b>%s</b>' % l['qty'],
                                                              '<b>%s</b>' % l['price']]
                                                if wiz['cost']:
                                                    row[lrow] += ['<b>%s</b>' % l['cost']]
                                                lrow += 1
                                            if wiz['cost']:
                                                colx += 1
                                        else:
                                            row[prowx] += ['<b>%s</b>' % line['qty'], '<b>%s</b>' % line['price']]
                                            colx += 2
                                            if wiz['cost']:
                                                row[prowx] += ['<b>%s</b>' % line['cost']]
                                                colx += 1
                                    for wh in warehouses:
                                        price = 0.0
                                        cost = prod['standard_price'] or 0.0
                                        if wh.id in prices and prod['id'] in prices[wh.id]:
                                            price = prices[wh.id][prod['id']]
                                        if wh.id in line['whs']:
                                            if wiz['lot']:
                                                lrow = prowx
                                                for l in sorted(line['whs'][wh.id]['lots'].values(), key=itemgetter('name')):
                                                    row[lrow] += ['<str>%s</str>' % l['name'], price, l['qty'], l['price']]
                                                    if l['qty'] > 0 and l['cost'] > 0:
                                                        cost = round(float(l['cost']) / float(l['qty']), 2)
                                                    if wiz['cost']:
                                                        row[lrow] += [cost, l['cost']]
                                                    lrow += 1
                                                if len(line['whs'][wh.id]['lots']) < len(line['lots']):
                                                    for i in range(len(line['lots']) - len(line['whs'][wh.id]['lots'])):
                                                        row[lrow] += [None, None, None, None]
                                                        if wiz['cost']:
                                                            row[lrow] += [None, None]
                                                        lrow += 1
                                                    to_rowspan((colx, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx, lrow - 1))
                                                    to_rowspan((colx + 1, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 1, lrow - 1))
                                                    to_rowspan((colx + 2, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 2, lrow - 1))
                                                    to_rowspan((colx + 3, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 3, lrow - 1))
                                                    if wiz['cost']:
                                                        to_rowspan((colx + 4, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots'])))), (colx + 4, lrow - 1)
                                                        to_rowspan((colx + 5, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots'])))), (colx + 5, lrow - 1)
                                                colx += 4
                                                if wiz['cost']:
                                                    colx += 2
                                            else:
                                                if line['whs'][wh.id]['qty'] > 0 and line['whs'][wh.id]['cost'] > 0:
                                                    cost = round(float(line['whs'][wh.id]['cost']) / float(line['whs'][wh.id]['qty']), 2)
                                                row[prowx] += [price, line['whs'][wh.id]['qty'], line['whs'][wh.id]['price']]
                                                if wiz['cost']:
                                                    row[prowx] += [cost, line['whs'][wh.id]['cost']]
                                        else:
                                            if len(line['lots']) > 1 and wiz['lot']:
                                                to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                                to_rowspan((colx + 1, rowx), (colx + 1, rowx + len(line['lots']) - 1))
                                                to_rowspan((colx + 2, rowx), (colx + 2, rowx + len(line['lots']) - 1))
                                                to_rowspan((colx + 3, rowx), (colx + 3, rowx + len(line['lots']) - 1))
                                                if wiz['cost']:
                                                    to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                                    to_rowspan((colx + 1, rowx), (colx + 1, rowx + len(line['lots']) - 1))
                                                for i in range(len(val['lots']) - 1):
                                                    row[prowx + i] += [None, None, None, None]
                                                    if wiz['cost']:
                                                        row[prowx + i] += [None, None]
                                            if wiz['lot']:
                                                row[prowx] += ['']
                                                colx += 1
                                            row[prowx] += [price, 0.0, 0.0]
                                            colx += 3
                                            if wiz['cost']:
                                                row[prowx] += [cost, 0.0]
                                                colx += 2
                                    if wiz['lot'] and len(line['lots']) > 1:
                                        rowx += len(line['lots'])
                                        prowx += len(line['lots'])
                                    else:
                                        rowx += 1
                                        prowx += 1
                                else:
                                    if len(warehouses) > 1:
                                        if wiz['lot']:
                                            row[prowx] += ['']
                                        row[prowx] += ['<b>0.0</b>', '<b>0.0</b>']
                                        if wiz['cost']:
                                            row[prowx] += ['<b>0.0</b>']
                                    for wh in warehouses:
                                        if wiz['lot']:
                                            row[prowx] += ['']
                                        row[prowx] += [0.0, 0.0, 0.0]
                                        if wiz['cost']:
                                            row[prowx] += [0.0, 0.0]
                                    rowx += 1
                                    prowx += 1
                                count += 1
                            data += row
                        number += 1
                else:
                    row = []
                    rrowx = 0
                    #I edited here =)
                    prodd = product_obj.browse(prod_ids)
                    prods = dict([(x['id'], x) for x in prodd.read(['ean13', 'name', 'default_code', 'uom_id', 'standard_price','attribute_value_ids'])])
                    for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):
                        temka=[]
                        if prod['id'] == 1951:
                            aa = True
                        row.append(['<str>%s</str>' % (number)])
                        if wiz['ean']:
                            row[rrowx] += [u'<str>%s</str>' % (prod['ean13'] or '')]
                        value = self.env['product.attribute.value'].browse(prod['attribute_value_ids'])
                        if value:
                            for a in value:
                                if len(a.name) <= 4:
                                    temka.append(a.name.encode("utf-8"))
                        #         Хэмжих нэгж хэрэггүй барааны шинж харна гэсэн болохоор доорх мөрийг коммент болгож өөрчлөлт хийв
                        # row[rrowx] += [u'<space/><space/>%s [%s] [%s]' % ( (prod['name'] or ''),(prod['default_code'] or ''),(str(temka).strip('[]'))),
                                # u'<c>%s</c>' % (prod['uom_id'][1])]
                        row[rrowx] += [u'<space/><space/>%s [%s]' % (
                        (prod['name'] or ''), (prod['default_code'] or '')),
                                       u'<c>%s</c>' % (str(temka).strip('[]'))]

                        if prod['id'] in data_dict:
                            line = data_dict[prod['id']]
                            colx = 1
                            if len(line['lots']) > 1 and wiz['lot']:
                                for i in range(len(line['lots']) - 1):
                                    if wiz['ean']:
                                        row.append([None, None, None, None])
                                    else:
                                        row.append([None, None, None])
                                to_rowspan((0, rowx), (0, rowx + len(line['lots']) - 1))
                                if wiz['ean']:
                                    to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                    colx += 1
                                to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                to_rowspan((colx + 1, rowx), (colx + 1, rowx + len(line['lots']) - 1))
                                colx += 2
                            if len(warehouses) > 1:
                                if wiz['lot']:
                                    lrow = rrowx
                                    for l in sorted(line['lots'].values(), key=itemgetter('name')):
                                        row[lrow] += ['<str>%s</str>' % l['name'], '<b>%s</b>' % l['qty'],
                                                      '<b>%s</b>' % l['price']]
                                        if wiz['cost']:
                                            row[lrow] += ['<b>%s</b>' % l['cost']]
                                        lrow += 1
                                    colx += 3
                                    if wiz['cost']:
                                        colx += 1
                                else:
                                    row[rrowx] += ['<b>%s</b>' % line['qty'], '<b>%s</b>' % line['price']]
                                    colx += 2
                                    if wiz['cost']:
                                        row[rrowx] += ['<b>%s</b>' % line['cost']]
                                        colx += 1
                            for wh in warehouses:
                                price = 0.0
                                cost = prod['standard_price'] or 0.0
                                if wh.id in prices and prod['id'] in prices[wh.id]:
                                    price = prices[wh.id][prod['id']]
                                if wh.id in line['whs']:
                                    if wiz['lot']:
                                        lrow = rrowx
                                        for l in sorted(line['whs'][wh.id]['lots'].values(), key=itemgetter('name')):
                                            row[lrow] += ['<str>%s</str>' % l['name'], price, l['qty'], l['price']]
                                            if l['qty'] > 0 and l['cost'] > 0:
                                                cost = round(float(l['cost']) / float(l['qty']), 2)
                                            if wiz['cost']:
                                                row[lrow] += [cost, l['cost']]
                                            lrow += 1
                                        if len(line['whs'][wh.id]['lots']) < len(line['lots']):
                                            for i in range(len(line['lots']) - len(line['whs'][wh.id]['lots'])):
                                                row[lrow] += [None, None, None, None]
                                                if wiz['cost']:
                                                    row[lrow] += [None, None]
                                                lrow += 1
                                            to_rowspan((colx, (rowx - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx, lrow - 1))
                                            to_rowspan((colx + 1, (rowx - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 1, lrow - 1))
                                            to_rowspan((colx + 2, (rowx - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 2, lrow - 1))
                                            to_rowspan((colx + 3, (rowx - len(line['lots']) - len(line['whs'][wh.id]['lots']))), (colx + 3, lrow - 1))
                                            if wiz['cost']:
                                                to_rowspan((colx + 4, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots'])))), (colx + 4, lrow - 1)
                                                to_rowspan((colx + 5, (lrow - 1 - len(line['lots']) - len(line['whs'][wh.id]['lots'])))), (colx + 5, lrow - 1)
                                        colx += 4
                                        if wiz['cost']:
                                            colx += 2
                                    else:
                                        if line['whs'][wh.id]['qty'] > 0 and line['whs'][wh.id]['cost'] > 0:
                                            cost = round(float(line['whs'][wh.id]['cost']) / float(line['whs'][wh.id]['qty']), 2)
                                        row[rrowx] += [price, line['whs'][wh.id]['qty'], line['whs'][wh.id]['price']]
                                        colx += 3
                                        if wiz['cost']:
                                            row[rrowx] += [cost, line['whs'][wh.id]['cost']]
                                            colx += 2
                                else:
                                    if len(line['lots']) > 1 and wiz['lot']:
                                        to_rowspan((colx, rowx), (colx, rowx + len(line['lots']) - 1))
                                        to_rowspan((colx + 1, rowx), (colx + 1, rowx + len(line['lots']) - 1))
                                        to_rowspan((colx + 2, rowx), (colx + 2, rowx + len(line['lots']) - 1))
                                        to_rowspan((colx + 3, rowx), (colx + 3, rowx + len(line['lots']) - 1))
                                        if wiz['cost']:
                                            to_rowspan((colx + 4, rowx), (colx + 4, rowx + len(line['lots']) - 1))
                                            to_rowspan((colx + 5, rowx), (colx + 5, rowx + len(line['lots']) - 1))
                                        for i in range(len(line['lots']) - 1):
                                            row[rrowx + i + 1] += [None, None, None, None]
                                            if wiz['cost']:
                                                row[rrowx + i + 1] += [None, None]
                                    if wiz['lot']:
                                        row[rrowx] += ['']
                                        colx += 1
                                    row[rrowx] += [price, 0.0, 0.0]
                                    colx += 3
                                    if wiz['cost']:
                                        row[rrowx] += [cost, 0.0]
                                        colx += 2
                            if wiz['lot'] and len(line['lots']) > 1:
                                rowx += len(line['lots'])
                                rrowx += len(line['lots'])
                            else:
                                rowx += 1
                                rrowx += 1
                        else:
                            if len(warehouses) > 1:
                                if wiz['lot']:
                                    row[rrowx] += ['']
                                row[rrowx] += ['<b>0.0</b>', '<b>0.0</b>']
                                if wiz['cost']:
                                    row[rrowx] += ['<b>0.0</b>']
                            for wh in warehouses:
                                if wiz['lot']:
                                    row[rrowx] += ['']
                                row[rrowx] += [0.0, 0.0, 0.0]
                                if wiz['cost']:
                                    row[rrowx] += [0.0, 0.0]
                            rowx += 1
                            rrowx += 1
                        number += 1
                    data += row
        return data, titles, row_span
