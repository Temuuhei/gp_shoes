# -*- coding: utf-8 -*-

{
    'name': 'Product Sale Report',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module adds product sale report by warehouse.
===========================================================================
    """,
    'website': False,
    'depends': ['gp_shoes_sale',
                'gp_shoes_warehouse'],
    'data': [
        'security/group.xml',
        'wizard/product_sale_report_view.xml',
        'report/report_excel_output_view.xml',
        'view/sale_order_line_view.xml',
        'view/cash.xml',
        'view/stock_picking.xml',
        'view/product_template.xml',
        'wizard/compare_report.xml',
        'view/sale_print_quotation.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
    'author': 'Pudge',
}
