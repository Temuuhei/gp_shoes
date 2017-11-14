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

class print_stock_inventory(osv.osv_memory):
    _name = "print.stock.inventory"
    _description = "Print Inventory"
    
    def report_action(self, cr, uid, ids, context=None):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        if context is None:
            context = {}
        if context.get('active_ids', False):
            form = self.read(cr, uid, ids[0], context=context)
            context = dict(context or {}, active_ids=context['active_ids'])
            ids = context['active_ids']
            data = {
                'ids': ids,
                'model': 'stock.inventory',
                'form': form
            }
            data['form']['active_ids'] = context.get('active_ids', False)
            return self.pool.get("report").get_action(cr, uid, [], 'l10n_mn_stock.print_stock_inventory', data=data, context=context)
        return False
    
    '''def _get_level(self, cr, uid, context=None):
        if self.pool.get('res.users').has_group(cr, uid, 'account.group_account_user'):
            level = 'accountant'
        else :
            level = 'manager'
        return level'''
    
    def get_type(self, cr, uid, context=None):
        res = [('price',_('Sale Price')),]
        if self.pool.get('res.users').has_group(cr, uid, 'l10n_mn_account.account_view_cost'):
            res += [('cost',_('Cost Price'))]
        return res
    
    def _get_type(self, cr, uid, context=None):
        if self.pool.get('res.users').has_group(cr, uid, 'l10n_mn_account.account_view_cost'):
            type = 'cost'
        else:
            type = 'price'
        return type
    
    _columns = {
        'type':      fields.selection(get_type, 'Price Type', required=True),
#        'level':        fields.selection([('manager','Manager'),('accountant','Accountant')], 'Level'),
        'serial':       fields.boolean('Show Serial'),
        'available':    fields.boolean('Available'),
        'is_groupby_category': fields.boolean('Is Group by Category'),
    }
    
    _defaults = {
        'type': _get_type,
#        'level': _get_level,
        'serial': False,
        'is_groupby_category': False
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
