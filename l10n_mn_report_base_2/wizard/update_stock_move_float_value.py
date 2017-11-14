# -*- coding: utf-8 -*-
##############################################################################
#
#    Asterisk Technologies LLC, Enterprise Management Solution    
#    Copyright (C) 2007-2012 Asterisk Technologies LLC (<http://www.erp.mn>). All Rights Reserved
#
#    Email : unurjargal@asterisk-tech.mn
#    Phone : 976 + 88005462
#
##############################################################################

# from openerp.osv import osv,fields,orm

from openerp.tools.translate import _
import time
import openerp.netsvc, decimal, base64, os, time, xlrd
from tempfile import NamedTemporaryFile
from openerp import api, _, SUPERUSER_ID

from odoo import  fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class update_stock_move_float_value(models.TransientModel):
    _name = 'update.stock.move.float.value'
    _description = 'Update stock move float value'

    def execute_script(self, cr, uid, ids, context={}):
        move_obj = self.pool.get('stock.move')
        product_ids = []
        cr.execute("select pp.id from product_product pp join product_template pt on pt.id = pp.product_tmpl_id "
                    "left join product_uom pu on pu.id = pt.uom_id "
                    "left join product_category pc on pc.id = pt.categ_id "
                    "where pu.id = 1 ")
        fetched = cr.fetchall()
        if fetched != []:
            for pid in fetched:
                product_ids.append(pid[0])

            product_ids = tuple(product_ids)
            cr.execute("select id,product_qty from stock_move where product_id in %s",(product_ids,))
            fetched = cr.fetchall()
            if fetched != []:
                for moveid,product_qty in fetched:
                    cr.execute("update stock_move set product_qty = %s where id = %s",(int(product_qty),moveid))
                    cr.commit()
        return True