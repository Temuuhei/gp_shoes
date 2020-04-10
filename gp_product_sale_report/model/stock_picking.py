# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
class StockLocation(models.Model):
    _inherit = "stock.location"


    daily_order = fields.Boolean('Daily Order create')

class StockPicking(models.Model):
    _inherit = "stock.picking"


    product_template = fields.Many2one('product.template', 'Main product')
    is_existed_products = fields.Boolean('Байгаа бараануудыг харуулах', default = False)
    return_cash = fields.Float('Return cash', default = 0.0)

    @api.multi
    def insert_products(self):
        product = self.env['product.product']
        quant = self.env['stock.quant']
        for object in self:
            products = product.search([('product_tmpl_id', '=', object.product_template.id)])
            move_products = []
            if not object.min_date:
                raise ValidationError(_(u'Та товлогдсон огноо талбарыг сонгоно уу! '))

            if not object.is_existed_products:
                if products and object.min_date:
                    for m in object.move_lines:
                        move_products.append(m.product_id.id)
                    for p in products:
                        if p.id not in move_products:
                            object.move_lines.create({'picking_id': object.id,
                                              'name': p.product_tmpl_id.name,
                                              'product_id': p.id,
                                              'date': object.min_date,
                                              'create_date': object.min_date,
                                              'product_uom': p.product_tmpl_id.uom_id.id,
                                              'location_id': object.location_id.id,
                                              'location_dest_id': object.location_dest_id.id})
            else:
                if products and object.min_date:
                    for m in object.move_lines:
                        move_products.append(m.product_id.id)
                    for p in products:
                        if p.id not in move_products:
                            quants = quant.search([('product_id', '=', p.id),('location_id','=',object.location_id.id)])
                            if quants:
                                qty = 0.0
                                for q in quants:
                                    qty += q.qty
                                object.move_lines.create({'picking_id': object.id,
                                              'name': p.product_tmpl_id.name,
                                              'product_id': p.id,
                                              'date': object.min_date,
                                              'product_uom_qty': qty,
                                              'create_date': object.min_date,
                                              'product_uom': p.product_tmpl_id.uom_id.id,
                                              'location_id': object.location_id.id,
                                              'location_dest_id': object.location_dest_id.id})




    @api.multi
    def action_confirm(self):

        self.filtered(lambda picking: not picking.move_lines).write({'launch_pack_operations': True})
        # TDE CLEANME: use of launch pack operation, really useful ?
        self.mapped('move_lines').filtered(lambda move: move.state == 'draft').action_confirm()
        self.filtered(lambda picking: picking.location_id.usage in (
        'supplier', 'inventory', 'production')).force_assign()
        products = []
        for ml in self.move_lines:
            if self.location_id.id != 8:
                if ml.product_id not in products:
                    products.append(ml.product_id)
                else:
                    raise ValidationError(
                        _(u'Та энэ барааг 1 ээс дээш эхний шаардлага табанд бүртгэсэн байна! : %s') % ml.product_id.name_get())

                quant = self.env['stock.quant'].search([('location_id', '=', self.location_id.id),
                                                        ('product_id', '=', ml.product_id.id)])
                print ' QUANT___', quant
                qty = 0
                if quant:
                    for q in quant:
                        qty += q.qty
                        print ' Q>QTY___', q.qty
                    print ' TQTY___', qty
                    if qty < ml.product_uom_qty:
                        raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s') % ml.product_id.name_get())
                else:
                    raise ValidationError(
                        _(u'Танай агуулахад тухайн бараа байхгүй байна! : %s') % ml.product_id.name_get())
        return True

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'


    cash = fields.Many2one('cash','Cash')
    card = fields.Many2one('cash','Card')
    mobile = fields.Many2one('cash','Mobile')
    amount = fields.Float('Amount', default = 0.0)
    amount1 = fields.Float('Card Amount', default = 0.0)
    amount2 = fields.Float('Mobile Amount', default = 0.0)
    is_return = fields.Boolean(string = 'Is return', invisible = False, default = False)
    is_hide = fields.Boolean(string = 'Is hide SOL', invisible = False, default = True)
    is_error = fields.Boolean(string = 'Is user Error', invisible = False, default = False)

    @api.one
    def process(self):
        ctx = self.env.context.copy()
        if 'active_id' in ctx:
            sp = self.env['stock.picking'].browse(ctx['active_id'])
            cash_history = self.env['cash.history']
            if self.is_return == True:
                for wizard in self:
                    if wizard.cash and wizard.amount > 0 and not wizard.card and not wizard.mobile:
                        if wizard.cash.amount < wizard.amount:
                            raise ValidationError(
                                _('Not enough money in the cash register.'))
                        # print 'sp.return_cash',sp.return_cash
                        wizard.cash.amount -= wizard.amount
                        created_out1 = cash_history.create({
                            'parent_id': wizard.cash.id,
                            'amount': wizard.amount,
                            'remaining_amount': wizard.cash.amount,
                            'description': u' дугаартай буцаалт [%s]' %sp.name ,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                            })
                        if created_out1:
                            wizard.cash.amount = created_out1.remaining_amount
                    elif wizard.card and wizard.amount1 > 0 and not wizard.cash and not wizard.mobile:
                        if wizard.card.amount < wizard.amount1:
                            raise ValidationError(
                                _('Not enough money in the card register.'))
                        wizard.card.amount -= wizard.amount1
                        created_bank_out = cash_history.create({
                            'parent_id': wizard.card.id,
                            'amount': wizard.amount1,
                            'remaining_amount': wizard.card.amount,
                            'description': u' дугаартай буцаалт [%s]' %sp.name ,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                            })
                        if created_bank_out:
                            wizard.card.amount = created_bank_out.remaining_amount
                    elif wizard.mobile and wizard.amount2 > 0 and not wizard.card and not wizard.cash:
                        if wizard.mobile.amount < wizard.amount2:
                            raise ValidationError(
                                _('Not enough money in the mobile register.'))
                        wizard.mobile.amount -= wizard.amount2
                        created_mobile_out = cash_history.create({
                            'parent_id': wizard.mobile.id,
                            'amount': wizard.amount2,
                            'remaining_amount': wizard.mobile.amount,
                            'description': u' дугаартай буцаалт [%s]' %sp.name ,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                            })
                        if created_mobile_out:
                                wizard.mobile.amount = created_mobile_out.remaining_amount
                    elif wizard.cash and wizard.card and not wizard.mobile:
                        if wizard.cash.amount < wizard.amount:
                            raise ValidationError(
                                _('Not enough money in the cash register.'))
                        wizard.cash.amount -= wizard.amount
                        created_out2 = cash_history.create({
                            'parent_id': wizard.cash.id,
                            'amount': wizard.amount,
                            'remaining_amount': wizard.cash.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_out2:
                            wizard.cash.amount = created_out2.remaining_amount
                        if wizard.card.amount < wizard.amount1:
                            raise ValidationError(
                                _('Not enough money in the card register.'))
                        wizard.card.amount -= wizard.amount1
                        created_bank_out2 = cash_history.create({
                            'parent_id': wizard.card.id,
                            'amount': wizard.amount1,
                            'remaining_amount': wizard.card.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_bank_out2:
                            wizard.card.amount = created_bank_out2.remaining_amount
                    elif wizard.cash and not wizard.card and wizard.mobile:
                        if wizard.cash.amount < wizard.amount:
                            raise ValidationError(
                                _('Not enough money in the cash register.'))
                        wizard.cash.amount -= wizard.amount
                        created_out3 = cash_history.create({
                            'parent_id': wizard.cash.id,
                            'amount': wizard.amount,
                            'remaining_amount': wizard.cash.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_out3:
                            wizard.cash.amount = created_out3.remaining_amount
                        if wizard.mobile.amount < wizard.amount2:
                            raise ValidationError(
                                _('Not enough money in the mobile register.'))
                        wizard.mobile.amount -= wizard.amount2
                        created_mobile_out3 = cash_history.create({
                            'parent_id': wizard.mobile.id,
                            'amount': wizard.amount2,
                            'remaining_amount': wizard.mobile.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_mobile_out3:
                            wizard.mobile.amount = created_mobile_out3.remaining_amount
                    elif not wizard.cash and wizard.card and wizard.mobile:
                        if wizard.card.amount < wizard.amount1:
                            raise ValidationError(
                                _('Not enough money in the card register.'))
                        wizard.card.amount -= wizard.amount1
                        created_card_out4 = cash_history.create({
                            'parent_id': wizard.card.id,
                            'amount': wizard.amount1,
                            'remaining_amount': wizard.card.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_card_out4:
                            wizard.card.amount = created_card_out4.remaining_amount
                        if wizard.mobile.amount < wizard.amount2:
                            raise ValidationError(
                                _('Not enough money in the mobile register.'))
                        wizard.mobile.amount -= wizard.amount2
                        created_mobile_out4 = cash_history.create({
                            'parent_id': wizard.mobile.id,
                            'amount': wizard.amount2,
                            'remaining_amount': wizard.mobile.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_mobile_out4:
                            wizard.mobile.amount = created_mobile_out4.remaining_amount
                    elif wizard.cash and wizard.card and wizard.mobile:
                        if wizard.card.amount < wizard.amount1:
                            raise ValidationError(
                                _('Not enough money in the card register.'))
                        wizard.card.amount -= wizard.amount1
                        created_card_out5 = cash_history.create({
                            'parent_id': wizard.card.id,
                            'amount': wizard.amount1,
                            'remaining_amount': wizard.card.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_card_out5:
                            wizard.card.amount = created_card_out5.remaining_amount
                        if wizard.mobile.amount < wizard.amount2:
                            raise ValidationError(
                                _('Not enough money in the mobile register.'))
                        wizard.mobile.amount -= wizard.amount2
                        created_mobile_out5 = cash_history.create({
                            'parent_id': wizard.mobile.id,
                            'amount': wizard.amount2,
                            'remaining_amount': wizard.mobile.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_mobile_out5:
                            wizard.mobile.amount = created_mobile_out5.remaining_amount
                        if wizard.cash.amount < wizard.amount:
                            raise ValidationError(
                                _('Not enough money in the cash register.'))
                        wizard.cash.amount -= wizard.amount
                        created_cash_out5 = cash_history.create({
                            'parent_id': wizard.cash.id,
                            'amount': wizard.amount,
                            'remaining_amount': wizard.cash.amount,
                            'description': u' дугаартай буцаалт [%s]' % sp.name,
                            'date': datetime.today(),
                            'user': self.env.uid,
                            'action': 'out'

                        })
                        if created_cash_out5:
                            wizard.cash.amount = created_cash_out5.remaining_amount


                    sp.write({'return_cash': sp.return_cash - (wizard.amount + wizard.amount1 + wizard.amount2)})
                stock_move = self.env['stock.move'].search([('picking_id', '=', sp.id)])
                if stock_move:
                    for s in stock_move:
                        if s.origin_returned_move_id:
                            return_stock_move = self.env['stock.move'].search([('id', '=', s.origin_returned_move_id.id)])
                            if return_stock_move:
                                sale_line = self.env['sale.order.line'].search([('id', '=',return_stock_move.procurement_id.sale_line_id.id)])
                                if sale_line:
                                    if self.is_hide:
                                        sale_line.update({'is_return': True})
                                    if self.is_error:
                                        sale_line.update({'is_user_error': True})


            for l in sp:
                if l.location_dest_id.daily_order:
                    for line in sp.move_lines:
                        qty = 0
                        already_sent_qty = 0
                        sent_do = []
                        if l.location_id:
                            wh = self.env['stock.warehouse'].search([('lot_stock_id', '=', l.location_id.id)])[0]
                        main_wh = self.env['stock.warehouse'].search([('main_warehouse', '=', True)])[0]
                        do_obj = self.env['daily.order'].search(
                            [('state', '=', 'pending'), ('product_id', '=', line.product_id.id)])
                        if do_obj:
                            for d in do_obj:
                                already_sent_qty += 1
                                sent_do.append(d.name)
                        if main_wh:
                            qty_obj = self.env['stock.quant'].search([('product_id', '=', line.product_id.id),
                                                                      ('location_id', '=', main_wh.lot_stock_id.id)])
                            for q in qty_obj:
                                qty += q.qty

                            print 'type \n',type(l.min_date),l.min_date
                            vals = {
                                'product_id': line.product_id.id,
                                'location_id': l.location_id.id,
                                'warehouse_id': wh.id,
                                'date': l.min_date,
                                'state': 'draft',
                                'product_qty': qty,
                                'sent_product_qty': already_sent_qty,
                                'sent_daily_order': sent_do,
                                'active': True,
                                'name': u'%s-ны %s дугаартай Бараа шилжүүлэх цэснээс шууд захиалга үүсэв' % (
                                l.min_date, l.name)

                            }
                            do_obj = self.env['daily.order'].create(vals)
                        else:
                            raise ValidationError(_(
                                'Main Warehouse doesnt detected!! \n Configure the main warehouse!'))

            for ml in sp.move_lines:
                quant = self.env['stock.quant'].search([('location_id', '=', sp.location_id.id),
                                                        ('product_id', '=', ml.product_id.id)])
                print ' QUANT___', quant
                qty = 0
                for q in quant:
                    qty += q.qty
                    print ' Q>QTY___', q.qty
                print ' TQTY___', qty
                if qty < ml.product_uom_qty:
                    raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s') % ml.product_id.name_get())
        prcs = super(StockImmediateTransfer, self).process()
        return prcs