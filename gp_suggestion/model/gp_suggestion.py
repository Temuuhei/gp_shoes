# -*- coding: utf-8 -*-
from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime

import odoo.addons.decimal_precision as dp

class SuggestionOrderLine(models.Model):
    _name = "suggestion.order.line"
    # _order = 'amount desc'

    suggestion_id = fields.Many2one('suggestion.order','Suggestion')
    product_id = fields.Many2one('product.product', string='Бараа', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict', readonly=True)
    sale_count = fields.Float('Sale Count')
    warehouse_id = fields.Many2one('stock.warehouse', string='Салбар',
                                   change_default=True, ondelete='restrict', readonly=True)
    def transit_order(self):
        print 'Temka  Transit here coding bro'

class SuggestionOrderProductLine(models.Model):
    _name = "suggestion.order.product.line"
    _order = 'amount desc'

    suggestion_id = fields.Many2one('suggestion.order', 'Suggestion')
    product_id = fields.Many2one('product.product', string='Бараа', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
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
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        print 'Temka here coding bro', end_date,type(start_date)
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
            for f in sol_list:
                if f['warehouse'] not in warehouse_ids:
                    print 'temka \n\n'

            print 'sol \n',sol_list



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
