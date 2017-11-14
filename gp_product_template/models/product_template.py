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
import code

class product_product(osv.osv):
    _inherit = 'product.template'
    
    def _get_uom(self, cr, uid, *args):
        uom_id = self.pool["product.uom"].search(cr, uid, [('is_default','=',True)],limit=1, order='id')[0]
        if uom_id:
            return uom_id
        else:
            return  {}
        
    _columns = {
                'default_code': fields.related('product_variant_ids', 'default_code', type='char', string='Internal Reference',required = True),
                }
    
    _defaults = {
                'hr_expense_ok':True,
                'uom_id': _get_uom,
                'uom_po_id': _get_uom,
             }
    
product_product()