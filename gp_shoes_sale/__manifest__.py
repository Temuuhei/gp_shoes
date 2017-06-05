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
    "name" : "GP Shoes Sale",
    "version" : "1.0",
    "author" : "Game of Code",
    "description": """
Customising Sale for GP Shoes
""",
    "website" : False,
    "category" : "Sale",
    "depends" : [
                'sale',
                'account'
                 ],
    "data" : [

        'views/account_payment_term.xml',
        'views/sale_order.xml',
        'views/cash.xml',
        
    ],
    "active": False,
    "installable": True,
    
}
