# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _default_payment_term(self):
        payment_term_id = self.env['account.payment.term'].search([('default','=',True)], limit=1)
        return payment_term_id

    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', required=False,
                                      oldname='payment_term',
                                      default=_default_payment_term)
    discount_manager = fields.Many2one('res.users', 'Discount manager',
                                       domain=lambda self: [('groups_id', '=', self.env.ref('gp_product_sale_report.group_discount_manager').id)])

    @api.multi
    def unlink(self):
        if self.state in ('done','sale'):
                raise UserError(
                        _(u'Та батлагдсан борлуулалтын захиалгын мөрийг устгаж болохгүй'))


    @api.multi
    def custom_confirm(self):
        for order in self:
            cash_amount = 0
            card_amount = 0
            mobile_amount = 0
            payment_type = 'mixed'
            cashes = self.env['cash'].search([('warehouse', '=', order.warehouse_id.id)])
            for order_line in order.order_line:
                cash_amount += order_line.cash_payment
                card_amount += order_line.card_payment
                mobile_amount += order_line.mobile_payment

            if cash_amount and not card_amount and not mobile_amount:
                payment_type = 'cash'
            elif card_amount and not cash_amount and not mobile_amount:
                payment_type = 'card'
            elif not cash_amount and not card_amount or mobile_amount:
                payment_type = 'mobile'
            elif cash_amount and card_amount or mobile_amount:
                payment_type = 'mixed'

            if cashes:
                for cash in cashes:
                    if cash.type == 'cash' and cash_amount:
                        cash.history.create({
                            'parent_id': cash.id,
                            'amount': cash_amount,
                            'remaining_amount': cash.amount,
                            'description': order.name + u' дугаартай борлуулалтаас [%s]' % order.id + u' [' + payment_type + u']',
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'in'
                        })
                        cash.amount += cash_amount
                    if cash.type == 'card' and card_amount:
                        cash.history.create({
                            'parent_id': cash.id,
                            'amount': card_amount,
                            'remaining_amount': cash.amount,
                            'description': order.name + u' дугаартай борлуулалтаас [%s]' % order.id + u' [' + payment_type + u']',
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'in'
                        })
                        cash.amount += card_amount

                    if cash.type == 'mobile' and mobile_amount:
                        cash.history.create({
                            'parent_id': cash.id,
                            'amount': card_amount,
                            'remaining_amount': cash.amount,
                            'description': order.name + u' дугаартай борлуулалтаас [%s]' % order.id + u' [' + payment_type + u']',
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'in'
                        })
                        cash.amount += mobile_amount

                order.write({'cash_pay': cash_amount, 'card_pay': card_amount,'mobile_pay': mobile_amount})
                order.action_confirm()
                #     Борлуулалтаас үүссэн Барааны хөдөлгөөнийг шууд батлах
                stock_picking = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)])
                if stock_picking:
                    for s in stock_picking:
                        s.write({'min_date': order.date,
                                 'date_done': order.date})
                        stock_move = self.env['stock.move'].search(
                            [('picking_id', '=', s.id)])

                        wiz_act = s.do_new_transfer()
                        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                        wiz.process()
                        if stock_move:
                            for sm in stock_move:
                                sm.write({'date': order.date})
                                print 'sm date',sm.date
                        print'Automat confirmed of Stock Picking'
                order.write({'state':'done'})

class Cash(models.Model):
    _inherit = "cash"

    # amount = fields.Float('Amount', compute="_compute_total_amount", store=True)
    #
    # @api.depends('history.amount')
    # def _compute_total_amount(self):
    #     for obj in self:
    #         tamt = 0
    #         for oh in obj.history:
    #             tamt += oh.amount
    #         obj.amount = tamt

class SaleChangeDate(models.TransientModel):
    _name = "sale.change.date"
    _description = "Sales Change Date"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))


    date = fields.Datetime(string='New Datetime',required = True)
    count = fields.Integer(default=_count, string='# of Orders')

    @api.multi
    def change_date(self):
        pickings = self.env['stock.picking']
        moves = self.env['stock.move']
        date_object = datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S')
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if sale_orders:
            if self.date:
                for s in sale_orders:
                    s.update({'date': self.date})
                    for l in s.order_line:
                        l.update({'order_date': date_object.date()})
                    pick = pickings.search([('group_id', '=', s.procurement_group_id.id)])
                    if pick:
                        for p in pick:
                            p.update({'min_date':self.date,
                                      'date_done': self.date})
                            move_obj = moves.search([('picking_id', '=', p.id)])
                            if move_obj:
                                for m in move_obj:
                                    m.update({'date':self.date})
            else:
                raise UserError(_(
                    'Please you select change date'))
        return {'type': 'ir.actions.act_window_close'}

