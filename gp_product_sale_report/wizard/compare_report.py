# -*- coding: utf-8 -*-
from __builtin__ import xrange

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
    product_category = fields.Many2one('product.category', 'Category')

    def prepare_data(self):

        where_categ = ''
        where_pt = ''
        if self.product_template:
            pt_ids = []
            for i in self.product_template:
                pt_ids.append(i.id)
            where_pt = "AND pt.id in (%s)" % ', '.join(map(repr, tuple(pt_ids)))
        if self.product_category:
            where_categ = "AND pc.id = %s" % self.product_category.id
        print '\n'
        print where_pt
        query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id,
                           coalesce(sum(sq.qty),0) AS qty, pc.name AS category, pc.id AS categ_id,
                           coalesce((SELECT name FROM product_attribute_value pav
                                     JOIN product_attribute_value_product_product_rel pavr
                                     ON pavr.product_attribute_value_id = pav.id
                                     WHERE pavr.product_product_id= pp.id
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
                    GROUP BY pt.id, sq.qty, pp.id, pc.id """

        self.env.cr.execute(query % (str(self.stock_warehouse.lot_stock_id.id), where_pt, where_categ))
        warehouse_data = self.env.cr.dictfetchall()

        product_ids = []
        for wd in warehouse_data:
            product_ids.append(wd['prod_id'])

        where_prods = 'AND pp.id in (%s)' % ', '.join(map(repr, tuple(product_ids)))
        print where_prods

        compare_query = """ SELECT pt.name AS tprod, pt.id AS tprod_id, pp.id AS prod_id,
                                   coalesce(sum(sq.qty),0) AS qty, pc.name AS category, pc.id AS categ_id,
                                   coalesce((SELECT name FROM product_attribute_value pav
                                             JOIN product_attribute_value_product_product_rel pavr
                                             ON pavr.product_attribute_value_id = pav.id
                                             WHERE pavr.product_product_id= pp.id
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
                            GROUP BY pt.id, sq.qty, pp.id, pc.id """

        self.env.cr.execute(compare_query % (str(self.stock_warehouse_compare.lot_stock_id.id), where_pt, where_categ, where_prods))
        compare_warehouse_data = self.env.cr.dictfetchall()
        print '\nPPPPPPPPPpp'
        print compare_warehouse_data

    @api.multi
    def export_report(self):
        self.prepare_data()
        # create workbook
        book = xlwt.Workbook(encoding='utf8')
        # create sheet
        report_name = _('Product sale report')
        sheet = book.add_sheet(report_name)

        # create report object
        report_excel_output = self.env['report.excel.output.extend'].with_context(filename_prefix='ProductSaleReport', form_title=report_name).create({})

        rowx = 0
        colx = 0

        # define title and header
        title_list = [('Baraa1'), ('Baraa2'), ('baihgui baraa')]
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
        sheet.write_merge(rowx, rowx, 0, colx_number, "xoxo", style_filter)
        rowx += 1

        # create title
        sheet.write_merge(rowx, rowx, colx, colx + len(title_list) - 1, 'Үндсэн мэдээлэл', style_title)
        rowx += 1
        for i in xrange(0, len(title_list)):
            sheet.write_merge(rowx, rowx, i, i, title_list[i], style_title)
        rowx += 1

        sheet.write(rowx+1, colx+1, "dflkjdfk", style_footer)

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
