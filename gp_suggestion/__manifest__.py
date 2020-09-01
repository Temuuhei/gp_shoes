# -*- coding: utf-8 -*-

{
    'name': 'Suggestion picking and moves',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module adds suggestion picking by sale orders.
===========================================================================
    """,
    'website': False,
    'depends': ['gp_shoes_sale',
                'gp_shoes_warehouse'],
    'data': [
        # 'security/group.xml',
        # 'wizard/product_sale_report_view.xml',
        # 'report/report_excel_output_view.xml',
        # 'view/sale_order_line_view.xml',
        # 'view/cash.xml',
        # 'view/stock_picking.xml',
        # 'view/product_template.xml',
        # 'wizard/compare_report.xml',
        'view/gp_suggestion_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
    'author': 'Tr1um',
}
