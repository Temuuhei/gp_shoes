# -*- coding: utf-8 -*-
##############################################################################
#
#    Game of Code LLC, Enterprise Management Solution
#    Copyright Game of Code LLC (C) 2017 . All Rights Reserved
#
#    Address :
#    Email :
#    Phone :
#
##############################################################################

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp


class DailyOrder(models.Model):
    _name = "daily.order"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date desc, product_qty desc'
    name = fields.Char(string='Тайлбар')
    date = fields.Datetime(string='Захиалсан огноо', required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'done': [('readonly', False)]}, copy=False,
                                 default=fields.Datetime.now)
    product_id = fields.Many2one('product.product', string='Бараа', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict', required=True)
    product_qty = fields.Float(string='Төв агуулахын нөөц', digits=dp.get_precision('Product Qty'), required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ],  string='Төлөв', readonly=True, copy=False, store=True, default='draft')
    location_id = fields.Many2one(
        'stock.location', "Захиалсан салбар",
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain="[('usage', '=', 'internal')]")

    def confirm_order(self):
        print'Confirm action here'
        stock_move = []
        qty = 0
        for item in self:
            main_warehouse = self.env['stock.warehouse'].search([('main_warehouse','=',True)])[0]
            if main_warehouse:
                picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                                                                      ('code', '=', 'internal')], limit=1)
                outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', main_warehouse.id),
                                                                           ('code', '=', 'outgoing')], limit=1)

                stock_move.append((0, 0, {'product_id': item.product_id.id,
                                          'product_uom_qty': 1,
                                          'state': 'draft',
                                          'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                                          'procure_method': 'make_to_stock',
                                          'location_id': main_warehouse.lot_stock_id.id,
                                          'location_dest_id': item.location_id.id,
                                          'company_id': 1,
                                          'date_expected': item.date,
                                          'date': item.date,
                                          'name': item.product_id.product_tmpl_id.name,
                                          'scrapped': False,
                                          }))
                vals={
                    'location_id':main_warehouse.lot_stock_id.id,
                    'picking_type_id':picking_type.id,
                    'move_type':'direct',
                    'company_id':1,
                    'location_dest_id':item.location_id.id,
                    'date': item.date,
                    'note':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                    'origin':u'%s-ны Өдрийн захиалгаас үүсэв'%(self.date),
                    'move_lines': stock_move,
                }
                new_picking = self.env['stock.picking'].create(vals)
                wiz_act = new_picking.do_new_transfer()
                wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                wiz.process()
                qty_obj = self.env['stock.quant'].search([('product_id', '=', item.product_id.id),
                                                          ('location_id', '=', main_warehouse.lot_stock_id.id)])
                for q in qty_obj:
                    qty += q.qty
                self.update({'state':'done',
                             'product_qty':qty})

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    main_warehouse = fields.Boolean(string = "Төв агуулах")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        module_id = self.env['ir.module.module'].search([('name','=','gp_shoes_daily_order'),
                                                         ('state','=','installed')])
        if module_id:
            print'Code here'
            if self.order_line:
                for line in self.order_line:
                    qty = 0
                    main_wh = self.env['stock.warehouse'].search([('main_warehouse','=',True)])[0]
                    if main_wh:
                        qty_obj = self.env['stock.quant'].search([('product_id', '=', line.product_id.id),
                                                                  ('location_id','=', main_wh.lot_stock_id.id)])
                        for q in qty_obj:
                            qty += q.qty

                        vals = {
                            'product_id': line.product_id.id,
                            'location_id': self.warehouse_id.lot_stock_id.id,
                            'date': self.date_order,
                            'state': 'draft',
                            'product_qty': qty,
                            'name':u'%s-ны %s Дугаартай Борлуулалтын захиалгаас шууд захиалга үүсэв'%(self.date_order, self.name)

                        }
                        do_obj = self.env['daily.order'].create(vals)
                        print'Daily Order Created ======>',do_obj
                    else:
                        raise UserError(_(
                            'Main Warehouse doesnt detected!! \n Configure the main warehouse!'))



        for order in self:
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
            order.order_line._action_procurement_create()
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        return True

