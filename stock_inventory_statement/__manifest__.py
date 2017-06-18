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
    "name" : "GP Shoes Stock Inventory Statement",
    "version" : "1.0",
    "author" : "Game of Code",
    "description": """
Stock Inventory Statement Wizard
""",
    "website" : False,
    "category" : "Stock",
    "depends" : [
                'stock',
                'l10n_mn_report_base_2'
                 ],
    "data" : [
        'wizard/stock_inventory_statement.xml',

        
    ],
    "active": False,
    "installable": True,
    
}
