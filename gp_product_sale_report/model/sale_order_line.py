# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class SaleOrderDiscount(models.Model):
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _name = 'sale.order.discount'

    discount = fields.Float('All Discount', default=0, track_visibility='always')
    active = fields.Boolean('Active', default=True,track_visibility='always')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Өдөрөөр салгах
    @api.depends('order_id.date')
    def _set_date(self):
        res = {}
        obj = self
        date_object = datetime.strptime(obj[0].order_id.date, '%Y-%m-%d %H:%M:%S')
        self.update({
            'year': date_object.year,
            'month': date_object.month,
            'day': date_object.day,
            'order_date': date_object.date()
        })

    warehouse_id = fields.Many2one('stock.warehouse', related='order_id.warehouse_id',
                                    string='Warehouse', store=True, readonly=True)
    order_date = fields.Date(compute=_set_date, string='Date', readonly=True, store=True)
    year = fields.Integer(compute=_set_date, string='Year', readonly=True, store=True)
    month = fields.Integer(compute=_set_date, string='Month', readonly=True, store=True)
    day = fields.Integer(compute=_set_date, string='Day', readonly=True, store=True)
    date = fields.Integer(compute=_set_date, string='Day', readonly=True, store=True)
    cash_payment = fields.Float(string = 'Cash payment1', default=0)
    card_payment = fields.Float(string = 'Card payment1', default=0)
    mobile_payment = fields.Float('Mobile payment', default=0)
    is_return = fields.Boolean('Is Return',default=False)
    is_user_error = fields.Boolean('Is User Error',default=False)
    is_discount = fields.Boolean('Is Discount',default=False)
    is_boss = fields.Boolean('Is Boss',default=False,copy=False)
    phone_number = fields.Char(string='Утасны дугаар')


    @api.multi
    def to_archive(self):
        self.update({'is_return': True})

    @api.multi
    def to_unarchive(self):
        self.update({'is_return': False})

    # @api.onchange('cash_payment')
    # def onChangeCash(self):
    #     for object in self:
    #         if object.discount > 0:
    #             limit = ((object.product_uom_qty * object.price_unit)*(100 - object.discount))/100
    #             if limit < object.cash_payment:
    #                 object.cash_payment = limit
    #             object.card_payment = limit - object.cash_payment
    #         else:
    #             limit = object.product_uom_qty * object.price_unit
    #             if limit < object.cash_payment:
    #                 object.cash_payment = limit
    #             object.card_payment = limit - object.cash_payment

    @api.onchange('is_discount')
    def onChangeIsDiscount(self):
        discount = self.env['sale.order.discount']
        active_dis = discount.search([('active','=',True)])[0]
        for object in self:
            if object.is_discount:
                if active_dis:
                    for d in active_dis:
                        object.discount = d.discount
                        object.cash_payment = ((object.product_uom_qty * object.price_unit)*(100 - object.discount))/100
            else:
                object.discount = 0
                object.cash_payment = 0



    # @api.onchange('card_payment')
    # def onChangeCard(self):
    #     for object in self:
    #         if object.discount > 0:
    #             limit = ((object.product_uom_qty * object.price_unit)*(100 - object.discount))/100
    #             if limit < object.card_payment:
    #                 object.card_payment = limit
    #             object.cash_payment = limit - object.card_payment
    #         else:
    #             limit = object.product_uom_qty * object.price_unit
    #             if limit < object.card_payment:
    #                 object.card_payment = limit
    #             object.cash_payment = limit - object.card_payment


    @api.model
    def create(self, values):
        create = super(SaleOrderLine, self).create(values)
        discount = self.env['sale.order.discount']
        active_dis = discount.search([('active', '=', True)])[0]
        quant = self.env['stock.quant'].search([('location_id', '=', create.order_id.warehouse_id.lot_stock_id.id),
                                                ('product_id', '=', create.product_id.id)])
        qt = 0
        for q in quant:
            qt += q.qty
        if not quant or qt <= 0 or qt < create.product_uom_qty:
            raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s') % create.name, )
        if not create.cash_payment and not create.card_payment and not create.mobile_payment:
            raise ValidationError(_('You cannot create card and cash payment with 0!'))
        if not create.is_boss:
            if create.price_unit != create.price_original:
                raise ValidationError(
                    _(u'Нэгж үнийг шууд өөрчлөх боломжгүй ба та системээс санал болгосон нэгж ашиглах мөн Хөнгөлөлттэй борлуулалт бол "Хөнгөлөлттэй эсэх" гэсэн талбарыг чеклэж бүртгэнэ үү !'))
            if not create.is_discount and create.price_unit != create.price_original:
                raise ValidationError(_(u'Хөнгөлөлттэй борлуулалт бол бол "Хөнгөлөлттэй эсэх" гэсэн талбарыг чеклэж бүртгэнэ үү !') )
        if active_dis and self.discount > 0:
            for a in active_dis:
                if create.discount != a.discount:
                    raise ValidationError(_(u'Борлуулалтын хөнгөлөлтийг тохируулсан дүнгээс зөрүүтэй байна. Хөнгөлөлттэй эсэх гэсэн талбарыг чеклэж бүртгэнэ үү .Та дараах хөнгөлөлтийг хийж өгнө! : %s') % a.discount, )
        if create and not create.is_boss:
            if create.price_subtotal != create.cash_payment + create.card_payment + create.mobile_payment:
                raise ValidationError(_(u'Касс картын нийлбэр нь бараа борлуулсан орлоготой таарахгүй байна : %s != %s + %s + %s') % (create.price_subtotal,create.cash_payment,create.card_payment,self.mobile_payment))
        return create

    @api.multi
    def write(self, values):
        write = super(SaleOrderLine, self).write(values)
        discount = self.env['sale.order.discount']
        active_dis = discount.search([('active', '=', True)])[0]
        if "product_uom_qty" in values or "product_id" in values:
            quant = self.env['stock.quant'].search([('location_id', '=', self.order_id.warehouse_id.lot_stock_id.id),
                                                    ('product_id', '=', self.product_id.id)])
            if not quant or quant.qty <= 0 or quant.qty < self.product_uom_qty:
                raise ValidationError(_(u'Танай агуулахад тухайн бараа байхгүй байна! : %s')% write.name)
        if not self.cash_payment and not self.card_payment and  not self.mobile_payment:
            raise ValidationError(_('You cannot create card and cash payment with 0!'))
        if not self.is_boss:
            if not self.is_discount and self.price_unit != self.price_original:
                raise ValidationError(
                    _(u'Хөнгөлөлттэй борлуулалт бол бол "Хөнгөлөлттэй эсэх" гэсэн талбарыг чеклэж бүртгэнэ үү !'))
        if not self.is_boss:
            if self.price_unit != self.price_original:
                raise ValidationError(
                    _(
                        u'Нэгж үнийг шууд өөрчлөх боломжгүй ба та системээс санал болгосон нэгж ашиглах мөн Хөнгөлөлттэй борлуулалт бол "Хөнгөлөлттэй эсэх" гэсэн талбарыг чеклэж бүртгэнэ үү !'))
            if active_dis and self.discount > 0:
                for a in active_dis:
                    if self.discount != a.discount:
                        raise ValidationError(_(u'Борлуулалтын хөнгөлөлт нь тохируулсан дүнгээс зөрүүтэй байна. Хөнгөлөлттэй эсэх гэсэн талбарыг чеклэж бүртгэнэ үү .Та дараах хөнгөлөлтийг хийж өгнө! : %s') % a.discount, )
        if self and not self.is_boss:
            if self.price_subtotal != self.cash_payment + self.card_payment + self.mobile_payment:
                raise ValidationError(_(u'Касс,Карт, Мобайлаар төлбөр төлсөн нийлбэр нь бараа борлуулсан орлоготой таарахгүй байна : %s != %s + %s + %s') % (self.price_subtotal,self.cash_payment,self.card_payment,self.mobile_payment))
        return write