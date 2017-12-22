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
base_style = xlwt.easyxf('align: wrap yes')

class ProductSaleReport(models.TransientModel):
    _name = 'product.sale.report'

    stock_warehouse = fields.Many2one('stock.warehouse', 'Stock warehouse')
    date_from = fields.Date('Date from')
    date_until = fields.Date('Date until')

    @api.multi
    def export_report(self):
        dataDict = {}
        dataLine = []
        dataLineTmpl = []
        initial_date = datetime.strptime(self.date_from, '%Y-%m-%d')
        dateFrom = datetime.strptime(self.date_from, '%Y-%m-%d')
        dateUntil = datetime.strptime(self.date_until, '%Y-%m-%d')
        daily = (((dateFrom - dateUntil).days) * -1) + 1
        self._cr.execute("""SELECT pp.id AS product_id,
                                   pt.default_code AS code,
                                   pt.name AS name,
                                   pp.id AS color,
                                   pt.id AS cost,
                                   COALESCE(SUM(sq.qty), 0) AS quantity,
                                   pt.list_price AS price,
                                   pp.product_tmpl_id AS tmpl,
                                   pt.id AS template
                            FROM stock_quant AS sq
                                JOIN product_product AS pp
                                   ON pp.id = sq.product_id
                                JOIN product_template AS pt
                                   ON pt.id = pp.product_tmpl_id
                            WHERE sq.location_id = %s
                                GROUP BY pp.id, 
                                   pp.default_code,
                                   pt.name,
                                   pt.list_price,
                                   pt.id 
                                   ORDER BY pt.id"""
                         % (self.stock_warehouse.lot_stock_id.id))
        data_quant = self._cr.dictfetchall()

        report_date = ''
        where_date_so = ''
        where_date_sp = ''
        if self.date_from and self.date_until:
            fm_dt = self.date_from+' 00:00:00'
            un_dt = self.date_until+' 23:59:59'
            where_date_so = 'AND so.confirmation_date BETWEEN %s AND %s' %("'"+fm_dt+"'", "'"+un_dt+"'")
            where_date_sp = 'AND sp.min_date BETWEEN %s AND %s' %("'"+fm_dt+"'", "'"+un_dt+"'")
            report_date += self.date_from + ' ~ ' + self.date_until

        if data_quant:
            for each_data in data_quant:
                data = {}
                data_total = {}
                self._cr.execute("""SELECT so.id AS sale_order_id,
                                           so.name AS order_name,
                                           sp.id AS stock_picking_id,
                                           sp.name AS picking_name,
                                           sp.origin AS origin,
                                           so.procurement_group_id AS procurement_group_id,
                                           sp.min_date AS min_date,
                                           sol.qty_delivered AS qty_delivered,
                                           sol.cash_payment AS cash_payment,
                                           sol.card_payment AS card_payment,
                                           sm.product_uom_qty AS product_uom_qty,
                                           sm.product_id AS product_id,
                                           (SELECT name FROM product_attribute_value pav 
                                                JOIN product_attribute_value_product_product_rel pavr 
                                                    ON pavr.product_attribute_value_id = pav.id 
                                            WHERE pavr.product_product_id=%s 
                                                ORDER BY pav.id ASC LIMIT 1) as size
                                    FROM sale_order AS so
                                        JOIN sale_order_line AS sol
                                           ON sol.order_id = so.id
                                        JOIN stock_picking AS sp
                                           ON sp.group_id = so.procurement_group_id
                                        JOIN stock_move AS sm
                                           ON sm.picking_id = sp.id
                                    WHERE so.state = 'done'
                                      AND sp.state = 'done'
                                      AND sol.product_id = %s 
                                      AND so.warehouse_id = %s 
                                      %s"""
                                 % (each_data['product_id'], each_data['product_id'], self.stock_warehouse.id, where_date_so))
                so_data = self._cr.dictfetchall()

                self._cr.execute("""SELECT sp.name AS name,
                                           sp.min_date AS min_date,
                                           sm.product_uom_qty AS in_qty,
                                           sm.product_id AS product_id
                                    FROM stock_picking AS sp
                                        JOIN stock_move AS sm
                                            ON sm.picking_id = sp.id
                                    WHERE sp.state = 'done'
                                          AND sp.location_dest_id = %s
                                          AND sm.product_id = %s
                                      %s"""
                                 % (self.stock_warehouse.lot_stock_id.id, each_data['product_id'], where_date_sp))
                in_data = self._cr.dictfetchall()

                self._cr.execute("""SELECT sp.name AS name,
                                           sp.min_date AS min_date,
                                           sm.product_uom_qty AS out_qty,
                                           sm.product_id AS product_id
                                    FROM stock_picking AS sp
                                        JOIN stock_move AS sm
                                            ON sm.picking_id = sp.id
                                        JOIN stock_location AS sl
                                            ON sl.id = sp.location_id
                                    WHERE sp.state = 'done'
                                          AND sp.location_id = %s
                                          AND sm.product_id = %s
                                      %s"""
                                 % (self.stock_warehouse.lot_stock_id.id, each_data['product_id'], where_date_sp))
                # AND sp.location_dest_id not in (SELECT id FROM stock_location WHERE usage = 'customer')

                out_data = self._cr.dictfetchall()

                # prepare data
                data['code'] = each_data['code']
                data['product'] = each_data['name']
                data['template'] = each_data['template']
                data['color'] = each_data['color']
                data['cost'] = each_data['cost']
                data['quantity'] = each_data['quantity']
                data['price'] = each_data['price']
                data['sub_total'] = {}

                total_in = 0
                total_out = 0
                total_qty = 0
                total_size = ''
                for eachDate in range(0, daily):
                    dataDate = datetime.strftime(dateFrom + timedelta(days=eachDate), '%Y-%m-%d')
                    dataDateTime = dateFrom + timedelta(days=eachDate)
                    inData = ''
                    if in_data:
                        for i in in_data:
                            in_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S')
                            in_dt = in_dt.replace(hour=00, minute=00, second=00)
                            if in_dt == dataDateTime:
                                inData += ',\n%s: %s' % (i['name'], i['in_qty']) if inData else '%s: %s' % (i['name'], i['in_qty'])
                                # total
                                total_in += i['in_qty']
                    outData = ''
                    if out_data:
                        for i in out_data:
                            out_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S')
                            out_dt = out_dt.replace(hour=00, minute=00, second=00)
                            if out_dt == dataDateTime:
                                outData += ',\n%s: %s' % (i['name'], i['out_qty']) if outData else '%s: %s' % (i['name'], i['out_qty'])
                                # total
                                total_out += i['out_qty']
                    data[dataDate] = {'qty_delivered': 0,
                                      'picking_name': '',
                                      'cash_payment': 0,
                                      'card_payment': 0,
                                      'product_uom_qty': 0,
                                      'out_data': outData,
                                      'in_data': inData}
                    if so_data:
                        for soLine in so_data:
                            dt = datetime.strptime(soLine['min_date'], '%Y-%m-%d %H:%M:%S')
                            dt = dt.replace(hour=00, minute=00, second=00)
                            if soLine['order_name'] == soLine['origin'] and dt == dataDateTime and soLine['product_id'] == each_data['product_id']:
                                data[dataDate]['qty_delivered'] += soLine['qty_delivered']
                                data[dataDate]['picking_name'] = soLine['picking_name']
                                data[dataDate]['cash_payment'] += soLine['cash_payment']
                                data[dataDate]['card_payment'] += soLine['card_payment']
                                data[dataDate]['product_uom_qty'] += soLine['product_uom_qty']
                                # total
                                total_size = soLine['size']
                                total_qty += soLine['qty_delivered']
                data['sub_total']['total_in'] = total_in
                data['sub_total']['total_out'] = total_out
                data['sub_total']['total_qty'] = total_qty
                data['sub_total']['total_size'] = total_size
                dataLine.append(data)
        print '\n___ ConditioN ___ ', self.stock_warehouse.lot_stock_id.id, self.stock_warehouse.id
        print '\n___ data ___ '
        for kkk in dataLine:
            print kkk['sub_total']
        print '\n___ data ___ '

        # create workbook
        book = xlwt.Workbook(encoding='utf8')
        # create sheet
        report_name = _('Product sale report')
        sheet = book.add_sheet(report_name)

        # create report object
        report_excel_output = self.env['report.excel.output'].with_context(filename_prefix='ProductSaleReport', form_title=report_name).create({})

        rowx = 0
        colx = 0

        header_daily = []

        for eachDl in range(0, daily):
            dataDate = datetime.strftime(dateFrom + timedelta(days=eachDl), '%Y-%m-%d')
            header_daily.append(dataDate)

        if dataLine:
            dataEachPrdList = []
            dataEachPrdDict = {}
            template = False
            lena = 0
            lenb = len(dataLine)
            for d in dataLine:
                lena += 1
                if template:
                    if template == d['template']:
                        dataEachPrdDict['quantity'] += d['quantity']
                        for everyDl in header_daily:
                            dataEachPrdDict[everyDl]['qty_delivered'] += d[everyDl]['qty_delivered']
                            dataEachPrdDict[everyDl]['cash_payment'] += d[everyDl]['cash_payment']
                            dataEachPrdDict[everyDl]['card_payment'] += d[everyDl]['card_payment']
                            dataEachPrdDict[everyDl]['out_data'] += ",\n"+d[everyDl]['out_data'] if dataEachPrdDict[everyDl]['out_data'] else d[everyDl]['out_data']
                            dataEachPrdDict[everyDl]['in_data'] += ",\n"+d[everyDl]['in_data'] if dataEachPrdDict[everyDl]['in_data'] else d[everyDl]['in_data']
                        dataEachPrdDict['sub_total']['total_qty'] += d['sub_total']['total_qty']
                        dataEachPrdDict['sub_total']['total_in'] += d['sub_total']['total_in']
                        dataEachPrdDict['sub_total']['total_out'] += d['sub_total']['total_out']
                        dataEachPrdDict['sub_total']['total_size'] += ", "+d['sub_total']['total_size'] if dataEachPrdDict['sub_total']['total_size'] else d['sub_total']['total_size']
                    else:
                        dataEachPrdList.append(dataEachPrdDict)
                        dataEachPrdDict = d
                        template = d['template']
                else:
                    dataEachPrdDict = d
                    template = d['template']
                if lenb == lena:
                    dataEachPrdList.append(dataEachPrdDict)
            print '\n11111 ',len(dataLine), len(dataEachPrdList)
            dataLine = dataEachPrdList
        print '\n22222 ',dataLine,'\n'

        # define title and header
        title_list = [('Code'), ('Product'), ('Color'), ('Cost'), ('Quantity'), ('Price')]
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
        sheet.write_merge(rowx, rowx, 0, colx_number, report_date, style_filter)
        rowx += 1

        # create title
        if header_daily:
            coly = len(title_list)
            cola = len(title_list)
            for x in range(0, len(header_daily)):
                cola += 4
                sheet.write_merge(rowx, rowx, coly, cola, header_daily[x], style_title)
                sheet.write_merge(rowx+1, rowx+1, coly, coly, 'Sold quantity', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+1, coly+1, 'Sold cash', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+2, coly+2, 'Sold card', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+3, coly+3, 'Returned', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+4, coly+4, 'From warehouse', style_title)
                cola += 1
                coly = cola
            sheet.write_merge(rowx, rowx, coly, cola+3, 'Total', style_title)
            sheet.write(rowx + 1, coly, 'Sold quantity', style_title)
            sheet.write(rowx + 1, coly + 1, 'Returned', style_title)
            sheet.write(rowx + 1, coly + 2, 'From warehouse', style_title)
            sheet.write(rowx + 1, coly + 3, 'Residual', style_title)
        sheet.write_merge(rowx, rowx, colx, colx + len(title_list) - 1, 'Main info', style_title)
        rowx += 1
        for i in xrange(0, len(title_list)):
            sheet.write_merge(rowx, rowx, i, i, title_list[i], style_title)
        rowx += 1

        num = 0
        if dataLine:
            for line in dataLine:
                sheet.write(rowx, colx, line['code'])
                sheet.write(rowx, colx + 1, line['product'])
                sheet.write(rowx, colx + 2, line['color'])
                sheet.write(rowx, colx + 3, line['cost'])
                sheet.write(rowx, colx + 4, line['quantity'])
                sheet.write(rowx, colx + 5, line['price'])
                if header_daily:
                    colc = len(title_list)
                    cold = len(title_list)
                    for hd in header_daily:
                        cold += 4
                        sheet.write(rowx, colx + colc, line[hd]['qty_delivered'])
                        sheet.write(rowx, colx + colc+1, line[hd]['cash_payment'])
                        sheet.write(rowx, colx + colc+2, line[hd]['card_payment'])
                        sheet.write(rowx, colx + colc+3, line[hd]['out_data'])
                        sheet.write(rowx, colx + colc+4, line[hd]['in_data'])
                        cold += 1
                        colc = cold
                    if line['sub_total']:
                        sheet.write(rowx, colx + colc, line['sub_total']['total_qty'])
                        sheet.write(rowx, colx + colc+1, line['sub_total']['total_out'])
                        sheet.write(rowx, colx + colc+2, line['sub_total']['total_in'])
                        sheet.write(rowx, colx + colc+3, line['sub_total']['total_size'])

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