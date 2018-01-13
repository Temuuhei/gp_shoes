# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def compute_default(self):
        res = ''
        self.env.cr.execute('select max(default_code_integer) from product_template')
        max = self.env.cr.fetchone()
        init_val = ''
        if max:
            x = 0
            for i in str(max[0]):
                x += 1
                if x == len(str(max[0])):
                    init_val += '1'
                else:
                    if i == '.':
                        init_val += '.'
                    else:
                        init_val += '0'
            fts = max[0] + float(init_val)
            res = convert_float_to_string(fts)
        return res

    standard_price = fields.Float('Cost', store=True)
    # standard_price_report = fields.Float('Cost', compute='_compute_standard_price',
    #     inverse='_set_standard_price', search='_search_standard_price',
    #     digits=dp.get_precision('Product Price'), groups="base.group_user",
    #     help="Cost of the product, in the default unit of measure of the product.", store=True)
    default_code_integer = fields.Float('Code', compute='_compute_code', store=True)
    default_code = fields.Char('Default code', default=compute_default)

    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', 'Дотоод код давтагдашгүй байх ёстой !'),
    ]

    # @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    # def _compute_standard_price(self):
    #     for obj in self:
    #         unique_variants = obj.filtered(lambda template: len(template.product_variant_ids) == 1)
    #         for template in unique_variants:
    #             template.standard_price = template.product_variant_ids.standard_price
    #         for template in (obj - unique_variant s):
    #             template.standard_price = 0.0

    @api.depends('default_code')
    def _compute_code(self):
        integers = ['0','1','2','3','4','5','6','7','8','9']
        strings = ''
        for obj in self:
            if obj.default_code:
                for char in obj.default_code:
                    if char in integers:
                        strings += char
                    else:
                        if char == '-' and '.' not in strings and strings:
                            strings += '.'
            if strings:
                obj.default_code_integer = float(strings)

def convert_float_to_string(fts):
    integers = ['.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    strings = ''
    if fts:
        for char in str(fts):
            if char in integers:
                if char == '.':
                    strings += '-'
                else:
                    strings += char
    return strings