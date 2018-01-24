# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

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