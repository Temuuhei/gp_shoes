# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    product_template = fields.Many2one('product.template', 'Main product')
    is_existed_products = fields.Boolean('Байгаа бараануудыг харуулах', default = False)

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

    @api.multi
    def process(self):

        ctx = self.env.context.copy()

        if 'active_id' in ctx:
            sp = self.env['stock.picking'].browse(ctx['active_id'])

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