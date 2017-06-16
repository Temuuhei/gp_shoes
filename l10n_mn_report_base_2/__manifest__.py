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
    "name" : "GP Shoes Report Base TEST",
    "version" : "1.0",
    "author" : "Game of Code",
    "description": """
Customising Sale for GP Shoes
""",
    "website" : False,
    "category" : "Report",
    "depends" : ['report',
                 'mail'
                 ],
    "data" : [
        'wizard/abstract_report_model_view.xml',
        'wizard/merge_data_view.xml',
        'wizard/update_stock_move_float_value_view.xml',

        
    ],
    "active": False,
    "installable": True,
    
}
