# -*- coding: utf-8 -*-
from itertools import groupby
from datetime import datetime, timedelta
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from collections import Counter
import odoo.addons.decimal_precision as dp
from __builtin__ import xrange
import xlwt
from StringIO import StringIO
import base64
from datetime import datetime, timedelta

class ProductTemplateDiscountLine(models.Model):
    _name = "product.template.discount.line"

    discount_id = fields.Many2one('product.template.discount', 'Parent Discount')
    product_tmpl_id = fields.Many2one('product.template', 'Product')
    # price_unit = fields.Float('Standard price')
    price_unit = fields.Float('Standard price', related='product_tmpl_id.main_price', store=True)
    price_unit_discount = fields.Float('Discounted price', related='product_tmpl_id.list_price', store=True)

class ProductTemplateDiscount(models.Model):
    _name = "product.template.discount"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date desc'

    @api.multi
    def unlink(self):
        if self.state in ('done'):
            raise UserError(
                _(u'Та батлагдсан хөнгөлөлтийг устгаж болохгүй ба хэрэв та дахин засварлахыг хүсвэл шинэ бүртгэл үүсгэнэ үү'))

    def approve_discounts(self):

        if self.line_id:
            if self.discount > 0 and self.discount <= 100:
                for line in self.line_id:
                    line.product_tmpl_id.write({'list_price': line.product_tmpl_id.main_price - (line.product_tmpl_id.main_price * self.discount/100)})
            else:
                for line in self.line_id:
                    line.product_tmpl_id.write({'list_price': line.product_tmpl_id.main_price})
            self.state = 'done'
        else:
            raise UserError(_(
                'Please select the products in line \n Check!'))

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    date = fields.Date(string='Огноо', required=True, index=True,
                                 copy=False,
                                 default=fields.Datetime.now, readonly = True)
    user_id = fields.Many2one('res.users', string='User', default=_default_user, readonly = True)
    discount = fields.Float('Discount', required = True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ],  string='Төлөв', readonly=True, copy=False, store=True, default='draft')
    line_id = fields.One2many('product.template.discount.line', 'discount_id', string='Discount Lines')
