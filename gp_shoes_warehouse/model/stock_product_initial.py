# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2007-2013 Game of Code LLC Co.,ltd (<http://www.erp.mn>). All Rights Reserved
#
#    Email : temuujintsogt@gmail.com
#    Phone : 976 + 99741074,976 + 91586182
#
##############################################################################

from odoo import osv, fields, models
from datetime import date
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.netsvc, decimal, base64, os, time, xlrd
from tempfile import NamedTemporaryFile
from datetime import datetime
import logging
from operator import itemgetter


class StockProductInitial(models.TransientModel):
    _name = 'stock.product.initial'
    _description = 'Stock Product Initial'
    
    date =  fields.Datetime('Date Of Inventory', required=True, default = date.today().strftime('%Y-%m-%d'))
    location_id = fields.Many2one('stock.location', 'Warehouse', required=True, domain = "[('usage', '=', 'internal')]")
    data = fields.Binary('Excel File', required=True)
    type = fields.Selection([('default_code','Default code'),('name','Name')], 'Import type', required=True, default = 'default_code')
    categ_id = fields.Many2one('product.category', u'Барааны ангилал', required=True)
    is_initial = fields.Boolean(u'Эхний үлдэгдэл эсэх',default = False)
    # _defaults = {
    #     'type':'default_code',
    # }

    def import_data(self, wiz):
        # print'\n\n\n Input complete'
        wiz = self
        context = self._context or {}
        product_obj = self.env['product.product']
        product_tmpl_obj = self.env['product.template']
        product_category_obj = self.env['product.category']
        product_uom_obj = self.env['product.uom']
        inventory_obj = self.env['stock.inventory']
        inventory_line_obj = self.env['stock.inventory.line']
        Inventory = self.env['stock.inventory']
        Warehouse = self.env['stock.warehouse']
        immediate = self.env['stock.immediate.transfer']
        product_att = self.env['product.attribute.value']
        product_uoms = {u'ш': 'Unit(s)'}



        fileobj = NamedTemporaryFile('w+')
        fileobj.write(base64.decodestring(wiz.data))
        fileobj.seek(0)

        if not os.path.isfile(fileobj.name):
            raise osv.except_osv(u'Алдаа',
                                 u'Мэдээллийн файлыг уншихад алдаа гарлаа.\nЗөв файл эсэхийг шалгаад дахин оролдоно уу!')
        book = xlrd.open_workbook(fileobj.name)
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        # print '\n\n\n\n ROWS', nrows

        rowi = 1
        if wiz.is_initial is True:
            while rowi < nrows:
                try:
                    row = sheet.row(rowi)
                    code = row[0].value
                    # print'Internal Code \n\n\n',code
                    product_type = 'product'
                    product_supply_method = 'buy'
                    product_procure_method = 'make_to_stock'
                    product_sale_ok = True
                    product_purchase_ok = True
                    product_cost_method = 'average'
                    product_valuation = 'real_time'

                    have_prod = product_obj.search([('default_code', '=', row[0].value)])
                    if not have_prod:
                        print 'Барааны код олдоогүй ба шууд үүсгэх ------------------>', have_prod
                        values_pro_tmp = {
                            'name': sheet.name,
                            'default_code': row[0].value,
                            'categ_id': self.categ_id.id,
                            'standard_price':row[5].value or 9999,
                            'list_price':row[1].value or 9999,
                            'uom_id': 1,
                            'type': product_type,
                            'purchase_line_warn': 'no-message',
                            'sale_line_warn': 'no-message',
                            'tracking': 'none',
                            'purchase_ok': True,
                            'sale_ok': True,
                            'company_id': 1,
                        }
                        # print'\n\n\n\n Values',values_pro_tmp
                        product_tmpl_id = product_tmpl_obj.create(values_pro_tmp)
                        print 'Барааны код олдоогүй ба шууд үүсгэсэн Produc Template ------------------>',product_tmpl_id,row[0].value
                        att_ids = []
                        if row[2].value:
                            product_attribute_value_size = self.env['product.attribute.value'].search(
                                [('name', '=', str(int(row[2].value)))])
                            print'Дараах утгатай %s %s-н id-тай барааны шинж байгаа эсэхийг шалгаж эхэлж байна' %(str(int(row[2].value)),product_attribute_value_size)
                            if product_attribute_value_size:
                                att_ids.append(product_attribute_value_size[0].id)
                            product_att_line = self.env['product.attribute.line'].search(
                                [('product_tmpl_id', '=', product_tmpl_id.id),
                                 ('attribute_id', '=', product_attribute_value_size[0].attribute_id.id)])
                            print'Барааны хувилбар буюу Product Template-д шинжийг нэмж эхэлж байа ====================='
                            if not product_att_line:
                                product_att_line = self.env['product.attribute.line'].create(
                                    {'product_tmpl_id': product_tmpl_id.id,
                                     'attribute_id':
                                         product_attribute_value_size[0].attribute_id.id})
                                print'Нэмэгдсэн Product Attribute Line ------------------->',product_att_line
                            print'Барааны хувилбар баганад үүсгэж эхэлж байна ==========================='
                            product_att_line.value_ids = [(6, 0, product_attribute_value_size.ids)]
                            #                        print'Үүссэн бичиглэлүүд Хувилбар баганад \n', product_att_line.value_ids

                            print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------'
                            if row[4].value:
                                print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------', str(row[4].value)
                                product_attribute_value_season = self.env['product.attribute.value'].search(
                                    [('name', '=', str(row[4].value))])
                                if product_attribute_value_season:
                                    att_ids.append(product_attribute_value_season.id)
                                product_att_line = self.env['product.attribute.line'].search(
                                    [('product_tmpl_id', '=', product_tmpl_id.id),
                                     ('attribute_id', '=', product_attribute_value_season.attribute_id.id)])
                                if not product_att_line:
                                    product_att_line = self.env['product.attribute.line'].create(
                                        {'product_tmpl_id': product_tmpl_id.id,
                                         'attribute_id':
                                             product_attribute_value_season.attribute_id.id})
                                    print'Нэмэгдсэн Product Attribute Line Улирал ------------------->', product_att_line
                                product_att_line.value_ids = [(6, 0, product_attribute_value_season.ids)]


                            product_id = product_obj.create({
                                'product_tmpl_id': product_tmpl_id.id,
                                'active': True,
                                'valuation': product_valuation,
                                'default_code': code,
                                'standart_price': row[5].value or 9999,
                                'attribute_value_ids': [(6, 0, att_ids)],
                            })
                        if row[3].value:
                            print'Агуулахын код'
                            line_data = {
                                'product_qty': row[3].value,
                                'location_id': wiz.location_id.id,
                                'product_id': product_id.id,
                                'product_uom_id': product_id.uom_id.id,
                                'theoretical_qty': 0,
                                'prod_lot_id': None,
                            }
                            # print'\n\n %s \n\n' % line_data
                            inventory_filter = 'product'
                            inventory = Inventory.create({
                                'name': _('INV- %s: %s -%s') %(wiz.location_id,product_id.name,product_id.default_code),
                                'filter': inventory_filter,
                                'product_id': product_id.id,
                                'location_id': wiz.location_id.id,
                                'lot_id': None,
                                'line_ids': [(0, 0, line_data)],
                            })
                            inventory.action_done()
                            print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон :)))*****'
                    else:
                        print'Зүгээр БАРААНЫ ТОО ХЭМЖЭЭГ ӨӨРЧИЛЖ БАЙНА ------------------------------',row
                        att_ids = []
                        check = True
                        product_attribute_value_size = self.env['product.attribute.value'].search(
                            [('name', '=', str(int(row[2].value)))])
                        product_attribute_value_season = self.env['product.attribute.value'].search(
                            [('name', '=', str(row[4].value))])
                        if product_attribute_value_size:
                            att_ids.append(product_attribute_value_size.id)
                            if product_attribute_value_season:
                                att_ids.append(product_attribute_value_season.id)
                        for have in have_prod:
                            # print 'RIGHTTTTTTTTTTTTTTTTTTTTTTTTT\n\n\n'
                            if len(have.attribute_value_ids) == len(att_ids):
                                a = set(have.attribute_value_ids)
                                b = set(att_ids)
                                diff = a.difference(b)
                                # print 'RIGHTTTTTTTTTTTTTTTTTTTTTTTTT\n\n\n',diff
                                if diff is False:
                                    print'-------------------- Энэ бараа байсан ба шууд Барааны тоо хэмжээг л өөрчилсөн',have_prod
                                    if row[3].value:
                                        # print'Агуулахын код'
                                        line_data = {
                                            'product_qty': row[3].value,
                                            'location_id': wiz.location_id.id,
                                            'product_id': have.id,
                                            'product_uom_id': have.uom_id.id,
                                            'theoretical_qty': 0,
                                            'prod_lot_id': None,
                                        }
                                        # print'\n\n %s \n\n' % line_data
                                        inventory_filter = 'product'
                                        inventory = Inventory.create({
                                            'name': _('INV- %s: %s -%s') % (
                                                wiz.location_id, have.name, have.default_code),
                                            'filter': inventory_filter,
                                            'product_id': have.id,
                                            'location_id': wiz.location_id.id,
                                            'lot_id': None,
                                            'line_ids': [(0, 0, line_data)],
                                        })
                                        inventory.action_done()
                                        print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон :)))*****'
                                        check = False
                                        break
                        for have in have_prod:
                            if len(have.attribute_value_ids) == len(att_ids):
                                for a in have.attribute_value_ids:
                                    if a.id in att_ids:
                                        if row[3].value:
                                            # print'Агуулахын код'
                                            line_data = {
                                                'product_qty': row[3].value,
                                                'location_id': wiz.location_id.id,
                                                'product_id': have.id,
                                                'product_uom_id': have.uom_id.id,
                                                'theoretical_qty': 0,
                                                'prod_lot_id': None,
                                            }
                                            # print'\n\n %s \n\n' % line_data
                                            inventory_filter = 'product'
                                            inventory = Inventory.create({
                                                'name': _('INV- %s: %s -%s') % (
                                                    wiz.location_id, have.name, have.default_code),
                                                'filter': inventory_filter,
                                                'product_id': have.id,
                                                'location_id': wiz.location_id.id,
                                                'lot_id': None,
                                                'line_ids': [(0, 0, line_data)],
                                            })
                                            inventory.action_done()
                                            check = False
                                            print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон :)))*****'

                        if check == True:
                            print'ШИНЭЭР БАРАААА ҮҮСГЭЖ бАЙНА 00000000000000000000000000000000000000000000'
                            new_att_ids =[]
                            product_att_line = self.env['product.attribute.line'].search(
                                [('product_tmpl_id', '=', have_prod[0].product_tmpl_id.id),
                                 ('attribute_id', '=', product_attribute_value_size[0].attribute_id.id)])
                            print'Барааны хувилбар буюу Product Template-д шинжийг нэмж эхэлж байа ====================='
                            if not product_att_line:
                                product_att_line = self.env['product.attribute.line'].create(
                                    {'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                                     'attribute_id':
                                         product_attribute_value_size[0].attribute_id.id})
                            new_att_ids.append(product_attribute_value_size[0].id)
                            print'GOYYYYYYYYYYYYYYYYYYYYYYYYYYYy',product_att_line.value_ids
                            if product_attribute_value_size not in product_att_line.value_ids:
                                print'Нэмэгдсэн Product Attribute Line ------------------->', product_att_line
                                print'Барааны хувилбар баганад үүсгэж эхэлж байна ==========================='
                                product_att_line.value_ids = [(6, 0, product_attribute_value_size.ids)]
                            if row[4].value:
                                print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------', str(row[4].value)
                                product_attribute_value_season = self.env['product.attribute.value'].search(
                                    [('name', '=', str(row[4].value))])
                                product_att_line = self.env['product.attribute.line'].search(
                                    [('product_tmpl_id', '=', have_prod[0].product_tmpl_id.id),
                                     ('attribute_id', '=', product_attribute_value_season.attribute_id.id)])
                                if not product_att_line:
                                    product_att_line = self.env['product.attribute.line'].create(
                                        {'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                                         'attribute_id':
                                             product_attribute_value_season.attribute_id.id})

                                    print'Нэмэгдсэн Product Attribute Line Улирал ------------------->', product_att_line
                                new_att_ids.append(product_attribute_value_season[0].attribute_id.id)
                                product_att_line.value_ids = [(6, 0, product_attribute_value_season[0].ids)]

                                # print'\n\nTemka', have
                            product_id = product_obj.create({
                                'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                                'active': True,
                                'valuation': product_valuation,
                                'default_code': code,
                                'standart_price': row[1].value or 9999,
                                'attribute_value_ids': [(6, 0, new_att_ids)],
                            })
                            if row[3].value is not None:
                                print'Агуулахын код'
                                line_data = {
                                    'product_qty': row[3].value,
                                    'location_id': wiz.location_id.id,
                                    'product_id': product_id.id,
                                    'product_uom_id': product_id.uom_id.id,
                                    'theoretical_qty': 0,
                                    'prod_lot_id': None,
                                }
                                # print'\n\n %s \n\n' % line_data
                                inventory_filter = 'product'
                                inventory = Inventory.create({
                                    'name': _('INV-%s: %s - %s') % (
                                        wiz.location_id, product_id.name, product_id.default_code),
                                    'filter': inventory_filter,
                                    'product_id': product_id.id,
                                    'location_id': wiz.location_id.id,
                                    'lot_id': None,
                                    'line_ids': [(0, 0, line_data)],
                                })
                                inventory.action_done()
                                print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ $$$$$$$$$$$$'
                    rowi += 1
                except IndexError:
                    raise UserError(_('Excel sheet must be 6 columned : Code, Price,Size,Qty,Season,Cost: error on row %s ' % rowi))

        else:
            print'Code here for Stock picking and move'
            while rowi < nrows:
                print'ROWWWWWWW %s'%rowi
                try:
                    row = sheet.row(rowi)
                    code = row[0].value
                    product_type = 'product'
                    product_supply_method = 'buy'
                    product_procure_method = 'make_to_stock'
                    product_sale_ok = True
                    product_purchase_ok = True
                    product_cost_method = 'average'
                    product_valuation = 'real_time'

                    have_prod = product_obj.search([('default_code', '=', row[0].value)])
                    if not have_prod:
                        print 'Барааны код олдоогүй ба шууд үүсгэх ------------------>', have_prod
                        values_pro_tmp = {
                            'name': sheet.name,
                            'default_code': row[0].value,
                            'categ_id': self.categ_id.id,
                            'standard_price':row[5].value or 9999,
                            'list_price':row[1].value or 9999,
                            'uom_id': 1,
                            'type': product_type,
                            'purchase_line_warn': 'no-message',
                            'sale_line_warn': 'no-message',
                            'tracking': 'none',
                            'purchase_ok': True,
                            'sale_ok': True,
                            'company_id': 1,
                        }
                        product_tmpl_id = product_tmpl_obj.create(values_pro_tmp)
                        print 'Барааны код олдоогүй ба шууд үүсгэсэн Produc Template ------------------>',product_tmpl_id,row[0].value
                        att_ids = []
                        if row[2].value:
                            product_attribute_value_size = self.env['product.attribute.value'].search(
                                [('name', '=', str(int(row[2].value)))])
                            print'Дараах утгатай %s %s-н id-тай барааны шинж байгаа эсэхийг шалгаж эхэлж байна' %(str(int(row[2].value)),product_attribute_value_size)
                            if product_attribute_value_size:
                                att_ids.append(product_attribute_value_size[0].id)
                            product_att_line = self.env['product.attribute.line'].search(
                                [('product_tmpl_id', '=', product_tmpl_id.id),
                                 ('attribute_id', '=', product_attribute_value_size[0].attribute_id.id)])
                            print'Барааны хувилбар буюу Product Template-д шинжийг нэмж эхэлж байа ====================='
                            if not product_att_line:
                                product_att_line = self.env['product.attribute.line'].create(
                                    {'product_tmpl_id': product_tmpl_id.id,
                                     'attribute_id':
                                         product_attribute_value_size[0].attribute_id.id})
                                print'Нэмэгдсэн Product Attribute Line ------------------->',product_att_line
                            print'Барааны хувилбар баганад үүсгэж эхэлж байна ==========================='
                            product_att_line.value_ids = [(6, 0, product_attribute_value_size.ids)]
                            #                        print'Үүссэн бичиглэлүүд Хувилбар баганад \n', product_att_line.value_ids

                            print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------'
                            if row[4].value:
                                print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------', str(row[4].value)
                                product_attribute_value_season = self.env['product.attribute.value'].search(
                                    [('name', '=', str(row[4].value))])
                                if product_attribute_value_season:
                                    att_ids.append(product_attribute_value_season.id)
                                product_att_line = self.env['product.attribute.line'].search(
                                    [('product_tmpl_id', '=', product_tmpl_id.id),
                                     ('attribute_id', '=', product_attribute_value_season.attribute_id.id)])
                                if not product_att_line:
                                    product_att_line = self.env['product.attribute.line'].create(
                                        {'product_tmpl_id': product_tmpl_id.id,
                                         'attribute_id':
                                             product_attribute_value_season.attribute_id.id})
                                    print'Нэмэгдсэн Product Attribute Line Улирал ------------------->', product_att_line
                                product_att_line.value_ids = [(6, 0, product_attribute_value_season.ids)]


                            product_id = product_obj.create({
                                'product_tmpl_id': product_tmpl_id.id,
                                'active': True,
                                'valuation': product_valuation,
                                'default_code': code,
                                'standart_price': row[5].value or 9999,
                                'attribute_value_ids': [(6, 0, att_ids)],
                            })
                            print'new product: %s'%product_id
                        if row[3].value:
                            wh = Warehouse.search([('lot_stock_id', '=', self.location_id.id)])[0]
                            if wh:
                                incoming_picking_type = self.env['stock.picking.type'].search(
                                    [('warehouse_id', '=', wh.id),
                                     ('code', '=', 'incoming')], limit=1)
                                stock_move = []
                                stock_move.append((0, 0, {'product_id': product_id.id,
                                                          'product_uom_qty':int(row[3].value),
                                                          'ordered_qty':int(row[3].value),
                                                          'state': 'draft',
                                                          'product_uom': product_id.product_tmpl_id.uom_id.id,
                                                          'procure_method': 'make_to_stock',
                                                          'location_id': 8,
                                                          'location_dest_id': self.location_id.id,
                                                          'company_id': 1,
                                                          'date_expected': self.date,
                                                          'date': self.date,
                                                          'name': product_id.product_tmpl_id.name,
                                                          'scrapped': False,
                                                          'to_refund_so': False,
                                                          }))
                                print 'Stock move \n\n\n ----------------',stock_move
                                vals = {
                                    'location_id': 8,
                                    'partner_id':9,
                                    'picking_type_id': incoming_picking_type.id,
                                    'move_type': 'direct',
                                    'company_id': 1,
                                    'location_dest_id': self.location_id.id,
                                    'date': self.date,
                                    'note': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                    'origin': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                    'move_lines': stock_move,
                                }
                                picking_obj = self.env['stock.picking']
                                new_picking = picking_obj.create(vals)
                                print'New Picking -----------------------',new_picking
                                wiz_act = new_picking.do_new_transfer()
                                wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                                wiz.process()
                                print'***** Харилцагчаас худалдан авалт хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон'

                    else:
                        print'Системд бүртгэлтэй байгаа барааны тоо хэмжээг ХА аар нэмж байна------------------------------', row
                        att_ids = []
                        check = True
                        product_attribute_value_size = self.env['product.attribute.value'].search(
                            [('name', '=', str(int(row[2].value)))])
                        product_attribute_value_season = self.env['product.attribute.value'].search(
                            [('name', '=', str(row[4].value))])
                        if product_attribute_value_size:
                            att_ids.append(product_attribute_value_size.id)
                            if product_attribute_value_season:
                                att_ids.append(product_attribute_value_season.id)
                        prod_id = 0
                        for have in have_prod:
                            # print '\n\n for have in have_prod: %s \n\n'%have_prod
                            # print '\n\n have.attribute_value_ids: %s, att_ids: %s \n\n' % (len(have.attribute_value_ids),len(att_ids))

        # len uur bval yaahuu-----------------------------------------------
                            if len(have.attribute_value_ids) == len(att_ids):#lenuur bval yaahuu
                                # print '\n\n a and b len are same \n\n'
                                a = set(have.attribute_value_ids.ids)
                                #ids bhgu bsn bolhoor id.nuud ni adilhan bsn ch gsn zuruutei yum shig ajillaj bsn
                                b = set(att_ids)
                                diff = a.difference(b)
        # diff true bh yum bol yaahiin--------------------------------------
                                if len(diff) == 0:
                                    # print'-------------------- Энэ бараа байсан ба шууд Барааны тоо хэмжээг л өөрчилсөн', have_prod
                                    # if row[2].value:
                                    #     product_attribute_value_size = self.env['product.attribute.value'].search(
                                    #         [('name', '=', str(row[2].value)[:4])])
                                    #     if product_attribute_value_size in have.attribute_value_ids:
                                    print'-------------------РАЗМЕР-------------------------',product_attribute_value_size.name
                                    prod_id = have.id
                                    break
                                else:
                                    print'================================DIFFERENCE TRUE'
                                    prod_id = 0
                        if prod_id == 0:
                            print'\n\n if prod is 0 \n\n'
                            att_id = []
                            if row[2].value:
                                product_attribute_value_size = self.env['product.attribute.value'].search(
                                    [('name', '=', str(int(row[2].value)))])
                                print'\n\n size of this is: %s \n\n'%product_attribute_value_size

                                if product_attribute_value_size:
                                    att_id.append(product_attribute_value_size.id)
                                    print'\n\n att_id: %s \n\n' % att_id
                                else:
                                    vals ={
                                        'name': str(int(row[2].value)),
                                        'attribute_id': 1
                                    }

                                    new_att_value = self.env['product.attribute.value'].create(vals)
                                    print'-------------------РАЗМЕР-------------------------', new_att_value.name
                                    att_id.append(new_att_value.id)
                                if row[4].value:
                                    product_attribute_value_season = self.env['product.attribute.value'].search(
                                            [('name', '=', str(row[4].value))])
                                    print'\n\n season of this is: %s \n\n' % product_attribute_value_season
                                    if product_attribute_value_season:
                                        att_id.append(product_attribute_value_season.id)
                                    else:
                                        raise UserError(
                                            _(
                                                'Ийм нэртэй аттрибут системд бүртгэлгүй байна %s ' % row[4].value))
                                product_id = product_obj.create({
                                    'product_tmpl_id': have[0].product_tmpl_id.id,
                                    'active': True,
                                    'valuation': product_valuation,
                                    'attribute_value_ids': [(6, 0, att_id)],
                                    'default_code': have.default_code
                                })
                                # print'\n\n product_id: %s \n\n'%product_id

                                if row[3].value:
                                    wh = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.location_id.id)])[0]
                                    if wh:
                                        picking_type = self.env['stock.picking.type'].search(
                                            [('warehouse_id', '=', wh.id),
                                             ('code', '=', 'incoming')], limit=1)
                                        stock_move = []
                                        stock_move.append((0, 0, {'product_id': product_id.id,
                                                                  'product_uom_qty': int(row[3].value),
                                                                  'ordered_qty': int(row[3].value),
                                                                  'state': 'draft',
                                                                  'product_uom': have.product_tmpl_id.uom_id.id,
                                                                  'procure_method': 'make_to_stock',
                                                                  'location_id': 8,
                                                                  'location_dest_id': self.location_id.id,
                                                                  'company_id': 1,
                                                                  'date_expected': self.date,
                                                                  'date': self.date,
                                                                  'name': have.product_tmpl_id.name,
                                                                  'scrapped': False,
                                                                  }))
                                        vals = {
                                            'location_id': 8,
                                            'picking_type_id': picking_type.id,
                                            'move_type': 'direct',
                                            'company_id': 1,
                                            'location_dest_id': self.location_id.id,
                                            'date': self.date,
                                            'note': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                            'origin': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                            'move_lines': stock_move,
                                        }
                                        new_picking = self.env['stock.picking'].create(vals)
                                        # print'\n\n new picking: %s \n\n'%new_picking.move_lines
                                        wiz_act = new_picking.do_new_transfer()
                                        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                                        wiz.process()
                                print'***** Харилцагчаас худалдан авалт хийж барааны гарт байгаа хэмжээг нэмлээ БАЙСАН БАРАА with Size'

                        else:
                            att_ids = []
                            print'---------------------Байсан бараа ба шууд ХА аат барааны тоо хэмжээнд нөлөөлж байна'
                            if row[3].value:
                                wh = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.location_id.id)])[0]
                                if wh:
                                    picking_type = self.env['stock.picking.type'].search(
                                        [('warehouse_id', '=', wh.id),
                                         ('code', '=', 'incoming')], limit=1)
                                    stock_move = []
                                    stock_move.append((0, 0, {'product_id': prod_id,
                                                              'product_uom_qty': int(row[3].value),
                                                              'ordered_qty': int(row[3].value),
                                                              'state': 'draft',
                                                              'product_uom': have.product_tmpl_id.uom_id.id,
                                                              'procure_method': 'make_to_stock',
                                                              'location_id': 8,
                                                              'location_dest_id': self.location_id.id,
                                                              'company_id': 1,
                                                              'date_expected': self.date,
                                                              'date': self.date,
                                                              'name': have.product_tmpl_id.name,
                                                              'scrapped': False,
                                                              }))
                                    vals = {
                                        'location_id': 8,
                                        'picking_type_id': picking_type.id,
                                        'move_type': 'direct',
                                        'company_id': 1,
                                        'location_dest_id': self.location_id.id,
                                        'date': self.date,
                                        'note': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                        'origin': u'%s-ны Өдрийн экселээс бараа оруулах цэсээр үүсэв' % (self.date),
                                        'move_lines': stock_move,
                                    }
                                    new_picking = self.env['stock.picking'].create(vals)
                                    print'\n\n new picking: %s \n\n' % new_picking
                                    wiz_act = new_picking.do_new_transfer()
                                    wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                                    wiz.process()
                            print'***** Харилцагчаас худалдан авалт хийж барааны гарт байгаа хэмжээг нэмлээ БАЙСАН БАРАА with Size'

                    rowi += 1
                except IndexError:
                    raise UserError(
                        _('Excel sheet must be 6 columned : Code, Price,Size,Qty,Season,Cost: error on row %s ' % rowi))

        return {
            'name': _(u'Амжилттай импортлолоо'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.product.initial',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target':'new',
            'nodestroy': True,
        }
