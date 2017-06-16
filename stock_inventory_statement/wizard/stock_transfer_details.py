# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.osv import osv
import logging
import time
_logger = logging.getLogger('STOCK')

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    force_date = fields.Datetime('Date')

    def default_get(self, cr, uid, flds, context=None):
        if context is None: context = {}
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        if picking.purchase_id and not picking.purchase_id.cost_ok:
            raise osv.except_osv(_('Warning !'), _('You cannot process incoming shipment until purchase order cost approved!')) 
        
        res = super(stock_transfer_details, self).default_get(cr, uid, flds, context=context)
        
        res.update(force_date=fields.datetime.now())
        return res
    
    @api.one
    def do_detailed_transfer(self):
        _logger.info('stock.transfer_details: do_detailed_transfer starting with %s lines. Picking: %s(id=%s)' %\
                       (len(self.item_ids) + len(self.packop_ids), self.picking_id.name, self.picking_id.id))
        d1 = fields.datetime.now()
        datetime_now = d1.strftime('%Y-%m-%d %H:%M:%S')
        if self.force_date and self.force_date > datetime_now:
            raise osv.except_osv(_('User Error'), _('You cannot process in future time!'))
        processed_ids = []
        # Create new and update existing pack operations
        for lstits in [self.item_ids, self.packop_ids]:
            for prod in lstits:
                force_date = prod.date or datetime_now
                if self.force_date:
                    force_date = self.force_date
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_uom_id.id,
                    'product_qty': prod.quantity,
                    'package_id': prod.package_id.id,
                    'lot_id': prod.lot_id.id,
                    'location_id': prod.sourceloc_id.id,
                    'location_dest_id': prod.destinationloc_id.id,
                    'result_package_id': prod.result_package_id.id,
                    'date': force_date,
                    'owner_id': prod.owner_id.id,
                }
                if prod.packop_id:
                    prod.packop_id.with_context(no_recompute=True).write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = self.picking_id.id
                    #packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    packop_id = self.env['stock.pack.operation'].with_context(no_recompute=True).create(pack_datas)
                    processed_ids.append(packop_id.id)
        # Delete the others
        packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
        packops.with_context(no_recompute=True).unlink()

        # Execute the transfer of the picking
        self.with_context(force_date=self.force_date or datetime_now).picking_id.do_transfer()

        duration = fields.datetime.now() - d1
        log_message = 'stock.transfer_details: do_detailed_transfer finished with %s lines. Picking: %s(id=%s). Duration:%s' %\
                       (len(self.item_ids) + len(self.packop_ids), self.picking_id.name, self.picking_id.id,
                        '%sm%ss' % divmod(duration.days * 86400 + duration.seconds, 60))
        self.picking_id.message_post(body=log_message)
        _logger.info(log_message)
        return True
