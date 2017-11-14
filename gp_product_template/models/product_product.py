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
    _inherit = 'product.product'    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        res = []
        index = -1
        i = 0
        for arg in args:
            if arg[0] == 'default_code':
                index = i
                break
            i += 1
        if index <> -1:
            args[index:index+1] = ['|',args[index],('product_number',args[index][1],args[index][2])]
        
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
    
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name','')
            code = context.get('display_default_code', True) and d.get('default_code',False) or False
            uom = d.get('uom','')
            category = d.get('category','')
            product_number = d.get('product_number','')
            if code:
                name = '[%s] [%s] [%s] [%s] [%s]' % (category,name,product_number,uom,code)
            ean = context.get('display_ean', False) and d.get('ean',False) or False
            if ean:
                name = '[%s] [%s] [%s] [%s] [%s]' % (category,name,product_number,uom,code)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights(cr, user, "read")
        self.check_access_rule(cr, user, ids, "read", context=context)

        result = []
        for product in self.browse(cr, user, ids, context=context):
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'ean': product.ean13,
                              'default_code': s.product_code or product.default_code,
                              'uom': product.uom_id.name,
                              'category': product.categ_id.name,
                              'product_number': product.product_number,
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'ean': product.ean13,
                          'default_code': product.default_code,
                          'uom': product.uom_id.name,
                          'category': product.categ_id.name,
                          'product_number': product.product_number,
                          }
                result.append(_name_get(mydict))
        return result