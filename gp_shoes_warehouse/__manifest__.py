# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'GP_stock',
    'version' : '1.1',
    'summary': 'Grand Plaza Stock',
    'sequence': 30,
    'description': """
Барааг агуулах болон барааны хувилбараар хайхад хэрэглэнэ
====================
Барааг агуулах болон барааны хувилбараар хайхад хэрэглэнэ
""",
    'category': 'Stock',
    'website': False,
    'images' : False,
    'depends' : ['product','stock','purchase','base'],
    'data': [
        'views/stock_quant.xml',
        'views/stock_product_initial_view.xml',
        'views/product_template.xml',
        'views/res_users.xml',
        'views/product_template_discount_view.xml',
        # 'views/product_initial_insertion_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
    'author': 'Arya Stark',
}
