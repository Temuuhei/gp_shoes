# -*- coding: utf-8 -*-

from odoo import fields, http, models
from odoo.http import request

ECOMMERCE_WAREHOUSE_CODES = ('HUNSG', 'MAXBA', 'UBBAS', 'UBSF', 'GRAGU', 'TUV')
ECOMMERCE_STOCK_LOCATION_NAME = 'Бараа'

STOCK_LOCATION_QUERY = """
    SELECT sq.product_id, w.id AS location_id, SUM(sq.qty) AS count_on_hand,
           pt.main_price AS price, pt.list_price AS list_price
    FROM stock_quant AS sq
        JOIN product_product AS pp ON pp.id = sq.product_id
        JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
        JOIN stock_warehouse AS w ON sq.location_id = w.lot_stock_id
        JOIN stock_location AS sl ON sq.location_id = sl.id
    WHERE sq.product_id IN %s
      AND w.code IN %s
      AND sl.name = %s
      AND sq.qty > 0
    GROUP BY sq.product_id, w.id, pt.main_price, pt.list_price
    HAVING SUM(sq.qty) > 0
"""

PRODUCT_IDS_QUERY = """
    SELECT DISTINCT sq.product_id
    FROM stock_quant sq
    JOIN stock_warehouse w ON sq.location_id = w.lot_stock_id
    JOIN stock_location sl ON sq.location_id = sl.id
    JOIN product_product pp ON pp.id = sq.product_id
    WHERE w.code IN %s
      AND sl.name = %s
      AND sq.qty > 0
      AND pp.active = true
"""


def _json_response(response, message, status=200):
    return {'status': status, 'response': response, 'message': message}


def _get_ecommerce_product_ids(cr):
    cr.execute(PRODUCT_IDS_QUERY, (ECOMMERCE_WAREHOUSE_CODES, ECOMMERCE_STOCK_LOCATION_NAME))
    return [row[0] for row in cr.fetchall()]


def _get_ecommerce_stock_locations(cr, product_id):
    return _get_ecommerce_stock_locations_map(cr, [product_id]).get(product_id, [])


def _get_ecommerce_stock_locations_map(cr, product_ids):
    if not product_ids:
        return {}
    cr.execute(
        STOCK_LOCATION_QUERY,
        (tuple(product_ids), ECOMMERCE_WAREHOUSE_CODES, ECOMMERCE_STOCK_LOCATION_NAME),
    )
    stock_map = {}
    for row in cr.dictfetchall():
        product_id = row.pop('product_id')
        stock_map.setdefault(product_id, []).append(row)
    return stock_map


def _build_ecommerce_product_vals(product, stock_locations):
    tmpl = product.product_tmpl_id
    return {
        'id': product.id,
        'name': product.name_get(),
        'barcode': product.new_barcode,
        'price': int(tmpl.main_price),
        'price_sale': int(tmpl.list_price),
        'stock_locations': stock_locations,
    }


class ProductProduct(http.Controller):

    @http.route('/get_products_info', type='json', auth='user')
    def get_products_info(self):
        cr = request.env.cr
        product_ids = _get_ecommerce_product_ids(cr)
        stock_map = _get_ecommerce_stock_locations_map(cr, product_ids)
        products = []
        for product in request.env['product.product'].browse(product_ids):
            stock_locations = stock_map.get(product.id)
            if stock_locations:
                products.append(_build_ecommerce_product_vals(product, stock_locations))
        return _json_response(products, 'Done All Products info Returned')


class StockQuant(http.Controller):

    @http.route('/stock_locations', type='json', auth='user')
    def stock_locations(self):
        warehouses = request.env['stock.warehouse'].search([
            ('real_warehouse', '=', True),
            ('code', 'in', list(ECOMMERCE_WAREHOUSE_CODES)),
        ])
        return _json_response(
            [{'id': warehouse.id, 'name': warehouse.name} for warehouse in warehouses],
            'Returns List of All known locations',
        )

    @http.route('/products', type='json', auth='user')
    def products(self, **rec):
        if request.jsonrequest and rec.get('id'):
            product = request.env['product.product'].search([
                ('active', '=', True),
                ('id', '=', rec['id']),
            ], limit=1)
            if not product:
                return _json_response([], 'Not Found Products or Unavailable')
            stock_locations = _get_ecommerce_stock_locations(request.env.cr, product.id)
            products = []
            if stock_locations:
                products.append(_build_ecommerce_product_vals(product, stock_locations))
            return _json_response(products, 'Done All Products info Returned')

        product_ids = _get_ecommerce_product_ids(request.env.cr)
        products = [
            {'id': product.id, 'name': product.name_get()}
            for product in request.env['product.product'].browse(product_ids)
        ]
        return _json_response(products, 'Return List of All Products')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    standard_price = fields.Float(
        'Standard price',
        related='product_variant_ids.new_standard_price',
        store=True,
    )
    default_code = fields.Char(
        'default_code',
        related='product_variant_ids.default_code',
        store=True,
    )
