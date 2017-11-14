# -*- encoding: utf-8 -*-
##############################################################################
#
#    USI-ERP, Enterprise Management Solution    
#    Copyright (C) 2007-2009 USI Co.,ltd (<http://www.usi.mn>). All Rights Reserved
#    $Id:  $
#
#    ЮүЭсАй-ЕРП, Байгууллагын цогц мэдээлэлийн систем
#    зохиогчийн эрх авсан 2007-2010 ЮүЭсАй ХХК (<http://www.usi.mn>). 
#
#    Зохиогчийн зөвшөөрөлгүйгээр хуулбарлах ашиглахыг хориглоно.
#
#    Харилцах хаяг :
#    Э-майл : info@usi.mn
#    Утас : 976 + 70151145
#    Факс : 976 + 70151146
#    Баянзүрх дүүрэг, 4-р хороо, Энхүүд төв,
#    Улаанбаатар, Монгол Улс
#
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
import time

class stock_print_picking(osv.osv_memory):
    _name = "stock.print.picking"
    _description = "Print Picking"
    
    def report_action(self, cr, uid, ids, context=None):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        if context is None:
            context = {}
        if context.get('active_id', False):
            form = self.browse(cr, uid, ids[0], context=context)
            context = dict(context or {}, active_ids=[context['active_id']])
            ids = context['active_ids']
            if form.type == 'price':
                return self.pool.get("report").get_action(cr, uid, ids, 'l10n_mn_stock.report_picking_in', context=context)
            else:
                return self.pool.get("report").get_action(cr, uid, ids, 'l10n_mn_stock.report_picking_in_cost', context=context)
        return False
    
    def _get_level(self, cr, uid, context=None):
        if self.pool.get('res.users').has_group(cr, uid, 'account.group_account_user') or \
           self.pool.get('res.users').has_group(cr, uid, 'l10n_mn_account.account_view_cost')  :
            level = 'accountant'
        else :
            level = 'manager'
        return level
    
    _columns = {
        'type': fields.selection([('price','Sale Price'),('cost','Cost Price')], 'Income Order Type', required=True),
        'level': fields.selection([('manager','Manager'),('accountant','Accountant')], 'Level'),
    }
    
    _defaults = {
        'type': 'price',
        'level': _get_level,
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
