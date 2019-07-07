# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

_logger = logging.getLogger(__name__)


class Quant(models.Model):
    """ Quants are the smallest unit of stock physical instances """
    _name = "stock.quant"
    _inherit = "stock.quant"
    _description = "Quants"

    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, ondelete="restrict", readonly=True, required=True)
    product_tmp_id = fields.Char(string="Product related", related='product_id.product_tmpl_id.name',store=True )

    @api.multi
    def my_function(self):
        first_warehouse = 0
        picking_type = 0
        outgoing_location = 0
        stock_move = []
        for item in self:
            warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', item.location_id.id)], limit=1)
            if first_warehouse == 0:
                first_warehouse = warehouse
                picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', first_warehouse.id),
                                                                      ('code', '=', 'internal')], limit=1)
                outgoing_location = self.env['stock.picking.type'].search([('warehouse_id', '=', first_warehouse.id),
                                                                           ('code', '=', 'outgoing')], limit=1)
            elif first_warehouse.id > 0:
                if not (warehouse == first_warehouse):
                    raise UserError(_("You can create transit order only for one location at time.") )
            stock_move.append((0, 0, {'product_id': item.product_id.id,
                                      'product_uom_qty': 1,
                                      'state': 'draft',
                                      'product_uom': item.product_id.product_tmpl_id.uom_id.id,
                                      'procure_method': 'make_to_stock',
                                      'location_id': item.location_id.id,
                                      'location_dest_id': outgoing_location.id,
                                      'company_id': item.company_id.id,
                                      'date_expected': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'name': item.product_tmp_id,
                                      'scrapped': False,
                                      }))
        if stock_move:
            return \
                {
                    'name': _("Stock Transit Order"),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'target': 'new',
                    'context': {
                        'default_picking_type_id': picking_type.id,
                        'default_location_id': outgoing_location.id,
                        'default_location_dest_id': False,
                        'default_origin':'Тайлбар бичнэ үү...',
                        'default_min_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'default_move_lines': stock_move,
                    }

                }
class Picking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"
    _description = "Transfer"
    _order = "date desc"

    def _default_stock_picking(self):
        # if self.location_id:
            # warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.location_id.id)], limit=1)
        picking_type = self.env['stock.picking.type'].search([('active', '=',True),
                                                              ('code', '=', 'internal'),
                                                             ('warehouse_id', '=',self.env.user.allowed_warehouses[0].id)], limit=1)
        return picking_type

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return self.env.user.allowed_warehouses[0].lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    # @api.model
    # def _default_date(self):
    #     if self.location_dest_id:
    #         min_date = datetime.now() +  timedelta(hours=(8))
    #         print ' Temka \n\n\n\n',min_date
    #         return min_date
        #

    @api.model
    def _compute_your_picking(self):
        if self:
            for s in self:
                # print '\n\n\ncreate: %s, uid; %s\n\n\n'%(s.create_uid,self.env.uid)
                if s.create_uid.id == self.env.uid:
                    s.inv = False
                    # print '\n\n 1-----------'
                else:
                    if  s.state in ('draft','done'):
                        # print '\n\n 2-----------'
                        s.inv = False
                    else:
                        # print '\n\n 3-----------'
                        s.inv = True

                # print '\n\n\n\n\n\n',s.inv
            return True


    location_id = fields.Many2one(
            'stock.location', "Source Location Zone",
            default=_default_location_id,
            readonly=True, required=True,
            states={'draft': [('readonly', False)]}, domain = "[('usage', '=', 'internal')]")
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain = "[('usage', '=', 'internal')]")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Picking Type',
        required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain = "[('code', '=', 'internal')]",
        default= _default_stock_picking)
    inv = fields.Boolean('Create user',compute='_compute_your_picking')


    @api.multi
    @api.onchange('location_dest_id','min_date')
    def onchange_partner_id(self):
        """
        Update the following fields when the location_dest_id is changed:
        - Min date
        """
        values = {}
        if self.location_dest_id:
            for a in self:
                min_date = datetime.now()
                values['min_date'] = min_date
        self.update(values)

    @api.multi
    def do_transfer(self):
        """ If no pack operation, we do simple action_done of the picking.
        Otherwise, do the pack operations. """
        # TDE CLEAN ME: reclean me, please
        self._create_lots_for_picking()

        no_pack_op_pickings = self.filtered(lambda picking: not picking.pack_operation_ids)
        no_pack_op_pickings.action_done()
        other_pickings = self - no_pack_op_pickings
        for picking in other_pickings:
            need_rereserve, all_op_processed = picking.picking_recompute_remaining_quantities()
            todo_moves = self.env['stock.move']
            toassign_moves = self.env['stock.move']

            # create extra moves in the picking (unexpected product moves coming from pack operations)
            if not all_op_processed:
                todo_moves |= picking._create_extra_moves()

            if need_rereserve or not all_op_processed:
                moves_reassign = any(x.origin_returned_move_id or x.move_orig_ids for x in picking.move_lines if
                                     x.state not in ['done', 'cancel'])
                if moves_reassign and picking.location_id.usage not in ("supplier", "production", "inventory"):
                    # unnecessary to assign other quants than those involved with pack operations as they will be unreserved anyways.
                    picking.with_context(reserve_only_ops=True, no_state_change=True).rereserve_quants(
                        move_ids=picking.move_lines.ids)
                picking.do_recompute_remaining_quantities()

            # split move lines if needed
            for move in picking.move_lines:
                rounding = move.product_id.uom_id.rounding
                remaining_qty = move.remaining_qty
                if move.state in ('done', 'cancel'):
                    # ignore stock moves cancelled or already done
                    continue
                elif move.state == 'draft':
                    toassign_moves |= move
                if float_compare(remaining_qty, 0, precision_rounding=rounding) == 0:
                    if move.state in ('draft', 'assigned', 'confirmed'):
                        todo_moves |= move
                elif float_compare(remaining_qty, 0, precision_rounding=rounding) > 0 and float_compare(remaining_qty,
                                                                                                        move.product_qty,
                                                                                                        precision_rounding=rounding) < 0:
                    # TDE FIXME: shoudl probably return a move - check for no track key, by the way
                    new_move_id = move.split(remaining_qty)
                    new_move = self.env['stock.move'].with_context(mail_notrack=True).browse(new_move_id)
                    todo_moves |= move
                    # Assign move as it was assigned before
                    toassign_moves |= new_move
                #edit here by Tr1um
                move.write({'date':picking.min_date})

            # TDE FIXME: do_only_split does not seem used anymore
            if todo_moves and not self.env.context.get('do_only_split'):
                todo_moves.action_done()
            elif self.env.context.get('do_only_split'):
                picking = picking.with_context(split=todo_moves.ids)

            picking._create_backorder()
        return True


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'


    @api.model
    def default_get(self, fields):
        res = super(StockImmediateTransfer, self).default_get(fields)
        if not res.get('pick_id') and self._context.get('active_id'):
            res['pick_id'] = self._context['active_id']
        return res

    @api.multi
    def process(self):
        self.ensure_one()
        # If still in draft => confirm and assign
        if self.pick_id.state == 'draft':
            self.pick_id.action_confirm()
            if self.pick_id.state != 'assigned':
                self.pick_id.action_assign()
                if self.pick_id.state != 'assigned':
                    raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
        for pack in self.pick_id.pack_operation_ids:
            if pack.product_qty > 0:
                pack.write({'qty_done': pack.product_qty})
            else:
                pack.unlink()
        self.pick_id.write({'date_done':self.pick_id.min_date})
        stock_move = self.env['stock.move'].search(
            [('picking_id', '=', self.pick_id.id)])
        if stock_move:
            for sm in stock_move:
                sm.write({'date': self.pick_id.min_date})
                print 'sm date', sm.date

        return self.pick_id.do_transfer()

class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"
    _inherit = "stock.inventory"

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return self.env.user.allowed_warehouses[0].lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))


    location_id = fields.Many2one(
        'stock.location', 'Inventoried Location',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain = "[('code', '=', 'internal')]",
        default=_default_location_id)
