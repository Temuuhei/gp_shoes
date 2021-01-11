# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.http import request
from odoo import http

class ProductProduct(http.Controller):
    @http.route('/get_products_info', type = 'json',auth = 'user')
    def get_products_info(self):
        print ('Yes entered here')
        product_recs = request.env['product.product'].search([('active','=',True),('qty_available','>',0)])
        products = []
        for rec in product_recs:
            if rec.qty_available:
                query = """ SELECT w.id AS location_id, sum(qty) as count_on_hand, pt.list_price as price
                                        FROM stock_quant AS sq
                                            left join product_product AS pp
                                               ON pp.id = sq.product_id
                                            JOIN product_template AS pt
                                               ON pt.id = pp.product_tmpl_id
                                            JOIN stock_warehouse AS w
                                               ON sq.location_id = w.lot_stock_id
                                        WHERE sq.product_id = %s
                                        GROUP BY w.id,pt.list_price
                                       """

                request.env.cr.execute(query % (rec.id,))
                stock_locations = request.env.cr.dictfetchall()
                vals = {
                    'id': rec.id,
                    'name' : rec.name_get(),
                    'barcode' : rec.new_barcode,
                    'price' : int(rec.product_tmpl_id.list_price),
                    'stock_locations' : stock_locations,
                }
                products.append(vals)
        data = {'status':200, 'response' : products, 'message' : 'Done All Products info Returned' }
        return data

class StockQuant(http.Controller):

    @http.route('/stock_locations', type = 'json',auth = 'user')
    def stock_locations(self):
        print ('Yes entered here stock Locations')
        warehouse_recs = request.env['stock.warehouse'].search([('real_warehouse','=',True)])
        warehouses = []
        for rec in warehouse_recs:
            vals = {
                'id': rec.id,
                'name' : rec.name,
            }
            warehouses.append(vals)
        data = {'status':200, 'response' : warehouses, 'message' : 'Returns List of All known locations' }
        return data

    @http.route('/products', type='json', auth='user')
    def products(self, **rec):
        if request.jsonrequest:
            if rec['id']:
                product_recs = request.env['product.product'].search([('active', '=', True), ('qty_available', '>', 0),('id', '=', rec['id'])])
                products = []
                if product_recs:
                    query = """ SELECT w.id AS location_id, sum(qty) as count_on_hand, pt.list_price as price
                                                            FROM stock_quant AS sq
                                                                left join product_product AS pp
                                                                   ON pp.id = sq.product_id
                                                                JOIN product_template AS pt
                                                                   ON pt.id = pp.product_tmpl_id
                                                                JOIN stock_warehouse AS w
                                                                   ON sq.location_id = w.lot_stock_id
                                                            WHERE sq.product_id = %s
                                                            GROUP BY w.id,pt.list_price
                                                           """

                    request.env.cr.execute(query % (rec['id'],))
                    stock_locations = request.env.cr.dictfetchall()
                    vals = {
                        'id': product_recs.id,
                        'name': product_recs.name_get(),
                        'barcode': product_recs.new_barcode,
                        'price': int(product_recs.product_tmpl_id.list_price),
                        'stock_locations': stock_locations,
                    }
                    products.append(vals)
                data = {'status': 200, 'response': products, 'message': 'Done All Products info Returned'}
            else:
                data = {'status': 200, 'response': [], 'message': 'Not Found Products or Unavailable'}
            return data
        product_recs = request.env['product.product'].search([('active', '=', True)])
        products = []
        for rec in product_recs:
            vals = {
                'id': rec.id,
                'name': rec.name_get(),
                            }
            products.append(vals)
        data = {'status': 200, 'response': products, 'message': 'Return List of All Products'}
        return data



class ProductTemplate(models.Model):
    _inherit = "product.template"

    # def compute_default(self):
    #     res = ''
    #     self.env.cr.execute('select max(default_code_integer) from product_template')
    #     max = self.env.cr.fetchone()
    #     init_val = ''
    #     if max:
    #         x = 0
    #         for i in str(max[0]):
    #             x += 1
    #             if x == len(str(max[0])):
    #                 init_val += '1'
    #             else:
    #                 if i == '.':
    #                     init_val += '.'
    #                 else:
    #                     init_val += '0'
    #         fts = max[0] + float(init_val)
    #         res = convert_float_to_string(fts)
    #     return res

    standard_price = fields.Float('Standard price', related='product_variant_ids.new_standard_price', store=True)
    # standard_price_report = fields.Float('Cost', compute='_compute_standard_price',
    #     inverse='_set_standard_price', search='_search_standard_price',
    #     digits=dp.get_precision('Product Price'), groups="base.group_user",
    #     help="Cost of the product, in the default unit of measure of the product.", store=True)
    default_code = fields.Char('default_code', related='product_variant_ids.default_code', store=True)

    # default_code_integer = fields.Integer('Code', compute='_compute_code', store=True)
    # _sql_constraints = [
    #     ('default_code_uniq', 'unique(default_code)', 'Дотоод код давтагдашгүй байх ёстой !'),
    # ]

    # @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    # def _compute_standard_price(self):
    #     for obj in self:
    #         unique_variants = obj.filtered(lambda template: len(template.product_variant_ids) == 1)
    #         for template in unique_variants:
    #             template.standard_price = template.product_variant_ids.standard_price
    #         for template in (obj - unique_variant s):
    #             template.standard_price = 0.0

    # @api.depends('default_code')
    # def _compute_code(self):
    #     integers = ['0','1','2','3','4','5','6','7','8','9']
    #     strings = ''
    #     for obj in self:
    #         if obj.default_code:
    #             for char in obj.default_code:
    #                 if char in integers:
    #                     strings += char
    #                 # else:
    #                 #     if char == '-' and '.' not in strings and strings:
    #                 #         strings += '.'
    #         if strings:
    #             obj.default_code_integer = int(strings)

# def convert_float_to_string(fts):
#     integers = ['.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
#     strings = ''
#     if fts:
#         for char in str(fts):
#             if char in integers:
#                 if char == '.':
#                     strings += '-'
#                 else:
#                     strings += char
#     return strings