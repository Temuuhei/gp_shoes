# -*- coding: utf-8 -*-
##############################################################################
#
#    Asterisk Technologies LLC, Enterprise Management Solution    
#    Copyright (C) 2013-2015 Asterisk Technologies LLC (<http://www.erp.mn/, http://asterisk-tech.mn/&gt;). All Rights Reserved
#
#    Email : info@asterisk-tech.mn
#    Phone : 976 + 88005462, 976 + 94100149
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_uom(osv.osv):
    _inherit = 'product.uom'

    _columns = {
                'is_default': fields.boolean('Is Default')
                }
    
product_uom()