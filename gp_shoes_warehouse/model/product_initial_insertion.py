# -*- coding: utf-8 -*-
##############################################################################
#
#    Asterisk Technologies LLC, Enterprise Management Solution    
#    Copyright (C) 2007-2013 Game of Code LLC Co.,ltd (<http://www.erp.mn>). All Rights Reserved
#
#    Email : temuujintsogt@gmail.com
#    Phone : 976 + 99741074,976 + 91586182
#
##############################################################################

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.netsvc, decimal, base64, os, time, xlrd
from tempfile import NamedTemporaryFile
from datetime import datetime
import logging

class ProductDataInitial(models.TransientModel):
    _name = 'product.data.initial'
    _description = 'Product Data Initial'
    
    data = fields.Binary('Product Data File', required=True)
    categ_id = fields.Many2one('product.category',u'Барааны ангилал', required=True)


    def import_data(self, cr, uid, ids, context={}):
        print'\n\n\n INPUT'
        product_obj = self.pool.get('product.product')
        product_tmpl_obj = self.pool.get('product.template')
        product_category_obj = self.pool.get('product.category')
        product_uom_obj = self.pool.get('product.uom')
        
        product_uoms = {u'ш':'Unit(s)'}
        
        form = self
        
        fileobj = NamedTemporaryFile('w+')
        fileobj.write(base64.decodestring(form.data))
        fileobj.seek(0)
        
        if not os.path.isfile(fileobj.name):
            raise osv.except_osv(u'Алдаа',u'Мэдээллийн файлыг уншихад алдаа гарлаа.\nЗөв файл эсэхийг шалгаад дахин оролдоно уу!')
        book = xlrd.open_workbook(fileobj.name)
        
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        
        rowi = 5
        
        while rowi < nrows :
            try:
                row = sheet.row(rowi)                
                product_name_mn = row[1].value                                                                                                                                                                
                product_type = 'product'
                product_supply_method = 'buy'
                product_procure_method = 'make_to_stock'
                product_sale_ok = True
                product_purchase_ok = 'True'
                product_cost_method = 'average'
                product_valuation = 'real_time'
                                                                
                
                product_tmpl_id = product_tmpl_obj.create(cr, uid, {
                    'name': product_name_mn,
                    'categ_id': form.categ_id.id,
                    'standard_price': 0.0,
                    'uom_id': 1,
                    'type': product_type,
                    'supply_method': product_supply_method,
                    'procure_method': product_procure_method,
                    'purchase_ok': product_sale_ok,
                    'sale_ok': product_purchase_ok,
                    'cost_method': product_cost_method,
                    'company_id': 1,
                }, context=context)                
                product_id = product_obj.create(cr, uid, {
                    'product_tmpl_id': product_tmpl_id,
                    'active': True,
                    'valuation': product_valuation,
                }, context=context)                
                
                rowi += 1                
            except IndexError :
                raise osv.except_osv('Error', 'Excel sheet must be 10 columned : error on row %s ' % rowi)
        return True
