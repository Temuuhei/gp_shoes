# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price_report = fields.Float('Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help="Cost of the product, in the default unit of measure of the product.", store=True)

    default_code_integer = fields.Float('Code', compute='_compute_code', store=True)

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_standard_price(self):
        for obj in self:
            unique_variants = obj.filtered(lambda template: len(template.product_variant_ids) == 1)
            for template in unique_variants:
                template.standard_price = template.product_variant_ids.standard_price
            for template in (obj - unique_variants):
                template.standard_price = 0.0

    @api.depends('default_code')
    def _compute_code(self):
        integers = ['0','1','2','3','4','5','6','7','8','9']
        intStr = ''
        for obj in self:
            for char in obj.default_code:
                if char in integers:
                    intStr += char
            if intStr:
                obj.default_code_integer = int(intStr)