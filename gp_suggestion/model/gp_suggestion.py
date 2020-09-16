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


class SuggestionOrderLineLine(models.Model):
    _name = "suggestion.order.line.line"
    # _order = 'amount desc'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.warehouse_id.name, rec.product_id.name + ': ' + str(rec.qty)))
        return res

    # @api.multi
    # def name_get(self):
    #
    #     return [('%s : %s : %s'  % (line.warehouse.name, line.product_id,line.qty)) for line in self]

    def ready_order(self):
        print'temka temka'
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
                print'p',p['tmpl']
                product_line.create({'product_id': int(p['tmpl']),
                                     'sale_count': p['qty'],
                                     'suggestion_id': self.id
                                     })
            product_sizes = []
            for m in sol_list:

                    created_values =main_line.create({
                        'warehouse_id': m['warehouse'],
                        'product_id': m['tmpl'],
                        'sale_count': m['qty'],
                        'suggestion_id': self.id
                                         })

                    warehouses = self.env['stock.warehouse'].search([('id', '<>', m['warehouse'])])
                    product_product = self.env['product.product'].search([('product_tmpl_id', '=', m['tmpl'])])
                    qty = 0.0
                    qty2 = 0.0
                    for f in product_product:
                        # Боломжит үлдэгдлийг олох Бусад агуулахад
                        for w in warehouses:
                            print 'w and remainder', f, w
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
                                temka = line_line.create({'line_id': created_values.id,
                                                    'warehouse_id': w.id,
                                                    'product_id': f.id,
                                                    'qty': remainder})
                                if temka:
                                    created_values.update({'is_useful':True})
                                print'Temka 11111111',temka


                # def to_archive(self):
                #     self.update({'active': False})

                # def ready_order(self):
                #     stock_move = []
                #     qty = 0
                #     for item in self:
                #         main_warehouse = self.env['stock.warehouse'].search([('main_warehouse','=',True)])[0]
                #         if main_warehouse:
                #             picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                #                                                                   ('code', '=', 'internal')], limit=1)
                #             outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                #                                                                        ('code', '=', 'outgoing')], limit=1)
                #
                #             stock_move.append((0, 0, {'product_id': item.product_id.id,
                #                                       'product_uom_qty': 1,
                #                                       'state': 'draft',
                #                                       'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                #                                       'procure_method': 'make_to_stock',
                #                                       'location_id': main_warehouse.lot_stock_id.id,
                #                                       'location_dest_id': item.location_id.id,
                #                                       'company_id': 1,
                #                                       'date_expected': datetime.now(),
                #                                       'date': datetime.now(),
                #                                       'name': item.product_id.product_tmpl_id.name,
                #                                       'scrapped': False,
                #                                       }))
                #             vals={
                #                 'location_id':main_warehouse.lot_stock_id.id,
                #                 'picking_type_id':picking_type.id,
                #                 'move_type':'direct',
                #                 'company_id':1,
                #                 'location_dest_id':item.location_id.id,
                #                 'date': datetime.now(),
                #                 'note':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                #                 'origin':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                #                 'move_lines': stock_move,
                #             }
                #             new_picking = self.env['stock.picking'].create(vals)
                #             wiz_act = new_picking.action_confirm()
                #             wiz_act = new_picking.force_assign()
                #             qty_obj = self.env['stock.quant'].search([('product_id', '=', item.product_id.id),
                #                                                       ('location_id', '=', main_warehouse.lot_stock_id.id)])
                #             for q in qty_obj:
                #                 qty += q.qty
                #             self.update({'state':'pending',
                #                          'product_qty':qty,
                #                          'origin':new_picking.name})

                # def confirm_order(self):
                #     stock_move = []
                #     qty = 0
                #     for item in self:
                #         main_warehouse = self.env['stock.warehouse'].search([('main_warehouse','=',True)])[0]
                #         if main_warehouse:
                #             picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                #                                                                   ('code', '=', 'internal')], limit=1)
                #             outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                #                                                                        ('code', '=', 'outgoing')], limit=1)
                #
                #             stock_move.append((0, 0, {'product_id': item.product_id.id,
                #                                       'product_uom_qty': 1,
                #                                       'state': 'draft',
                #                                       'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                #                                       'procure_method': 'make_to_stock',
                #                                       'location_id': main_warehouse.lot_stock_id.id,
                #                                       'location_dest_id': item.location_id.id,
                #                                       'company_id': 1,
                #                                       'date_expected': datetime.now(),
                #                                       'date': datetime.now(),
                #                                       'name': item.product_id.product_tmpl_id.name,
                #                                       'scrapped': False,
                #                                       }))
                #             vals={
                #                 'location_id':main_warehouse.lot_stock_id.id,
                #                 'picking_type_id':picking_type.id,
                #                 'move_type':'direct',
                #                 'company_id':1,
                #                 'location_dest_id':item.location_id.id,
                #                 'date': datetime.now(),
                #                 'note':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                #                 'origin':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                #                 'move_lines': stock_move,
                #             }
                #             new_picking = self.env['stock.picking'].create(vals)
                #             wiz_act = new_picking.do_new_transfer()
                #             wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                #             wiz.process()
                #             qty_obj = self.env['stock.quant'].search([('product_id', '=', item.product_id.id),
                #                                                       ('location_id', '=', main_warehouse.lot_stock_id.id)])
                #             for q in qty_obj:
                #                 qty += q.qty
                #             self.update({'state':'done',
                #                          'product_qty':qty,
                #                          'origin':new_picking.name})
#

# class RecordDailyOrderView111(models.AbstractModel):
#     _name = 'report.gp_shoes_daily_order.record_daily_order_view111'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         print 'qqqqqqqqqqq \n\n\n',docids
#         return docids
#
#
#
#     @api.model
#     def render_html(self, docids, data=None):
#         print 'hahahahahahah \n\n',docids
#         report_obj = self.env['ir.actions.report']
#         report = report_obj._get_report_from_name('gp_shoes_daily_order.record_daily_order_view111')
#
#         docargs = {
#             'doc_ids': docids,
#             'doc_model': report.template_report_daily_order,
#             'docs': self,
#         }
#         print 'docargs \n\n\n',docargs
#         return docargs

# class StockWarehouse(models.Model):
#     _inherit = "stock.warehouse"
#
#     main_warehouse = fields.Boolean(string = "Төв агуулах")
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     @api.multi
#     def action_confirm(self):
#         module_id = self.env['ir.module.module'].search([('name','=','gp_shoes_daily_order'),
#                                                          ('state','=','installed')])
#         if module_id:
#             if self.order_line:
#                 for line in self.order_line:
#                     qty = 0
#                     already_sent_qty = 0
#                     sent_do = []
#                     main_wh = self.env['stock.warehouse'].search([('main_warehouse','=',True)])[0]
#                     do_obj = self.env['daily.order'].search([('state','=','pending'),('product_id','=',line.product_id.id)])
#                     if do_obj:
#                         for d in do_obj:
#                             already_sent_qty += 1
#                             sent_do.append(d.name)
#                     if main_wh:
#                         qty_obj = self.env['stock.quant'].search([('product_id', '=', line.product_id.id),
#                                                                   ('location_id','=', main_wh.lot_stock_id.id)])
#                         for q in qty_obj:
#                             qty += q.qty
#
#                         vals = {
#                             'product_id': line.product_id.id,
#                             'location_id': self.warehouse_id.lot_stock_id.id,
#                             'warehouse_id': self.warehouse_id.id,
#                             'date': self.date_order,
#                             'state': 'draft',
#                             'product_qty': qty,
#                             'sent_product_qty': already_sent_qty,
#                             'sent_daily_order': sent_do,
#                             'active': True,
#                             'name':u'%s-ны %s Дугаартай Борлуулалтын захиалгаас шууд захиалга үүсэв'%(self.date_order, self.name)
#
#                         }
#                         do_obj = self.env['daily.order'].create(vals)
#                     else:
#                         raise UserError(_(
#                             'Main Warehouse doesnt detected!! \n Configure the main warehouse!'))
#
#
#
#         for order in self:
#             order.state = 'sale'
#             order.confirmation_date = fields.Datetime.now()
#             if self.env.context.get('send_email'):
#                 self.force_quotation_send()
#             order.order_line._action_procurement_create()
#         if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
#             self.action_done()
#         return True
#
