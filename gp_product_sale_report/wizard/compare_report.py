# -*- coding: utf-8 -*-
from __builtin__ import xrange

import itertools
from odoo import api, fields, models, _
import xlwt
from StringIO import StringIO
import base64
from datetime import datetime, timedelta

style_title = xlwt.easyxf('font: bold 1, name Tahoma, height 160;'
                          'align: vertical center, horizontal center, wrap on;'
                          'borders: left thin, right thin, top thin, bottom thin;'
                          'pattern: pattern solid, pattern_fore_colour gray25, pattern_back_colour black;')
style_filter = xlwt.easyxf('font: bold 1, name Tahoma, height 220;'
                          'align: vertical center, horizontal center, wrap on;')
style_footer = xlwt.easyxf('font: bold 1, name Tahoma, height 160;'
                          'align: vertical center, horizontal center, wrap on;')
base_style = xlwt.easyxf('align: wrap yes')

class CompareProduct(models.TransientModel):
    _name = 'compare.product'

    stock_warehouse = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    stock_warehouse_compare = fields.Many2one('stock.warehouse', 'Compare warehouse', required=True)
    # product_template = fields.Many2one('product.template', 'Product')
    product_template = fields.Many2many('product.template', 'pt_report_rel', 'pt_id', 'cp_id')
    product_category = fields.Many2many('product.category', 'pc_report_rel', 'pc_id', 'cp_id')
    is_second_war = fields.Boolean('Is Second Warehouse')

    def prepare_data(self):

        where_categ = ''
        where_pt = ''
        pc_names = ''
        pt_names = ''
        if self.product_template:
            pt_ids = []
            for i in self.product_template:
                pt_ids.append(i.id)
                pt_names += str(i.name) if not pt_names else ', ' + str(i.name)
            where_pt = "AND pt.id in (%s)" % ', '.join(map(repr, tuple(pt_ids)))
        if self.product_category:
            pc_ids = []
            for x in self.product_category:
                pc_ids.append(x.id)
                pc_names += str(x.name) if not pc_names else ', ' + str(x.name)
            where_categ = "AND pc.id in (%s)" % ', '.join(map(repr, tuple(pc_ids)))
        if  not self.is_second_war:
            query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id, pt.default_code AS dc,
                               coalesce(sum(sq.qty),0) AS qty, pc.name AS ctg, pc.id AS categ_id,
                               coalesce((SELECT name FROM product_attribute_value pav
                                         JOIN product_attribute_value_product_product_rel pavr
                                         ON pavr.product_attribute_value_id = pav.id
                                         WHERE pavr.product_product_id = pp.id
                                         ORDER BY pav.id ASC LIMIT 1),'') as size
                        FROM stock_quant AS sq
                            JOIN product_product AS pp
                               ON pp.id = sq.product_id
                            JOIN product_template AS pt
                               ON pt.id = pp.product_tmpl_id
                            JOIN product_category AS pc
                               ON pc.id = pt.categ_id
                        WHERE sq.qty > 0
                        AND sq.location_id = %s %s %s
                        GROUP BY pt.id, sq.qty, pp.id, pc.id
                        ORDER BY string_to_array(pt.default_code, '-')::int[], pt.id"""

            self.env.cr.execute(query % (str(self.stock_warehouse.lot_stock_id.id), where_pt, where_categ))
            warehouse_data = self.env.cr.dictfetchall()

            product_ids = []
            where_prods = ''
            for wd in warehouse_data:
                product_ids.append(wd['tprod_id'])
            if product_ids:
                where_prods = 'AND pt.id in (%s)' % ', '.join(map(repr, tuple(product_ids)))

            compare_query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id, pt.default_code AS dc,
                                       coalesce(sum(sq.qty),0) AS qty, pc.name AS ctg, pc.id AS categ_id,
                                       coalesce((SELECT name FROM product_attribute_value pav
                                                 JOIN product_attribute_value_product_product_rel pavr
                                                 ON pavr.product_attribute_value_id = pav.id
                                                 WHERE pavr.product_product_id = pp.id
                                                 ORDER BY pav.id ASC LIMIT 1),'') as size
                                FROM stock_quant AS sq
                                    JOIN product_product AS pp
                                       ON pp.id = sq.product_id
                                    JOIN product_template AS pt
                                       ON pt.id = pp.product_tmpl_id
                                    JOIN product_category AS pc
                                       ON pc.id = pt.categ_id
                                WHERE sq.qty > 0
                                AND sq.location_id = %s %s %s %s
                                GROUP BY pt.id, sq.qty, pp.id, pc.id
                                ORDER BY string_to_array(pt.default_code, '-')::int[], pt.id"""

            self.env.cr.execute(compare_query % (str(self.stock_warehouse_compare.lot_stock_id.id), where_pt, where_categ, where_prods))
            compare_warehouse_data = self.env.cr.dictfetchall()
        else:
            query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id, pt.default_code AS dc,
                               coalesce(sum(sq.qty),0) AS qty, pc.name AS ctg, pc.id AS categ_id,
                               coalesce((SELECT name FROM product_attribute_value pav
                                         JOIN product_attribute_value_product_product_rel pavr
                                         ON pavr.product_attribute_value_id = pav.id
                                         WHERE pavr.product_product_id = pp.id
                                         ORDER BY pav.id ASC LIMIT 1),'') as size
                        FROM stock_quant AS sq
                            JOIN product_product AS pp
                               ON pp.id = sq.product_id
                            JOIN product_template AS pt
                               ON pt.id = pp.product_tmpl_id
                            JOIN product_category AS pc
                               ON pc.id = pt.categ_id
                        WHERE sq.qty > 0
                        AND sq.location_id = %s %s %s
                        GROUP BY pt.id, sq.qty, pp.id, pc.id
                        ORDER BY string_to_array(pt.default_code, '-')::int[], pt.id"""

            self.env.cr.execute(query % (str(self.stock_warehouse_compare.lot_stock_id.id), where_pt, where_categ))
            compare_warehouse_data = self.env.cr.dictfetchall()

            product_ids = []
            where_prods = ''
            for wd in compare_warehouse_data:
                product_ids.append(wd['tprod_id'])
            if product_ids:
                where_prods = 'AND pt.id in (%s)' % ', '.join(map(repr, tuple(product_ids)))

            compare_query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id, pt.default_code AS dc,
                                       coalesce(sum(sq.qty),0) AS qty, pc.name AS ctg, pc.id AS categ_id,
                                       coalesce((SELECT name FROM product_attribute_value pav
                                                 JOIN product_attribute_value_product_product_rel pavr
                                                 ON pavr.product_attribute_value_id = pav.id
                                                 WHERE pavr.product_product_id = pp.id
                                                 ORDER BY pav.id ASC LIMIT 1),'') as size
                                FROM stock_quant AS sq
                                    JOIN product_product AS pp
                                       ON pp.id = sq.product_id
                                    JOIN product_template AS pt
                                       ON pt.id = pp.product_tmpl_id
                                    JOIN product_category AS pc
                                       ON pc.id = pt.categ_id
                                WHERE sq.qty > 0
                                AND sq.location_id = %s %s %s %s
                                GROUP BY pt.id, sq.qty, pp.id, pc.id
                                ORDER BY string_to_array(pt.default_code, '-')::int[], pt.id"""

            self.env.cr.execute(compare_query % (str(self.stock_warehouse.lot_stock_id.id), where_pt, where_categ, where_prods))
            warehouse_data = self.env.cr.dictfetchall()


        data = []
        if warehouse_data:
            dict = {}
            for i in warehouse_data:
                exist = False
                for j in compare_warehouse_data:
                    if i['prod_id'] == j['prod_id']:
                        exist = True
                        dict.update({"info2": str(j['size']) + ": " + str(j['qty'])})
                if 'tprod_id' not in dict:
                    dict = i
                    dict.update({"info": str(i['size']) +": "+ str(i['qty'])})
                    if not exist:
                        dict.update({"not_exist_prds": i['size']})
                    data.append(i)
                else:
                    if i['tprod_id'] == dict['tprod_id']:
                        dict['size'] += ", "+i['size'] if dict['size'] else i['size']
                        dict['qty'] += i['qty']
                        dict['info'] += ' '+str(i['size']) +": "+ str(i['qty'])
                        if not exist:
                            if 'not_exist_prds' in dict.keys():
                                dict['not_exist_prds'] += ', ' + str(i['size'])
                            else:
                                dict.update({'not_exist_prds': str(i['size'])})
                    else:
                        dict = i
                        dict.update({"info": str(i['size']) +": "+ str(i['qty'])})
                        if not exist:
                            dict.update({"not_exist_prds": i['size']})
                        data.append(i)

        data_com = []
        if compare_warehouse_data:
            # print 'compare_warehouse_data\n',compare_warehouse_data
            # print 'warehouse_data\n',warehouse_data
            dict_com = {}
            for i in compare_warehouse_data:
                if 'tprod_id' not in dict_com:
                    dict_com = i
                    dict_com.update({"info": str(i['size']) + ": " + str(i['qty'])})
                    data_com.append(i)
                else:
                    if i['tprod_id'] == dict_com['tprod_id']:
                        dict_com['size'] += ", " + i['size'] if dict_com['size'] else i['size']
                        dict_com['qty'] += i['qty']
                        dict_com['info'] += ' ' + str(i['size']) + ": " + str(i['qty'])
                    else:
                        dict_com = i
                        dict_com.update({"info": str(i['size']) + ": " + str(i['qty'])})
                        data_com.append(i)

        # print 'data,data_com\n',data,data_com
        if data and data_com:
            for d in data:
                for cd in data_com:
                    if d['tprod_id'] == cd['tprod_id']:
                        d.update({"compare": cd['info']})
        # print 'data, pt_name, pc_names \n',data, pt_names, pc_names
        return data, pt_names, pc_names


    @api.multi
    def export_report(self):
        data, pt_names, pc_names = self.prepare_data()
        # create workbook
        book = xlwt.Workbook(encoding='utf8')
        # create sheet
        report_name = _('Product compare report')
        sheet = book.add_sheet(report_name)

        # create report object
        report_excel_output = self.env['report.excel.output.extend'].with_context(filename_prefix='ProductCompareReport', form_title=report_name).create({})

        rowx = 0
        colx = 0

        # define title and header
        title_list = [_('Code'), _('Product'), _('Sizes'), _('Quant'), _('Detail'), _('Non exist product'), _('Exist product')]
        colx_number = len(title_list) - 1

        # create header
        report_swh = _('%s') % self.stock_warehouse.name
        sheet.write_merge(rowx, rowx, 1, colx_number, report_swh, style_filter)
        sheet.write
        rowx += 1

        # create name
        sheet.write_merge(rowx, rowx, colx + 1, colx_number, report_name.upper(), style_filter)
        rowx += 1

        # create filters
        if self.product_category:
            sheet.write_merge(rowx, rowx, 0, colx_number, _("Category: ") + pc_names, style_filter)
        rowx += 1
        if self.product_template:
            sheet.write_merge(rowx, rowx, 0, colx_number, _("Filtered by product: ") + pt_names, style_filter)
        rowx += 1

        # create title
        if self.is_second_war:
            sheet.write_merge(rowx, rowx, colx, colx + len(title_list) - 3,
                              _('Warehouse: ') + str(self.stock_warehouse_compare.name), style_title)
            sheet.write_merge(rowx, rowx, colx + len(title_list) - 2, colx + len(title_list) - 1,
                              _('Warehouse compared: ') + str(self.stock_warehouse.name), style_title)
        else:
            sheet.write_merge(rowx, rowx, colx, colx + len(title_list) - 3, _('Warehouse: ')+str(self.stock_warehouse.name), style_title)
            sheet.write_merge(rowx, rowx, colx + len(title_list) - 2, colx + len(title_list) - 1, _('Warehouse compared: ')+str(self.stock_warehouse_compare.name), style_title)
        rowx += 1
        for i in xrange(0, len(title_list)):
            sheet.write_merge(rowx, rowx, i, i, title_list[i], style_title)
        rowx += 1

        if data:
            for d in data:
                sheet.write(rowx, colx, d['dc'], style_footer)
                sheet.write(rowx, colx+1, d['tprod'], style_footer)
                sheet.write(rowx, colx+2, d['size'], style_footer)
                sheet.write(rowx, colx+3, d['qty'], style_footer)
                sheet.write(rowx, colx+4, d['info'], style_footer)
                sheet.write(rowx, colx+5, d['not_exist_prds'] if 'not_exist_prds' in d else '', style_footer)
                sheet.write(rowx, colx+6, d['compare'] if 'compare' in d else '', style_footer)
                rowx += 1
        # prepare file data
        io_buffer = StringIO()
        book.save(io_buffer)
        io_buffer.seek(0)
        filedata = base64.encodestring(io_buffer.getvalue())
        io_buffer.close()

        # set file data
        report_excel_output.filedata = filedata

        # call export function
        return report_excel_output.export_report()
