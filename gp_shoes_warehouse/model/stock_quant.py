from datetime import datetime

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging

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

class PickingType(models.Model):
    """ The picking type determines the picking view """
    _name = "stock.picking"
    _inherit = "stock.picking"
    _description = "The picking type determines the picking view"

    @api.multi
    def my_function(self, cr, uid, ids, context=None):
        print'IDSSSSSSSSSSSSSSSSSSSSSs',ids
        # if any(expense.state != 'draft' for expense in self):
        #     raise UserError(_("You cannot report twice the same line!"))
        # if len(self.mapped('employee_id')) != 1:
        #     raise UserError(_("You cannot report expenses for different employees in the same report!"))
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': {
                # 'default_expense_line_ids': [line.id for line in self],
                # 'default_employee_id': self[0].employee_id.id,
                # 'default_name': self[0].name if len(self.ids) == 1 else ''
            }
        }
class StockQuant(models.Model):
    """ The picking type determines the picking view """
    _name = "stock.quant"
    _inherit = "stock.quant"
    _description = "The picking type determines the picking view"

    @api.multi
    def my_function2(self):
        for i in self:
            print'IDSSSSSSSSSSSSSSSSSSSSSs',i
        # if any(expense.state != 'draft' for expense in self):
        #     raise UserError(_("You cannot report twice the same line!"))
        # if len(self.mapped('employee_id')) != 1:
        #     raise UserError(_("You cannot report expenses for different employees in the same report!"))
        # return {
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'hr.expense.sheet',
        #     'target': 'current',
        #     'context': {
        #         # 'default_expense_line_ids': [line.id for line in self],
        #         # 'default_employee_id': self[0].employee_id.id,
        #         # 'default_name': self[0].name if len(self.ids) == 1 else ''
        #     }
        # }

