# -*- coding: utf-8 -*-
from itertools import groupby
from datetime import datetime, timedelta
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from collections import Counter
import odoo.addons.decimal_precision as dp
from __builtin__ import xrange
import xlwt
from StringIO import StringIO
import base64
from datetime import datetime, timedelta

style_title = xlwt.easyxf('font: bold 1, name Tahoma, height 160;'
                          'align: vertical center, horizontal center, wrap on;'
                          'borders: left thin, right thin, top thin, bottom thin;'
                          'pattern: pattern solid, pattern_fore_colour gray25, pattern_back_colour black;')
style_filter = xlwt.easyxf('font: bold 1, name Tahoma, height 220;'
                          'align: vertical center, horizontal center, wrap on;')
style_footer = xlwt.easyxf('font: bold 1, name Tahoma, height 160;'
                          'align: vertical center, horizontal center, wrap on;')
base_style = xlwt.easyxf('align: wrap yes')

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    real_warehouse = fields.Boolean(string = "Бодит агуулах", default =False)


class ProductProduct(models.Model):
    _inherit = "product.product"

    suggestion_line_sid = fields.Many2one('suggestion.order.line',string = "Suggestion line sid")
    suggestion_line_bid = fields.Many2one('suggestion.order.line',string = "Suggestion line bid")

class SuggestionOrderLineLine(models.Model):
    _name = "suggestion.order.line.line"
    _order = 'number desc'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.warehouse_id.name, rec.product_id.name + ': ' + str(rec.qty)))
        return res

    def ready_order(self):
        stock_move = []
        qty = 0
        for item in self:
            if self.picking_id:
                raise UserError(_(
                    'Stock Picking is already created!! \n Check!'))
            else:
                picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', item.warehouse_id.id),
                                                                      ('code', '=', 'internal')], limit=1)
                stock_move.append((0, 0, {'product_id': item.product_id.id,
                                          'product_uom_qty': 1,
                                          'state': 'draft',
                                          'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                                          'procure_method': 'make_to_stock',
                                          'location_dest_id': item.warehouse_id.lot_stock_id.id,
                                          'location_id': item.line_id.warehouse_id.lot_stock_id.id,
                                          'company_id': 1,
                                          'date_expected': datetime.now(),
                                          'date': datetime.now(),
                                          'name': item.product_id.product_tmpl_id.name,
                                          'scrapped': False,
                                          }))
                vals={
                    'location_id':item.warehouse_id.lot_stock_id.id,
                    'picking_type_id':picking_type.id,
                    'move_type':'direct',
                    'company_id':1,
                    'location_dest_id':item.line_id.warehouse_id.lot_stock_id.id,
                    'date': datetime.now(),
                    'note':u'Санал болголтын функционалаас үүсэв',
                    'origin':u'Санал болголтын функционалаас үүсэв',
                    'move_lines': stock_move,
                }
                new_picking = self.env['stock.picking'].create(vals)
                wiz_act = new_picking.action_confirm()
                wiz_act = new_picking.force_assign()
                self.update({'picking_id':new_picking.id})

    line_id = fields.Many2one('suggestion.order.line', 'Suggestion Line')
    warehouse_id = fields.Many2one('stock.warehouse', string='Салбар',
                                   change_default=True, ondelete='restrict')
    number = fields.Integer('Rank')
    product_id = fields.Many2one('product.product', string = 'Бараа')
    picking_id = fields.Many2one('stock.picking', string = 'Барааны хөдөлгөөн')
    qty = fields.Float('Qty')

class SuggestionOrderLine(models.Model):
    _name = "suggestion.order.line"

    @api.depends('product_id', 'warehouse_id')
    def _qty_available(self):
        product_product = self.env['product.product'].search([('product_tmpl_id', '=', self.product_id.id)])
        start_date = datetime.strptime(self.suggestion_id.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.suggestion_id.end_date, '%Y-%m-%d').date()
        remainder_qty = 0.0
        for m in self:
            for f in product_product:
                self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                 "where date <= %s "
                                 "and location_id = %s and product_id = %s and state = 'done'",
                                 (str(end_date) + ' 23:59:59', m.warehouse_id.lot_stock_id.id,
                                  f.id))
                fetched = self._cr.dictfetchall()
                if fetched:
                    for k in fetched:
                        if k['product_qty'] is None:
                            qty = 0.0
                        else:
                            qty = k['product_qty']
                self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                 "where date <= %s "
                                 "and location_dest_id = %s and product_id = %s and state = 'done'",
                                 (str(end_date) + ' 23:59:59', m.warehouse_id.lot_stock_id.id, f.id))
                in_moves = self._cr.dictfetchall()
                if in_moves:
                    for i in in_moves:
                        if i['product_qty'] is None:
                            qty2 = 0.0
                        else:
                            qty2 = i['product_qty']
                remainder = qty2 - qty
                remainder_qty += remainder
        self.remaining_qty = remainder_qty
        return self.remaining_qty

    @api.one
    @api.depends('product_id')
    def _compute_product_ids(self):
        warehouses = self.env['stock.warehouse'].search([('id', '<>', self.warehouse_id.id)])
        start_date = datetime.strptime(self.suggestion_id.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.suggestion_id.end_date, '%Y-%m-%d').date()
        # obj = self.env['suggestion.order.line.product.product.rel']
        product_ids = []
        if self.product_id:
           self._cr.execute("""SELECT sol.product_id as product_id,
                                        w.id as warehouse_id
                                            FROM sale_order_line AS sol
                                                LEFT JOIN product_product AS pp
                                               ON pp.id = sol.product_id
                                                LEFT join product_template AS pt
                                               ON pp.product_tmpl_id = pt.id
                                                LEFT JOIN stock_warehouse w
           					                ON w.id = sol.warehouse_id
                                                WHERE
                                                  sol.state = 'done'
                                                  AND sol.is_return <> 't'
                                                   AND order_date BETWEEN '%s' AND '%s'
                                                   AND pt.id = %s
                                               GROUP BY sol.product_id,
                                                        w.id
                                                          """
                            % (start_date, end_date, self.product_id.id))
           products= self._cr.dictfetchall()
           if products:
               for f in products:
                   if f['product_id'] not in product_ids:
                       product_ids.append(f['product_id'])
           self.product_ids = product_ids
        return self.product_ids

    @api.one
    @api.depends('remaining_qty')
    def _compute_balance_product_ids(self):
        product_ids = []
        product_product = self.env['product.product'].search([('product_tmpl_id', '=', self.product_id.id)])
        end_date = datetime.strptime(self.suggestion_id.end_date, '%Y-%m-%d').date()
        for m in self:
            for f in product_product:
                self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                 "where date <= %s "
                                 "and location_id = %s and product_id = %s and state = 'done'",
                                 (str(end_date) + ' 23:59:59', m.warehouse_id.lot_stock_id.id,
                                  f.id))
                fetched = self._cr.dictfetchall()
                # print'fetched \n',fetched
                if fetched:
                    for k in fetched:
                        if k['product_qty'] is None:
                            qty = 0.0
                        else:
                            qty = k['product_qty']
                self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                 "where date <= %s "
                                 "and location_dest_id = %s and product_id = %s and state = 'done'",
                                 (str(end_date) + ' 23:59:59', m.warehouse_id.lot_stock_id.id, f.id))
                in_moves = self._cr.dictfetchall()
                # print'in_moves \n', in_moves
                if in_moves:
                    for i in in_moves:
                        if i['product_qty'] is None:
                            qty2 = 0.0
                        else:
                            qty2 = i['product_qty']
                remainder = qty2 - qty
                if remainder > 0.0:
                    product_ids.append(f.id)
        self.balance_product_ids = product_ids
        return self.balance_product_ids

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Төлөв', readonly=True, copy=False, store=True, default='draft')
    suggestion_id = fields.Many2one('suggestion.order','Suggestion')
    is_useful = fields.Boolean(string = 'Useful',default = False)
    product_id = fields.Many2one('product.template', string='Бараа',
                                 change_default=True, ondelete='restrict', readonly=True)
    sale_count = fields.Float('Sale Count')
    # remaining_qty = fields.Float('Remaining Qty',compute = _qty_available, store = True)
    remaining_qty = fields.Float('Remaining Qty')

    balance_product_ids = fields.One2many('product.product','suggestion_line_bid', string='Balance Sizes')
    product_ids = fields.One2many('product.product','suggestion_line_sid', string='Sold Sizes')
    # balance_product_ids = fields.Many2many('product.product', string='Balance Sizes', compute=_compute_balance_product_ids,store = True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Салбар',
                                   change_default=True, ondelete='restrict', readonly=True)
    # product_ids = fields.Many2many('product.product', string='Sold Sizes',compute = _compute_product_ids,store = True)
    sale_sizes = fields.Char(string = 'SSizes',default =' ')
    total_sizes = fields.Char(string = 'TSizes',default =' ')
    warehouse_line_id = fields.One2many('suggestion.order.line.line', 'line_id', string='Other Warehouses')
    tuv_sizes = fields.Char(string = 'Tuv Sizes',default =' ')
    sizes_gragu = fields.Char(string = 'GRAGU Sizes',default =' ')
    sizes_maxba = fields.Char(string = 'MAXBA Sizes',default =' ')
    sizes_maxsg = fields.Char(string = 'MAXSG Sizes',default =' ')
    sizes_maxsf = fields.Char(string = 'MAXSF Sizes',default =' ')
    sizes_ubbas = fields.Char(string = 'UBBAS Sizes',default =' ')
    sizes_ub_sf = fields.Char(string = 'UB-SF Sizes',default =' ')
    sizes_ubbug = fields.Char(string = 'UBBUG Sizes',default =' ')
    sizes_hubas = fields.Char(string = 'HUBAS Sizes',default =' ')
    sizes_hubug = fields.Char(string = 'HUBUG Sizes',default =' ')
    sizes_emart = fields.Char(string = 'EMART Sizes',default =' ')
    sizes_grand1 = fields.Char(string = 'GRAND1 Sizes',default =' ')







class SuggestionOrderProductLine(models.Model):
    _name = "suggestion.order.product.line"
    _order = 'sale_count desc'

    suggestion_id = fields.Many2one('suggestion.order', 'Suggestion')
    product_id = fields.Many2one('product.template', string='Бараа')
    sale_count = fields.Float('Sale Count')
    amount = fields.Float('Amount')

class SuggestionOrderWarehouseLine(models.Model):
    _name = "suggestion.order.warehouse.line"
    _order = 'amount desc'

    suggestion_id = fields.Many2one('suggestion.order', 'Suggestion')
    number = fields.Integer('Rank')
    warehouse_id = fields.Many2one('stock.warehouse', string='Салбар',
                                 change_default=True, ondelete='restrict')
    amount = fields.Float('Amount')

class SuggestionOrder(models.Model):
    _name = "suggestion.order"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'start_date desc'

    start_date = fields.Date(string='Эхлэх огноо', required=True, index=True,
                                 copy=False,
                                 default=fields.Datetime.now)
    end_date = fields.Date(string='Дуусах огноо', required=True,index=True,
                           copy=False,
                           default=fields.Datetime.now)
    warehouse_id = fields.Many2one('stock.warehouse', string = 'Салбар')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ],  string='Төлөв', readonly=True, copy=False, store=True, default='draft')
    suggestion_lines = fields.One2many('suggestion.order.line', 'suggestion_id', string='Suggestion Lines')
    top_product_lines = fields.One2many('suggestion.order.product.line', 'suggestion_id', string='Top Products')
    top_warehouse_lines = fields.One2many('suggestion.order.warehouse.line', 'suggestion_id', string='Top Warehouses')


    def compute_order(self):
        if self.top_warehouse_lines or self.top_product_lines or self.suggestion_lines:
            self._cr.execute("""DELETE FROM suggestion_order_warehouse_line WHERE suggestion_id = %s """ % (self.id,))
            self._cr.execute("""DELETE FROM suggestion_order_product_line WHERE suggestion_id = %s """ % (self.id,))
            self._cr.execute("""DELETE FROM suggestion_order_line WHERE suggestion_id = %s """ % (self.id,))

        warehouse_line = self.env['suggestion.order.warehouse.line']
        product_line = self.env['suggestion.order.product.line']
        line_line = self.env['suggestion.order.line.line']
        main_line = self.env['suggestion.order.line']
        product_objs = self.env['product.product']
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        diff = end_date - start_date
        if diff.days > 7:
            raise UserError(_(
                       'Too Large. You only can get 7 days calculation \n Check!'))
        self._cr.execute("""SELECT w.id as warehouse,
                                    sl.id as location,
                                   pt.name AS name,
                                   pt.id AS tmpl,
                                   sum(sol.price_total) AS total,
                                   sum(sol.qty_delivered) AS qty
                                     FROM sale_order_line AS sol
                                     LEFT JOIN product_product AS pp
                                    ON pp.id = sol.product_id
                                     LEFT join product_template AS pt
                                    ON pp.product_tmpl_id = pt.id
                                     LEFT JOIN stock_warehouse w
                                    ON w.id = sol.warehouse_id
                                     LEFT JOIN stock_location sl
                                    ON w.lot_stock_id = sl.id
                                     WHERE
                                       sol.state = 'done'
                                       AND sol.is_return <> 't'
                                        AND order_date BETWEEN '%s' AND '%s'
                                    GROUP BY w.id,
                                            sl.id,
                                               pt.id
                                               ORDER BY qty DESC"""
                         % (start_date, end_date))
        sol_list = self._cr.dictfetchall()
        if sol_list:
            # Агуулахын мэдээллийг олох
            c = Counter()
            a = Counter()
            # List of dic г агуулахаар нь бүлэглэж sum total г олов
            for v in sol_list:
                c[v['warehouse']] += v['total']
            warehouse_data = [{'warehouse': warehouse, 'total': total} for warehouse, total in c.items()]
            # Rank лахын тулд эрэмблэв
            sort_orders = sorted(warehouse_data, key=lambda k: k['total'],reverse=True)
            i = 1
            for e in sort_orders:
                warehouse_line.create({'warehouse_id':e['warehouse'],
                                       'amount':e['total'],
                                       'number':i,
                                       'suggestion_id':self.id})
                i += 1
            # Хамгийн их борлуулалттай барааны жагсаалт
            for d in sol_list:
                a[d['tmpl']] += d['qty']

            product_template_ids = [{'tmpl': tmpl, 'qty': qty} for tmpl, qty in a.items()]

            for p in product_template_ids:
                product_line.create({'product_id': int(p['tmpl']),
                                     'sale_count': p['qty'],
                                     'suggestion_id': self.id
                                     })
            product_sizes = []
            if self.warehouse_id:
                self._cr.execute("""SELECT w.id as warehouse,
                                                    sl.id as location,
                                                   pt.name AS name,
                                                   pt.id AS tmpl,
                                                   sum(sol.price_total) AS total,
                                                   sum(sol.qty_delivered) AS qty
                                                     FROM sale_order_line AS sol
                                                     LEFT JOIN product_product AS pp
                                                    ON pp.id = sol.product_id
                                                     LEFT join product_template AS pt
                                                    ON pp.product_tmpl_id = pt.id
                                                     LEFT JOIN stock_warehouse w
                                                    ON w.id = sol.warehouse_id
                                                     LEFT JOIN stock_location sl
                                                    ON w.lot_stock_id = sl.id
                                                     WHERE
                                                       sol.state = 'done'
                                                       AND sol.is_return <> 't'
                                                        AND sol.order_date BETWEEN '%s' AND '%s'
                                                        AND sol.warehouse_id = '%s'
                                                    GROUP BY w.id,
                                                            sl.id,
                                                               pt.id
                                                               ORDER BY qty DESC"""
                                 % (start_date, end_date,self.warehouse_id.id))
                sol_list_by_wh = self._cr.dictfetchall()
                for m in sol_list_by_wh:
                    # speed Үлдэгдлийг тооцох
                    remaing_qty_last = 0
                    product_ids = []
                    product_product = self.env['product.product'].search([('product_tmpl_id', '=', m['tmpl'])])
                    end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
                    for f in product_product:
                        self._cr.execute(
                            "SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                            "where date <= %s "
                            "and location_id = %s and product_id = %s and state = 'done'",
                            (str(end_date) + ' 23:59:59', m['location'],
                             f.id))
                        fetched = self._cr.dictfetchall()
                        # print'fetched \n',fetched
                        if fetched:
                            for k in fetched:
                                if k['product_qty'] is None:
                                    qty = 0.0
                                else:
                                    qty = k['product_qty']
                        self._cr.execute(
                            "SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                            "where date <= %s "
                            "and location_dest_id = %s and product_id = %s and state = 'done'",
                            (str(end_date) + ' 23:59:59', m['location'], f.id))
                        in_moves = self._cr.dictfetchall()
                        # print'in_moves \n', in_moves
                        if in_moves:
                            for i in in_moves:
                                if i['product_qty'] is None:
                                    qty2 = 0.0
                                else:
                                    qty2 = i['product_qty']
                        remainder = qty2 - qty
                        if remainder > 0.0:
                            product_ids.append(f.id)
                            remaing_qty_last += remainder

                    # speed

                    # speed Борлуулсан бараануудыг тооцох
                    start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
                    sold_product_ids = []
                    self._cr.execute("""SELECT sol.product_id as product_id,
                                                        w.id as warehouse_id
                                                            FROM sale_order_line AS sol
                                                                LEFT JOIN product_product AS pp
                                                               ON pp.id = sol.product_id
                                                                LEFT join product_template AS pt
                                                               ON pp.product_tmpl_id = pt.id
                                                                LEFT JOIN stock_warehouse w
                                                            ON w.id = sol.warehouse_id
                                                                WHERE
                                                                  sol.state = 'done'
                                                                  AND sol.is_return <> 't'
                                                                   AND sol.order_date BETWEEN '%s' AND '%s'
                                                                   AND pt.id = %s
                                                                   AND sol.warehouse_id = %s
                                                               GROUP BY sol.product_id,
                                                                        w.id
                                                                          """
                                     % (start_date, end_date, m['tmpl'], m['warehouse']))
                    sold_products = self._cr.dictfetchall()
                    if sold_products:
                        for f in sold_products:
                            if f['product_id'] not in sold_product_ids:
                                sold_product_ids.append(f['product_id'])

                    # speed
                    created_values = main_line.create({
                        'warehouse_id': m['warehouse'],
                        'product_id': m['tmpl'],
                        'sale_count': m['qty'],
                        'balance_product_ids': [(6,0,product_ids)],
                        'product_ids': [(6,0,sold_product_ids)],
                        'remaining_qty': remaing_qty_last,
                        'suggestion_id': self.id
                    })
                    warehouses = self.env['stock.warehouse'].search(
                        [('id', '<>', m['warehouse']), ('real_warehouse', '=', True)])
                    product_product = self.env['product.product'].search(
                        [('product_tmpl_id', '=', m['tmpl']),
                         ('id', 'not in', created_values.balance_product_ids.ids)])
                    qty = 0.0
                    qty2 = 0.0
                    for f in product_product:
                        # Боломжит үлдэгдлийг олох Бусад агуулахад
                        for w in warehouses:
                            self._cr.execute(
                                "SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                "where date <= %s "
                                "and location_id = %s and product_id = %s and state = 'done'",
                                (str(end_date) + ' 23:59:59', w.lot_stock_id.id,
                                 f.id))
                            fetched = self._cr.dictfetchall()
                            if fetched:
                                for k in fetched:
                                    if k['product_qty'] is None:
                                        qty = 0.0
                                    else:
                                        qty = k['product_qty']
                            self._cr.execute(
                                "SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                "where date <= %s "
                                "and location_dest_id = %s and product_id = %s and state = 'done'",
                                (str(end_date) + ' 23:59:59', w.lot_stock_id.id, f.id))
                            in_moves = self._cr.dictfetchall()
                            if in_moves:
                                for i in in_moves:
                                    if i['product_qty'] is None:
                                        qty2 = 0.0
                                    else:
                                        qty2 = i['product_qty']
                            remainder = qty2 - qty
                            if remainder > 0.0:
                                rank = len(self.top_warehouse_lines) + 1
                                for h in self.top_warehouse_lines:
                                    if h.warehouse_id.id == w.id:
                                        rank = h.number
                                self._cr.execute(
                                    'INSERT INTO suggestion_order_line_line (line_id,warehouse_id,product_id,number,qty) '
                                    'values (%s, %s,%s, %s, %s)',
                                    (created_values.id, w.id, f.id, rank, remainder))
                                # temka1 = line_line.create({'line_id': created_values.id,
                                #                           'warehouse_id': w.id,
                                #                           'product_id': f.id,
                                #                           'number': rank,
                                #                           'qty': remainder})
                                # if temka1:
                                created_values.update({'is_useful': True})
                    for i in self.suggestion_lines:
                        if i.warehouse_line_id:
                            check_product = []
                            self._cr.execute(
                                "SELECT id,product_id as product_id,warehouse_id,number from suggestion_order_line_line "
                                "where line_id <= %s ORDER BY number DESC",
                                (i.id,))
                            sorted_line = self._cr.dictfetchall()
                            for s in sorted_line:
                                if s['product_id'] not in check_product:
                                    check_product.append(s['product_id'])
                                else:
                                    self._cr.execute(
                                        """DELETE FROM suggestion_order_line_line WHERE id = %s """ % (s['id'],))

                            for temka2 in self.suggestion_lines:
                                product_check_sizes = []
                                product_check_grand_gutal = []
                                product_check_max_basconi = []
                                product_check_max_shoegallery = []
                                product_check_max_sasha_fabiani = []
                                product_check_ub_basconi = []
                                product_check_ub_sasha_fabiani = []
                                product_check_ub_bugatti = []
                                product_check_hunnu_basconi = []
                                product_check_hunnu_bugatti = []
                                product_check_emart_shoegallery = []
                                product_check_grand1 = []
                                sizes = ' '
                                sizes_gragu = ' '
                                sizes_maxba = ' '
                                sizes_maxsg = ' '
                                sizes_maxsf = ' '
                                sizes_ubbas = ' '
                                sizes_ub_sf = ' '
                                sizes_ubbug = ' '
                                sizes_hubas = ' '
                                sizes_hubug = ' '
                                sizes_emart = ' '
                                sizes_grand1 = ' '
                                wh_line = self.env['suggestion.order.line.line'].search(
                                    [('line_id', '=', temka2.id)])
                                if wh_line:
                                    for temka1 in wh_line:
                                        if temka1.product_id.id not in product_check_sizes and temka1.warehouse_id.id == 1:
                                            product_check_sizes.append(temka1.product_id.id)
                                            sizes = sizes + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_grand_gutal and temka1.warehouse_id.id == 2:
                                            product_check_grand_gutal.append(temka1.product_id.id)
                                            sizes_gragu = sizes_gragu + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_max_basconi and temka1.warehouse_id.id == 4:
                                            product_check_max_basconi.append(temka1.product_id.id)
                                            sizes_maxba = sizes_maxba + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_max_shoegallery and temka1.warehouse_id.id == 6:
                                            product_check_max_shoegallery.append(temka1.product_id.id)
                                            sizes_maxsg = sizes_maxsg + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_max_sasha_fabiani and temka1.warehouse_id.id == 7:
                                            product_check_max_sasha_fabiani.append(temka1.product_id.id)
                                            sizes_maxsf = sizes_maxsf + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_ub_basconi and temka1.warehouse_id.id == 8:
                                            product_check_ub_basconi.append(temka1.product_id.id)
                                            sizes_ubbas = sizes_ubbas + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_ub_sasha_fabiani and temka1.warehouse_id.id == 9:
                                            product_check_ub_sasha_fabiani.append(temka1.product_id.id)
                                            sizes_ub_sf = sizes_ub_sf + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_ub_bugatti and temka1.warehouse_id.id == 10:
                                            product_check_ub_bugatti.append(temka1.product_id.id)
                                            sizes_ubbug = sizes_ubbug + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_hunnu_basconi and temka1.warehouse_id.id == 19:
                                            product_check_hunnu_basconi.append(temka1.product_id.id)
                                            sizes_hubas = sizes_hubas + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_hunnu_bugatti and temka1.warehouse_id.id == 20:
                                            product_check_hunnu_bugatti.append(temka1.product_id.id)
                                            sizes_hubug = sizes_hubug + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_emart_shoegallery and temka1.warehouse_id.id == 25:
                                            product_check_emart_shoegallery.append(temka1.product_id.id)
                                            sizes_emart = sizes_emart + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                        if temka1.product_id.id not in product_check_grand1 and temka1.warehouse_id.id == 28:
                                            product_check_grand1.append(temka1.product_id.id)
                                            sizes_grand1 = sizes_grand1 + ' ' + str(
                                                temka1.product_id.attribute_value_ids[0].name)
                                temka2.write({'tuv_sizes': sizes,
                                              'sizes_gragu': sizes_gragu,
                                              'sizes_maxba': sizes_maxba,
                                              'sizes_maxsg': sizes_maxsg,
                                              'sizes_maxsf': sizes_maxsf,
                                              'sizes_ubbas': sizes_ubbas,
                                              'sizes_ub_sf': sizes_ub_sf,
                                              'sizes_ubbug': sizes_ubbug,
                                              'sizes_hubas': sizes_hubas,
                                              'sizes_hubug': sizes_hubug,
                                              'sizes_emart': sizes_emart,
                                              'sizes_grand1': sizes_grand1})
            if self.suggestion_lines:
                for f in self.suggestion_lines:
                    if f.balance_product_ids:
                        for p in f.balance_product_ids:
                            for a in p.attribute_value_ids:
                                f.total_sizes = str(f.total_sizes) + ' ' + str(a.name)
                    if f.product_ids:
                        for p1 in f.product_ids:
                            for a1 in p1.attribute_value_ids:
                                f.sale_sizes = str(f.sale_sizes) + ' ' + str(a1.name)
            else:
                for m in sol_list:
                    #speed Үлдэгдлийг тооцох
                    remaing_qty_last = 0
                    product_ids = []
                    product_product = self.env['product.product'].search([('product_tmpl_id', '=', m['tmpl'])])
                    end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
                    for f in product_product:
                        self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                         "where date <= %s "
                                         "and location_id = %s and product_id = %s and state = 'done'",
                                         (str(end_date) + ' 23:59:59', m['location'],
                                          f.id))
                        fetched = self._cr.dictfetchall()
                        # print'fetched \n',fetched
                        if fetched:
                            for k in fetched:
                                if k['product_qty'] is None:
                                    qty = 0.0
                                else:
                                    qty = k['product_qty']
                        self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                         "where date <= %s "
                                         "and location_dest_id = %s and product_id = %s and state = 'done'",
                                         (str(end_date) + ' 23:59:59', m['location'], f.id))
                        in_moves = self._cr.dictfetchall()
                        # print'in_moves \n', in_moves
                        if in_moves:
                            for i in in_moves:
                                if i['product_qty'] is None:
                                    qty2 = 0.0
                                else:
                                    qty2 = i['product_qty']
                        remainder = qty2 - qty
                        if remainder > 0.0:
                            product_ids.append(f.id)
                            remaing_qty_last += remainder


                    #speed

                    #speed Борлуулсан бараануудыг тооцох
                    start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
                    sold_product_ids = []
                    self._cr.execute("""SELECT sol.product_id as product_id,
                                                        w.id as warehouse_id
                                                            FROM sale_order_line AS sol
                                                                LEFT JOIN product_product AS pp
                                                               ON pp.id = sol.product_id
                                                                LEFT join product_template AS pt
                                                               ON pp.product_tmpl_id = pt.id
                                                                LEFT JOIN stock_warehouse w
                                                            ON w.id = sol.warehouse_id
                                                                WHERE
                                                                  sol.state = 'done'
                                                                  AND sol.is_return <> 't'
                                                                   AND order_date BETWEEN '%s' AND '%s'
                                                                   AND pt.id = %s
                                                                   AND sol.warehouse_id = %s
                                                               GROUP BY sol.product_id,
                                                                        w.id
                                                                          """
                                     % (start_date, end_date, m['tmpl'],m['warehouse']))
                    sold_products = self._cr.dictfetchall()
                    if sold_products:
                        for f in sold_products:
                            if f['product_id'] not in sold_product_ids:
                                sold_product_ids.append(f['product_id'])
                    #speed
                    created_values = main_line.create({
                        'warehouse_id': m['warehouse'],
                        'product_id': m['tmpl'],
                        'sale_count': m['qty'],
                        'balance_product_ids': [(6, 0, product_ids)],
                        'product_ids': [(6, 0, sold_product_ids)],
                        'remaining_qty': remaing_qty_last,
                        'suggestion_id': self.id
                    })
                    warehouses = self.env['stock.warehouse'].search([('id', '<>', m['warehouse']),('real_warehouse','=',True)])
                    product_product = self.env['product.product'].search(
                        [('product_tmpl_id', '=', m['tmpl']), ('id', 'not in', created_values.balance_product_ids.ids)])
                    qty = 0.0
                    qty2 = 0.0
                    for f in product_product:
                        # Боломжит үлдэгдлийг олох Бусад агуулахад
                        for w in warehouses:
                            self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                             "where date <= %s "
                                             "and location_id = %s and product_id = %s and state = 'done'",
                                             (str(end_date) + ' 23:59:59', w.lot_stock_id.id,
                                              f.id))
                            fetched = self._cr.dictfetchall()
                            if fetched:
                                for k in fetched:
                                    if k['product_qty'] is None:
                                        qty = 0.0
                                    else:
                                        qty = k['product_qty']
                            self._cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from stock_move "
                                             "where date <= %s "
                                             "and location_dest_id = %s and product_id = %s and state = 'done'",
                                             (str(end_date) + ' 23:59:59', w.lot_stock_id.id, f.id))
                            in_moves = self._cr.dictfetchall()
                            if in_moves:
                                for i in in_moves:
                                    if i['product_qty'] is None:
                                        qty2 = 0.0
                                    else:
                                        qty2 = i['product_qty']
                            remainder = qty2 - qty
                            if remainder > 0.0:
                                rank = len(self.top_warehouse_lines) + 1
                                for h in self.top_warehouse_lines:
                                    if h.warehouse_id.id == w.id:
                                        rank = h.number
                                self._cr.execute(
                                    'INSERT INTO suggestion_order_line_line (line_id,warehouse_id,product_id,number,qty) '
                                    'values (%s, %s,%s, %s, %s)',
                                    (created_values.id, w.id,f.id,rank,remainder))
                                # temka1 = line_line.create({'line_id': created_values.id,
                                #                           'warehouse_id': w.id,
                                #                           'product_id': f.id,
                                #                           'number': rank,
                                #                           'qty': remainder})
                                # if temka1:
                                created_values.update({'is_useful': True})
                for i in self.suggestion_lines:
                    if i.warehouse_line_id:
                        check_product = []
                        self._cr.execute("SELECT id,product_id as product_id,warehouse_id,number from suggestion_order_line_line "
                                         "where line_id <= %s ORDER BY number DESC",
                                         (i.id,))
                        sorted_line = self._cr.dictfetchall()
                        for s in sorted_line:
                            if s['product_id'] not in check_product:
                                check_product.append(s['product_id'])
                            else:
                                self._cr.execute(
                                    """DELETE FROM suggestion_order_line_line WHERE id = %s """ % (s['id'],))


                        for temka2 in self.suggestion_lines:
                            product_check_sizes = []
                            product_check_grand_gutal = []
                            product_check_max_basconi = []
                            product_check_max_shoegallery = []
                            product_check_max_sasha_fabiani = []
                            product_check_ub_basconi = []
                            product_check_ub_sasha_fabiani = []
                            product_check_ub_bugatti = []
                            product_check_hunnu_basconi = []
                            product_check_hunnu_bugatti = []
                            product_check_emart_shoegallery = []
                            product_check_grand1 = []
                            sizes = ' '
                            sizes_gragu = ' '
                            sizes_maxba = ' '
                            sizes_maxsg = ' '
                            sizes_maxsf = ' '
                            sizes_ubbas = ' '
                            sizes_ub_sf = ' '
                            sizes_ubbug = ' '
                            sizes_hubas = ' '
                            sizes_hubug = ' '
                            sizes_emart = ' '
                            sizes_grand1 = ' '
                            wh_line = self.env['suggestion.order.line.line'].search(
                                [('line_id', '=', temka2.id)])
                            if wh_line:
                                for temka1 in wh_line:
                                    if temka1.product_id.id not in product_check_sizes and temka1.warehouse_id.id == 1:
                                        product_check_sizes.append(temka1.product_id.id)
                                        sizes = sizes + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_grand_gutal and temka1.warehouse_id.id == 2:
                                        product_check_grand_gutal.append(temka1.product_id.id)
                                        sizes_gragu = sizes_gragu + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_max_basconi and temka1.warehouse_id.id == 4:
                                        product_check_max_basconi.append(temka1.product_id.id)
                                        sizes_maxba = sizes_maxba + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_max_shoegallery and temka1.warehouse_id.id == 6:
                                        product_check_max_shoegallery.append(temka1.product_id.id)
                                        sizes_maxsg = sizes_maxsg + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_max_sasha_fabiani and temka1.warehouse_id.id == 7:
                                        product_check_max_sasha_fabiani.append(temka1.product_id.id)
                                        sizes_maxsf = sizes_maxsf + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_ub_basconi and temka1.warehouse_id.id == 8:
                                        product_check_ub_basconi.append(temka1.product_id.id)
                                        sizes_ubbas = sizes_ubbas + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_ub_sasha_fabiani and temka1.warehouse_id.id == 9:
                                        product_check_ub_sasha_fabiani.append(temka1.product_id.id)
                                        sizes_ub_sf = sizes_ub_sf + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_ub_bugatti and temka1.warehouse_id.id == 10:
                                        product_check_ub_bugatti.append(temka1.product_id.id)
                                        sizes_ubbug = sizes_ubbug + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_hunnu_basconi and temka1.warehouse_id.id == 19:
                                        product_check_hunnu_basconi.append(temka1.product_id.id)
                                        sizes_hubas = sizes_hubas + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_hunnu_bugatti and temka1.warehouse_id.id == 20:
                                        product_check_hunnu_bugatti.append(temka1.product_id.id)
                                        sizes_hubug = sizes_hubug + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_emart_shoegallery and temka1.warehouse_id.id == 25:
                                        product_check_emart_shoegallery.append(temka1.product_id.id)
                                        sizes_emart = sizes_emart + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                                    if temka1.product_id.id not in product_check_grand1 and temka1.warehouse_id.id == 28:
                                        product_check_grand1.append(temka1.product_id.id)
                                        sizes_grand1 = sizes_grand1 + ' ' + str(temka1.product_id.attribute_value_ids[0].name)
                            temka2.write({'tuv_sizes':sizes,
                                            'sizes_gragu':sizes_gragu,
                                            'sizes_maxba':sizes_maxba,
                                            'sizes_maxsg':sizes_maxsg,
                                            'sizes_maxsf':sizes_maxsf,
                                            'sizes_ubbas':sizes_ubbas,
                                            'sizes_ub_sf':sizes_ub_sf,
                                            'sizes_ubbug':sizes_ubbug,
                                            'sizes_hubas':sizes_hubas,
                                            'sizes_hubug':sizes_hubug,
                                            'sizes_emart':sizes_emart,
                                            'sizes_grand1':sizes_grand1})
                if self.suggestion_lines:
                    for f in self.suggestion_lines:
                        if f.balance_product_ids:
                            for p in f.balance_product_ids:
                                for a in p.attribute_value_ids:
                                    f.total_sizes = str(f.total_sizes) + ' ' + str(a.name)
                        if f.product_ids:
                            for p1 in f.product_ids:
                                for a1 in p1.attribute_value_ids:
                                    f.sale_sizes = str(f.sale_sizes) + ' ' + str(a1.name)


    def prepare_data(self):

        data = []

        self._cr.execute("""SELECT pt.default_code as id,l.product_id AS pt_id,pt.name AS pt,wh.name as warehouse ,l.sale_count AS sold_qty,
                                    l.sale_sizes AS sold_sizes,l.remaining_qty as total_qty,l.total_sizes as total_sizes,
                                    l.tuv_sizes as tuv_sizes,
                                    l.sizes_gragu as sizes_gragu,
                                    l.sizes_maxba as sizes_maxba,
                                    l.sizes_maxsg as sizes_maxsg,
                                    l.sizes_maxsf as sizes_maxsf,
                                    l.sizes_ubbas as sizes_ubbas,
                                    l.sizes_ub_sf as sizes_ub_sf,
                                    l.sizes_ubbug as sizes_ubbug,
                                    l.sizes_hubas as sizes_hubas,
                                    l.sizes_hubug as sizes_hubug,
                                    l.sizes_emart as sizes_emart,
                                    l.sizes_grand1 as sizes_grand1

                            from suggestion_order_line l
                            left join suggestion_order so on so.id = l.suggestion_id
                            left join product_template pt on pt.id = l.product_id
                            left join stock_warehouse wh on wh.id = l.warehouse_id
                            where l.is_useful = 't' AND so.id =  %s """ % (self.id))
        main_list = self._cr.dictfetchall()
        if main_list:
          return main_list


    @api.multi
    def export_report(self):
        data = self.prepare_data()
        # print 'data',data
        # create workbook
        book = xlwt.Workbook(encoding='utf8')
        # create sheet
        report_name = _('Suggestion Order Report')
        sheet = book.add_sheet(report_name)

        # create report object
        report_excel_output = self.env['report.excel.output.extend'].with_context(filename_prefix='Suggestion Order Report', form_title=report_name).create({})

        rowx = 0
        colx = 0

        # define title and header
        top_warehouses = [_('Top Warehouses :')]
        title_list = [_('Code'), _('Product'), _('Sold WH'),_('Sold Qty'), _('Sold Sizes'), _('Balance'), _('Balance sizes'), _('Tuv WH'), _('Grand Gutal'),_('MAX Basconi'), _('MAX SHOEGALLERY'),
                      _('MAX SASHA FABIANI'),_('UB BASCONI'),_('UB SASHA FABIANI'),_('UB BUGATTI'),_('HUNNU BASCONI'),_('HUNNU BUGATTI'),_('EMART SHOEGALLERY'),_('GRAND 1'),]
        if self.top_warehouse_lines:
            for u in self.top_warehouse_lines.sorted(key=lambda r: r.number, reverse=True):
                variable = _('%s') % u.warehouse_id.name + '-' + str(u.number)
                top_warehouses.append(variable)
        colx_number = len(title_list) - 1

        # create name
        sheet.write_merge(rowx, rowx, colx + 1, colx_number, report_name.upper(), style_filter)
        rowx += 1
        # create header
        # if self.warehouse_id:
        if self.warehouse_id.name:
            report_swh = _('%s') % self.warehouse_id.name
            sheet.write_merge(rowx, rowx, 1, colx_number, report_swh, style_filter)
            sheet.write
            rowx += 1

        report_start_date = _('Start Date : %s') % self.start_date
        # create name
        sheet.write_merge(rowx, rowx, colx + 1, colx_number, report_start_date, style_filter)
        rowx += 1
        report_end_date = _('End Date : %s') % self.end_date
        # create name
        sheet.write_merge(rowx, rowx, colx + 1, colx_number, report_end_date, style_filter)
        rowx += 2

        for i in xrange(0, len(top_warehouses)):
            sheet.write_merge(rowx, rowx, i, i, top_warehouses[i], style_title)

        rowx += 2

        for i in xrange(0, len(title_list)):
            sheet.write_merge(rowx, rowx, i, i, title_list[i], style_title)
        rowx += 1

        if data:
            for d in data:
                sheet.write(rowx, colx, d['id'], style_footer)
                sheet.write(rowx, colx+1, d['pt'], style_footer)
                sheet.write(rowx, colx+2, d['warehouse'], style_footer)
                sheet.write(rowx, colx+3, d['sold_qty'], style_footer)
                sheet.write(rowx, colx+4, d['sold_sizes'], style_footer)
                sheet.write(rowx, colx+5, d['total_qty'], style_footer)
                sheet.write(rowx, colx+6, d['total_sizes'], style_footer)
                sheet.write(rowx, colx+7, d['tuv_sizes'], style_footer)
                sheet.write(rowx, colx+8, d['sizes_gragu'], style_footer)
                sheet.write(rowx, colx+9, d['sizes_maxba'], style_footer)
                sheet.write(rowx, colx+10, d['sizes_maxsg'], style_footer)
                sheet.write(rowx, colx+11, d['sizes_maxsf'], style_footer)
                sheet.write(rowx, colx+12, d['sizes_ubbas'], style_footer)
                sheet.write(rowx, colx+13, d['sizes_ub_sf'], style_footer)
                sheet.write(rowx, colx+14, d['sizes_ubbug'], style_footer)
                sheet.write(rowx, colx+15, d['sizes_hubas'], style_footer)
                sheet.write(rowx, colx+16, d['sizes_hubug'], style_footer)
                sheet.write(rowx, colx+17, d['sizes_emart'], style_footer)
                sheet.write(rowx, colx+18, d['sizes_grand1'], style_footer)
                rowx += 1
        # prepare file data
        io_buffer = StringIO()
        book.save(io_buffer)
        io_buffer.seek(0)
        filedata = base64.encodestring(io_buffer.getvalue())
        io_buffer.close()

        # set file data
        report_excel_output.filedata = filedata

        # call export function
        return report_excel_output.export_report()
        # else:
        #     raise UserError(_(
        #         'Specific Warehouse does not selected!! \n Check!'))



