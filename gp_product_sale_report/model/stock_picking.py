# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    product_template = fields.Many2one('product.template', 'Main product')

    @api.multi
    def insert_products(self):
        product = self.env['product.product']
        print self
        for object in self:
            products = product.search([('product_tmpl_id', '=', object.product_template.id)])
            move_products = []
            if products:
                for m in object.move_lines:
                    move_products.append(m.product_id.id)
                for p in products:
                    if p.id not in move_products:
                        object.move_lines.create({'picking_id': object.id,
                                          'name': p.product_tmpl_id.name,
                                          'product_id': p.id,
                                          'product_uom': p.product_tmpl_id.uom_id.id,
                                          'location_id': object.location_id.id,
                                          'location_dest_id': object.location_dest_id.id})


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
        print '___ PROCESS ___'
        prcs = super(StockImmediateTransfer, self).process()
        sp = self.env['stock.picking'].browse(self.env.context.active_id.id)
        for ml in sp.move_lines:
            quant = self.env['stock.quant'].search([('location_id', '=', self.location_id.id),
                                                ('product_id', '=', ml.product_id.id)])
            if quant.qty < ml.product_uom_qty or not quant.qty:
                raise ValidationError(_('There is no product in your stock or not enough!'), ml.product_id.product_tmpl_id.name)
        return prcs