# -*- coding: utf-8 -*-
##############################################################################
#
# Game of Code LLC , Enterprise Management Solution
# Copyright (C) 2017 Game of Code LLC . All Rights Reserved #
# Email :
# Phone :
#
##############################################################################
 
{
    "name" : "GP Shoes DailY Order",
    "version" : "1.0",
    "author" : "Arya Stark",
    "description": """
Daily Order
""",
    "website" : False,
    "category" : "Sale",
    "depends" : [
                'gp_shoes_sale',
                'gp_shoes_warehouse',
                 ],
    "data" : [
        # 'wizard/cash_wizard.xml',
        'views/daily_order_view.xml',
        # 'views/sale_order.xml',
        # 'views/cash.xml',
        # 'wizard/sale_order_wizard.xml',

        
    ],
    "active": False,
    "installable": True,
    
}
