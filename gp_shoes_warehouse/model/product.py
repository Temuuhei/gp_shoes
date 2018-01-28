# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
import itertools
import psycopg2
import decimal
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, except_orm
import odoo.addons.decimal_precision as dp

class ProductProduct(models.Model):
    _name = "product.product"
    _description = "Product"
    _inherit = ['product.product']
    _order = 'default_code, id'



    old_code = fields.Float('Old price')
    new_standard_price = fields.Float('Standard price')
    new_barcode = fields.Char('Barcode')
    # _sql_constraints = [
    #     ('old_code', 'unique(old_code)', "Another product already exists with this old code number!"),
    # ]

    # @api.depends('default_code')
    # def _compute_code(self):
    #     for record in self:
    #         if record.default_code:
    #             re.findall("\d+", record.default_code)
    #             match = re.findall("\d+", record.default_code)
    #             for x in match:
    #                 record.old_code = x[0]
    #             print 'OLD CODE \n\n',record.old_code



    @api.multi
    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '%s' % (name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []
        for product in self.sudo():
            # display only the attributes with multiple possible values on the template
            variable_attributes = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id')
            # variant = product.attribute_value_ids._variant_name(variable_attributes)
            # name = variant or "%s %s (%s)" % (product.name,product.default_code, variant) or product.name
            variant = ""
            for i in product.attribute_value_ids:
                if not variant == "":
                    variant += ", "
                variant= variant + i.name
            name = "%s %s (%s)" % (product.name,product.default_code, variant) or product.name
            sellers = []
            if partner_ids:
                sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                if not sellers:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s %s (%s)" % (s.product_name,s.default_code, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          }
                result.append(_name_get(mydict))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['product.product']
            if operator in positive_operators:
                products = self.search([('default_code', '=', name)] + args, limit=limit)
                if not products:
                    products = self.search([('barcode', '=', name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search(args + [('default_code', operator, name)], limit=limit)
                if not limit or len(products) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(products)) if limit else False
                    products += self.search(args + [('name', operator, name), ('id', 'not in', products.ids)],
                                            limit=limit2)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', ('default_code', operator, name), ('name', operator, name)],
                                       limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', '=', res.group(2))] + args, limit=limit)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not products and self._context.get('partner_id'):
                suppliers = self.env['product.supplierinfo'].search([
                    ('name', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)])
                if suppliers:
                    products = self.search([('product_tmpl_id.seller_ids', 'in', suppliers.ids)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()

class ProductTemplate(models.Model):
    _inherit = "product.template"
    type = fields.Selection([
        ('consu', _('Consumable')),
        ('service', _('Service')),
        ('product', _('Stockable Product'))], string='Product Type', default='product', required=True,
        help='A stockable product is a product for which you manage stock. The "Inventory" app has to be installed.\n'
             'A consumable product, on the other hand, is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.\n'
             'A digital content is a non-material product you sell online. The files attached to the products are the one that are sold on '
             'the e-commerce such as e-books, music, pictures,... The "Digital Product" module has to be installed.')
    barcode = fields.Char('Barcode', store=True)

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', 'Баркод код давтагдашгүй байх ёстой !'),
    ]

    @api.multi
    def create_variant_ids(self):
        Product = self.env["product.product"]
        for tmpl_id in self.with_context(active_test=False):
            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            variant_alone = tmpl_id.attribute_line_ids.filtered(lambda line: len(line.value_ids) == 1).mapped('value_ids')
            for value_id in variant_alone:
                updated_products = tmpl_id.product_variant_ids.filtered(lambda product: value_id.attribute_id not in product.mapped('attribute_value_ids.attribute_id'))
                updated_products.write({'attribute_value_ids': [(4, value_id.id)]})

            # list of values combination
            existing_variants = [set(variant.attribute_value_ids.ids) for variant in tmpl_id.product_variant_ids]
            variant_matrix = itertools.product(*(line.value_ids for line in tmpl_id.attribute_line_ids if line.value_ids and line.value_ids[0].attribute_id.create_variant))
            variant_matrix = map(lambda record_list: reduce(lambda x, y: x+y, record_list, self.env['product.attribute.value']), variant_matrix)
            to_create_variants = filter(lambda rec_set: set(rec_set.ids) not in existing_variants, variant_matrix)

            # check product
            variants_to_activate = self.env['product.product']
            variants_to_unlink = self.env['product.product']
            for product_id in tmpl_id.product_variant_ids:
                if not product_id.active and product_id.attribute_value_ids in variant_matrix:
                    variants_to_activate |= product_id
                elif product_id.attribute_value_ids not in variant_matrix:
                    variants_to_unlink |= product_id
            if variants_to_activate:
                variants_to_activate.write({'active': True})
            default_code = ''
            default_code = tmpl_id.default_code
            # create new product
            for variant_ids in to_create_variants:
                new_variant = Product.create({
                    'product_tmpl_id': tmpl_id.id,
                    'default_code': default_code,
                    'attribute_value_ids': [(6, 0, variant_ids.ids)]
                })
                # unlink or inactive product
                for variant in variants_to_unlink:
                    try:
                        with self._cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                            variant.unlink()
                    # We catch all kind of exception to be sure that the operation doesn't fail.
                    except (psycopg2.Error, except_orm):
                        variant.write({'active': False})
                        pass
            return True

    def action_reload_product_tmp(self):
        product_obj = self.env['product.product'].search([('active','=',True)])
        product_tmp_obj = self.env['product.template']
        for pro in product_obj:
            if pro.default_code and pro.product_tmpl_id:
                # float_code = int(pro.default_code)
                print 'Default code',pro.default_code
                # print 'Float Default code \n',float_code
                tmp = product_tmp_obj.search([('id','=',pro.product_tmpl_id.id)])
                if tmp and tmp.default_code == '':
                    tmp.write({'default_code':pro.default_code})
                else:
                    rm = product_obj.search ([('default_code','=','')])
                if not pro.attribute_value_ids:
                    print 'Идэвхигүй болгож буй бараа -----',pro.name
                    pro.write({'active': False})

                    # if rm:
                    #      rm.unlink()

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            self.with_context(active_test=False).mapped('product_variant_ids').write({'active': vals.get('active')})
        if 'default_code' in vals:
            products = self.env['product.product'].search([('active','=',True),('product_tmpl_id','=',self.id)])
            if products:
                for pro in products:
                    pro.write({'default_code': vals.get('default_code')})
        res = super(ProductTemplate, self).write(vals)
        return res

    @api.multi
    def _set_template_price(self):
        if self._context.get('uom'):
            for template in self:
                value = self.env['product.uom'].browse(self._context['uom'])._compute_price(template.price,
                                                                                            template.uom_id)
                template.write({'list_price': value})
        else:
            self.write({'list_price': self.price})

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_standard_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) >= 1)
        for template in unique_variants:
            for tmp in self.product_variant_ids:
                tmp.standard_price =  self.standard_price
                # self.standard_price = tmp.standard_price
            # template.standard_price = template.product_variant_ids.standard_price
        for template in (self - unique_variants):
            template.standard_price = 0.0

    @api.one
    def _set_standard_price(self):
        if len(self.product_variant_ids) >= 1:
            for tmp in self.product_variant_ids:
                tmp.standard_price = self.standard_price

    def _search_standard_price(self, operator, value):
        products = self.env['product.product'].search([('standard_price', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]


class ProductAttributevalue(models.Model):
    _name = "product.attribute.value"
    _order = 'sequence'
    _inherit = ['product.attribute.value']
    _order = 'name'