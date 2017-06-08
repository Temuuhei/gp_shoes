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

    # @api.one
    # @api.depends('is_true', 'product_tmp_id')
    # def compute_is_true(self):
    #     product_tmpl_id = 0
    #     for quant in self:
    #         quant.is_true = True
    #         if quant.product_id:
    #             product_obj = self.env['product.product'].search([('id', '=',quant.product_id )])
    #             print 'Temka\n\n\n\n\n\n',product_obj
    #             quant.product_tmp_id = product_obj.product_tmpl_id

    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, ondelete="restrict", readonly=True, required=True)
    # product_tmp_id = fields.Many2one(
    #     'product.template',related='product_id.product_tmpl_id', string ='Product Template',
    #     index=True, ondelete="restrict", stored = "True" )
    product_tmp_id = fields.Integer(compute='_compute_comment')

    def _compute_comment(self):
        for record in self:
            record.product_tmp_id = record.product_id.product_templ_id.id
            print record.comment
    # is_true = fields.Boolean(string='Is Product Template', compute=compute_is_true, default=False, invisible="1")

# class
#     @api.multi
#     def name_get(self):
#         """ name_get() -> [(id, name), ...]
#
#         Returns a textual representation for the records in ``self``.
#         By default this is the value of the ``display_name`` field.
#
#         :return: list of pairs ``(id, text_repr)`` for each records
#         :rtype: list(tuple)
#         """
#         result = []
#         name = self._rec_name
#         if name in self._fields:
#             convert = self._fields[name].convert_to_display_name
#             for record in self:
#                 result.append((record.id, convert(record[name], record)))
#         else:
#             for record in self:
#                 result.append((record.id, "%s,%s" % (record._name, record.id)))
#
#         return result
#     @api.multi
#     def name_get_product_template(self):
#         for quant in self:
#             if quant.product_id:
#                if quant.product_id.product_tmpl_id