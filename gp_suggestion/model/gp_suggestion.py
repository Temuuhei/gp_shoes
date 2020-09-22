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

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    real_warehouse = fields.Boolean(string = "Бодит агуулах", default =False)

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
        warehouses = self.env['stock.warehouse'].search([('id', '<>', self.warehouse_id.id)])
        start_date = datetime.strptime(self.suggestion_id.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.suggestion_id.end_date, '%Y-%m-%d').date()
        # obj = self.env['suggestion.order.line.product.product.rel']
        product_ids = []
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
    remaining_qty = fields.Float('Remaining Qty',compute = _qty_available, store = True)
    balance_product_ids = fields.Many2many('product.product', string='Balance Sizes', compute=_compute_balance_product_ids)
    warehouse_id = fields.Many2one('stock.warehouse', string='Салбар',
                                   change_default=True, ondelete='restrict', readonly=True)
    product_ids = fields.Many2many('product.product', string='Sold Sizes',compute = _compute_product_ids)
    warehouse_line_id = fields.One2many('suggestion.order.line.line', 'line_id', string='Other Warehouses')



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
            self._cr.execute("""DELETE FROM suggestion_order_warehouse_line WHERE suggestion_id = %s """ % (self.id))
            self._cr.execute("""DELETE FROM suggestion_order_product_line WHERE suggestion_id = %s """ % (self.id))
            self._cr.execute("""DELETE FROM suggestion_order_line WHERE suggestion_id = %s """ % (self.id))

        warehouse_line = self.env['suggestion.order.warehouse.line']
        product_line = self.env['suggestion.order.product.line']
        line_line = self.env['suggestion.order.line.line']
        main_line = self.env['suggestion.order.line']
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        self._cr.execute("""SELECT w.id as warehouse,
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
                                     WHERE
                                       sol.state = 'done'
                                       AND sol.is_return <> 't'
                                        AND order_date BETWEEN '%s' AND '%s'
                                    GROUP BY w.id,
                                               pt.id
                                               ORDER BY qty DESC"""
                         % (start_date, end_date))
        sol_list = self._cr.dictfetchall()
        warehouse_ids = []
        product_template_ids = []
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
                for m in sol_list:
                    if m['warehouse'] == self.warehouse_id.id:
                        created_values =main_line.create({
                            'warehouse_id': m['warehouse'],
                            'product_id': m['tmpl'],
                            'sale_count': m['qty'],
                            'suggestion_id': self.id
                                             })

                        warehouses = self.env['stock.warehouse'].search([('id', '<>', m['warehouse']),('real_warehouse','=',True)])
                        product_product = self.env['product.product'].search([('product_tmpl_id', '=', m['tmpl']),('id','not in',created_values.balance_product_ids.ids)])
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
                                    rank = 0
                                    for h in self.top_warehouse_lines:
                                        if h.warehouse_id.id == w.id:
                                            rank = h.number
                                    temka = line_line.create({'line_id': created_values.id,
                                                        'warehouse_id': w.id,
                                                        'product_id': f.id,
                                                        'number': rank,
                                                        'qty': remainder})
                                    if temka:
                                        created_values.update({'is_useful':True})
            else:
                for m in sol_list:
                    created_values = main_line.create({
                        'warehouse_id': m['warehouse'],
                        'product_id': m['tmpl'],
                        'sale_count': m['qty'],
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
                                # vals = [(0, 0, {'line_id': created_values.id,
                                #                 'warehouse_id': w.id,
                                #                 'qty': remainder})]
                                rank = 0
                                for h in self.top_warehouse_lines:
                                    if h.warehouse_id.id == w.id:
                                        rank = h.number

                                temka = line_line.create({'line_id': created_values.id,
                                                          'warehouse_id': w.id,
                                                          'product_id': f.id,
                                                          'number': rank,
                                                          'qty': remainder})
                                if temka:
                                    created_values.update({'is_useful': True})

