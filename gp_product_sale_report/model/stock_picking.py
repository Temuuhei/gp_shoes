# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.one
    def _check_return(self):
        print ' Check'
        for sm in self:
            return_sm = self.env['stock.move'].browse(sm.id)
            if return_sm:
                for s in return_sm:
                    if s.origin_returned_move_id:
                        self.write({'is_return':True})
                        print 'Return \n\n',sm.is_return
                        return True
                    else:
                        return False

    product_template = fields.Many2one('product.template', 'Main product')
    is_existed_products = fields.Boolean('Байгаа бараануудыг харуулах', default = False)
    is_return = fields.Boolean(compute = '_check_return',string='Is return', type="boolean", store = True)
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
# class StockMove(models.Model):
#     _inherit = "stock.move"

    # @api.model
    # def create(self, values):
    #     create = super(StockMove, self).create(values)
    #     quant = self.env['stock.quant'].search([('location_id', '=', create.picking_id.location_id.id),
    #                                             ('product_id', '=', create.product_id.id)])
    #     if quant.qty < create.product_uom_qty:
    #         raise ValidationError(_('There is no product in your stock or not enough!'))
    #     return create
    #
    # @api.multi
    # def write(self, values):
    #     write = super(StockMove, self).write(values)
    #     if "product_uom_qty" in values or "product_id" in values:
    #         quant = self.env['stock.quant'].search(
    #             [('location_id', '=', self.picking_id.location_id.id),
    #              ('product_id', '=', self.product_id.id)])
    #         if quant.qty < self.product_uom_qty:
    #             raise ValidationError(_('There is no product in your stock or not enough!'))
    #     return write

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def _check_return(self):
        ctx = self.env.context.copy()
        if 'active_id' in ctx:
            sp = self.env['stock.picking'].browse(ctx['active_id'])
            return_sm  = self.env ['stock.move'].browse(sp.id)
            # print 'sp \n\n',sp,return_sm
            for sm in return_sm:
                if sm.origin_returned_move_id:
                    return True

    cash = fields.Many2one('cash','Cash')
    amount = fields.Float('Amount', default = 0.0)
    is_return = fields.Boolean('Is return', default = _check_return, invisible = False)

    @api.one
    def process(self):
        ctx = self.env.context.copy()
        if 'active_id' in ctx:
            sp = self.env['stock.picking'].browse(ctx['active_id'])
            cash_history = self.env['cash.history']
        for wizard in self:
            if wizard.is_return:
                if wizard.cash.amount < wizard.amount:
                    raise ValidationError(
                        _('Not enough money in the cash register.'))
                sp.write({'return_cash': sp.return_cash - wizard.amount})
                # print 'sp.return_cash',sp.return_cash
                wizard.cash.amount -= wizard.amount
                created_out = cash_history.create({
                    'parent_id': wizard.cash.id,
                    'amount': wizard.amount,
                    'remaining_amount': wizard.cash.amount,
                    'description': u' дугаартай буцаалт [%s]' %sp.name ,
                    'date': datetime.today(),
                    'user': self.env.uid,
                    'action': 'out'

                })
            if created_out:
                wizard.cash.amount = created_out.remaining_amount
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