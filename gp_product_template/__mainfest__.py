# -*- coding: utf-8 -*-
##############################################################################

##############################################################################
{
    "name" : "gp_product_template",
    "version" : "1.0",
    "author" : "Arya Stark",
    "description": """
      Grand Plaza  Product
""",
    "website" : False,
    "category" : "Stock",
    "depends" : ['stock','product'],
    "init": [],
    "data" : [
            # 'views/unit_of_measure_view.xml',
            'views/product_template_view.xml',
            'views/product_product_view.xml',
    ],

    "demo_xml": [
    ],
    # 'icon': '/l10n_mn_report_base/static/src/img/asterisk-tech.png',
    "active": False,
    "installable": True,
}