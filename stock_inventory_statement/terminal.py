# -*- coding: utf-8 -*-
##############################################################################
#    purevsuren
#
##############################################################################
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import openerp.sql_db
import logging
from datetime import tzinfo, timedelta, datetime, date
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from operator import itemgetter, attrgetter
from time import gmtime, strftime
from openerp import SUPERUSER_ID
_logger = logging.getLogger('terminal.service')

#Inherited Model
class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def odoo_stock_picking_loader(self, cr, uid, ids, context = None):
        
        if context is None:
            context = {}
        
        return True
    
stock_move()
