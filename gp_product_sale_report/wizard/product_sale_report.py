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

class ProductSaleReport(models.TransientModel):
    _name = 'product.sale.report'

    stock_warehouse = fields.Many2one('stock.warehouse', 'Stock warehouse', required=True)
    date_from = fields.Date('Date from', required=True)
    date_until = fields.Date('Date until', required=True)
    show_cost = fields.Boolean('Show cost')


    @api.multi
    def export_report(self):
        dataDict = {}
        dataLine = []
        dataLineTmpl = []
        initial_date = datetime.strptime(self.date_from, '%Y-%m-%d')
        dateFrom = datetime.strptime(self.date_from, '%Y-%m-%d')
        dateUntil = datetime.strptime(self.date_until, '%Y-%m-%d')
        daily = (((dateFrom - dateUntil).days) * -1) + 1

        location = '('+str(self.stock_warehouse.lot_stock_id.id)+')'
        report_date = ''
        where_date_so = ''
        where_date_sp = ''
        if self.date_from and self.date_until:
            fm_dt = self.date_from + ' 00:00:00'
            un_dt = self.date_until + ' 23:59:59'
            fm_dtdt = datetime.strptime(fm_dt, "%Y-%m-%d %H:%M:%S")
            un_dtdt = datetime.strptime(un_dt, "%Y-%m-%d %H:%M:%S")
            fm_dt = fm_dtdt.strftime("%Y-%m-%d %H:%M:%S")
            un_dt = un_dtdt.strftime("%Y-%m-%d %H:%M:%S")
            initial_date_where = " and sm.date < '%s' " % (fm_dt)
            last_date_where = " and sm.date < '%s' " % (un_dt)
            where_date_so = 'AND so.date BETWEEN %s AND %s' % ("'" + fm_dt + "'", "'" + un_dt + "'")
            where_date_sp = 'AND sp.min_date >= %s AND sp.min_date <= %s' % ("'" + fm_dt + "'", "'" + un_dt + "'")
            where_date_sm = 'AND sm.date >= %s AND sm.date <= %s' % ("'" + fm_dt + "'", "'" + un_dt + "'")
            report_date += self.date_from + ' ~ ' + self.date_until
        # check_picking = []
        # self._cr.execute("""SELECT  sm.product_id AS product_id,
        #                             pt.id AS tmpl,
        #                             sum(sm.product_uom_qty) AS qty
        #                               FROM stock_picking AS sp
        #                               LEFT JOIN stock_move AS sm
        #                                 ON sp.id = sm.picking_id
        #                               LEFT JOIN product_product AS pp
        #                                 ON pp.id = sm.product_id
        #                               LEFT join product_template AS pt
        #                                 ON pp.product_tmpl_id = pt.id
        #                               WHERE
        #                                 sp.state = 'done'
        #                                 AND sm.location_id = %s %s
        #                              GROUP BY sm.product_id,
        #                                         pt.id"""
        #                  % (self.stock_warehouse.lot_stock_id.id, where_date_sp))
        # check_picking_move = self._cr.dictfetchall()
        # if check_picking_move:
        #     for s in check_picking_move:
        #         check_picking.append(s['product_id'])

        # Одоо байгаа барааны мэдээлэл
        self._cr.execute("""SELECT pp.id AS product_id,
                                   pt.default_code AS code,
                                   pt.name AS name,
                                   pt.id AS color,
                                   pt.standard_price AS cost,
                                   COALESCE(SUM(sq.qty), 0) AS quantity,
                                   pt.list_price AS price,
                                   pp.product_tmpl_id AS tmpl,
                                   pt.id AS template,
                                   pt.barcode AS barcode,
                                   pt.main_price AS main_price,
                                   coalesce((SELECT name FROM product_attribute_value pav
                                        JOIN product_attribute_value_product_product_rel pavr
                                            ON pavr.product_attribute_value_id = pav.id
                                    WHERE pavr.product_product_id= pp.id
                                        ORDER BY pav.id ASC LIMIT 1),'') as size,
                                   (SELECT coalesce(sum(query.qty),0) as qty
                                    FROM ((SELECT coalesce(sum(sm.product_qty),0) AS qty
                                           FROM stock_move sm
                                                JOIN product_product ppp
                                                    ON (pp.id=sm.product_id)
                                           WHERE sm.state='done'
                                                 AND sm.location_id not in %s
                                                 AND sm.location_dest_id in %s
                                                 AND ppp.id = pp.id %s
                                           GROUP BY sm.product_id)
                                          union
                                          (SELECT -coalesce(sum(sm.product_qty),0) AS qty
                                           FROM stock_move sm
                                                JOIN product_product ppp ON (pp.id=sm.product_id)
                                           WHERE sm.state='done'
                                                 AND sm.location_id in %s
                                                 AND sm.location_dest_id not in %s
                                                 AND ppp.id = pp.id %s
                                           GROUP BY sm.product_id)
                                         ) AS query ) as firstqty,

                                      (SELECT coalesce(sum(last_query.qty),0) as qty
                                    FROM ((SELECT coalesce(sum(sm.product_qty),0) AS qty
                                           FROM stock_move sm
                                                JOIN product_product ppp
                                                    ON (pp.id=sm.product_id)
                                           WHERE sm.state='done'
                                                 AND sm.location_id not in %s
                                                 AND sm.location_dest_id in %s
                                                 AND ppp.id = pp.id %s
                                           GROUP BY sm.product_id)
                                          union
                                          (SELECT -coalesce(sum(sm.product_qty),0) AS qty
                                           FROM stock_move sm
                                                JOIN product_product ppp ON (pp.id=sm.product_id)
                                           WHERE sm.state='done'
                                                 AND sm.location_id in %s
                                                 AND sm.location_dest_id not in %s
                                                 AND ppp.id = pp.id %s
                                           GROUP BY sm.product_id)
                                         ) AS last_query ) as last_qty


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
                                ORDER BY string_to_array(pt.default_code, '-')::int[], pt.id,coalesce((SELECT name FROM product_attribute_value pav
                                        JOIN product_attribute_value_product_product_rel pavr
                                            ON pavr.product_attribute_value_id = pav.id
                                    WHERE pavr.product_product_id= pp.id
                                        ORDER BY pav.id ASC LIMIT 1),'') ASC"""
                         % (location,location,initial_date_where,
                            location,location,initial_date_where,
                            location, location, last_date_where,
                            location, location, last_date_where,
                            self.stock_warehouse.lot_stock_id.id))

        data_quant = self._cr.dictfetchall()


        # тухайн бараа нь тайлант хугацааны эхний үлдэгдлээр байхгүй байгаад тухайн хугацааны хооронд байсан ба одоогийн байдлаар зарагдсан(хасагдсан) барааг харуулах
        # Тухайн агуулахаас гарсан хөдөлгөөн дээр тулгуурлаж
        check_dur_move = []
        self._cr.execute("""SELECT  sm.product_id AS product_id,
                                                           pt.id AS tmpl,
                                                           sum(sm.product_uom_qty) AS qty
                                                             FROM stock_move AS sm
                                                             LEFT JOIN product_product AS pp
                                                               ON pp.id = sm.product_id
                                                             LEFT join product_template AS pt
                                                               ON pp.product_tmpl_id = pt.id
                                                             WHERE
                                                               sm.state = 'done'
                                                               AND sm.location_id = %s
                                                                %s
                                                            GROUP BY sm.product_id,
                                                                       pt.id"""
                         % (self.stock_warehouse.lot_stock_id.id, where_date_sm))
        check_dur_move_list = self._cr.dictfetchall()
        if check_dur_move_list and data_quant:
            for cdm in check_dur_move_list:
                check_dur_move.append(cdm['product_id'])





        #Тухайн тайлант хугацаанд ямар ч гүйлгээ хийгдээгүй мөртлөө нөөц нь байсан ба яг одоогийн байдлаар байхгүй байгаа бараа тайланд харагдахгүй байсан учир тухайн барааг олох query г бичиж өгөв
        self._cr.execute("""SELECT ppp.id as product_id, ppp.default_code as code, coalesce(sum(sm.product_qty),0) AS qty
                                   FROM stock_move sm
                                        JOIN product_product ppp
                                            ON ppp.id=sm.product_id
                                   WHERE sm.state='done'
                                         AND sm.location_id not in %s
                                         AND sm.location_dest_id in %s
                                         %s
                                   GROUP BY ppp.id,ppp.default_code
                                  union
                                  SELECT ppp.id as product_id, ppp.default_code as code, -coalesce(sum(sm.product_qty),0) AS qty
                                   FROM stock_move sm
                                        JOIN product_product ppp ON (ppp.id=sm.product_id)
                                   WHERE sm.state='done'
                                         AND sm.location_id in %s
                                         AND sm.location_dest_id not in %s
                                         %s

                                   GROUP BY ppp.id,ppp.default_code
                                   ORDER BY code
                                            """
                         % (location,location,initial_date_where,
                            location, location, initial_date_where))
        check_was_but_not_now = self._cr.dictfetchall()
        dq_last = []
        dq_last2 = []
        was_but_not_now = []
        if data_quant:
            for dql in data_quant:
                dq_last.append(dql['product_id'])

        # Эхний үлдэгдэл болон эцсийн үлдэгдэл байхгүй барааг тайлант хугацаанд хөдөлгөөн орсон бол энд нэмэв by out
        if check_dur_move_list:
            for cd in check_dur_move_list:
                # for d in data_quant:
                if cd['product_id'] not in dq_last:
                    self._cr.execute("""SELECT sm.product_id as product_id, ppp.default_code as code, coalesce(sum(sm.product_qty),0) AS qty
                                                                        FROM stock_move sm
                                                                            JOIN product_product ppp
                                                                            ON ppp.id=sm.product_id
                                                                        WHERE sm.state='done'
                                                                             AND sm.location_id not in %s
                                                                             AND sm.location_dest_id in %s
                                                                             AND sm.product_id = %s
                                                                             %s
                                                            GROUP BY sm.product_id,ppp.default_code
                                                            union
                                                            SELECT sm.product_id as product_id, ppp.default_code as code, -coalesce(sum(sm.product_qty),0) AS qty
                                                                        FROM stock_move sm
                                                                            JOIN product_product ppp ON (ppp.id=sm.product_id)
                                                                        WHERE sm.state='done'
                                                                             AND sm.location_id in %s
                                                                             AND sm.location_dest_id not in %s
                                                                             AND sm.product_id = %s
                                                                             %s
                                                            GROUP BY sm.product_id,ppp.default_code"""
                                     % (location, location, cd['product_id'], last_date_where,
                                        location, location, cd['product_id'], last_date_where))
                    check_last_qty = self._cr.dictfetchall()
                    last_qty = 0.0
                    if check_last_qty:
                        for i in check_last_qty:
                            last_qty += i['qty']
                    product_was_obj = self.env['product.product'].browse(cd['product_id'])
                    self._cr.execute("""SELECT name FROM product_attribute_value pav
                                                                                                               JOIN product_attribute_value_product_product_rel pavr
                                                                                                                   ON pavr.product_attribute_value_id = pav.id
                                                                                                           WHERE pavr.product_product_id = %s
                                                                                                               ORDER BY pav.id ASC LIMIT 1""" % str(
                        product_was_obj.id))
                    product_were_list = self._cr.dictfetchall()

                    data_quant.append({'product_id': product_was_obj.id,
                                  'code': product_was_obj.default_code,
                                  'name': product_was_obj.product_tmpl_id.name,
                                  'color': product_was_obj.product_tmpl_id.id,
                                  'cost': product_was_obj.product_tmpl_id.standard_price,
                                  'quantity': 0,
                                  'last_qty': last_qty,
                                  'price': product_was_obj.product_tmpl_id.list_price,
                                  'tmpl': product_was_obj.product_tmpl_id.id,
                                  'template': product_was_obj.product_tmpl_id.id,
                                  'barcode': product_was_obj.product_tmpl_id.barcode,
                                  'main_price': product_was_obj.product_tmpl_id.main_price,
                                  'size': product_were_list[0]['name'],
                                  'firstqty': cd['qty']
                                  })
                    break

        for dql_last in data_quant:
            dq_last2.append(dql_last['product_id'])
        checklist = []
        if check_was_but_not_now:
            for cwb in check_was_but_not_now:
                was_but_not_now.append(cwb['product_id'])
                if cwb ['product_id'] not in dq_last2:
                    if cwb ['product_id'] not in checklist:
                        checklist.append(cwb ['product_id'])
            for c in checklist:
                qty = 0.0
                for wbn in check_was_but_not_now:
                    if c == wbn['product_id']:
                        qty += wbn['qty']
                if qty > 0:
                    self._cr.execute("""SELECT sm.product_id as product_id, ppp.default_code as code, coalesce(sum(sm.product_qty),0) AS qty
                                                    FROM stock_move sm
                                                        JOIN product_product ppp
                                                        ON ppp.id=sm.product_id
                                                    WHERE sm.state='done'
                                                         AND sm.location_id not in %s
                                                         AND sm.location_dest_id in %s
                                                         AND sm.product_id = %s
                                                         %s
                                        GROUP BY sm.product_id,ppp.default_code
                                        union
                                        SELECT sm.product_id as product_id, ppp.default_code as code, -coalesce(sum(sm.product_qty),0) AS qty
                                                    FROM stock_move sm
                                                        JOIN product_product ppp ON (ppp.id=sm.product_id)
                                                    WHERE sm.state='done'
                                                         AND sm.location_id in %s
                                                         AND sm.location_dest_id not in %s
                                                         AND sm.product_id = %s
                                                         %s
                                        GROUP BY sm.product_id,ppp.default_code"""
                                     % (location,location, c, last_date_where,
                                        location, location, c, last_date_where))
                    check_last_qty = self._cr.dictfetchall()
                    last_qty = 0.0
                    if check_last_qty:
                        for i in check_last_qty:
                            last_qty += i['qty']
                    product_was_bn_obj = self.env['product.product'].browse(c)
                    if product_was_bn_obj:
                        self._cr.execute("""SELECT name FROM product_attribute_value pav
                                       JOIN product_attribute_value_product_product_rel pavr
                                           ON pavr.product_attribute_value_id = pav.id
                                   WHERE pavr.product_product_id = %s
                                       ORDER BY pav.id ASC LIMIT 1""" % str(
                            product_was_bn_obj.id))
                        product_was_bn_list = self._cr.dictfetchall()

                        data_quant.append({'product_id': product_was_bn_obj.id,
                                           'code': product_was_bn_obj.default_code,
                                           'name': product_was_bn_obj.product_tmpl_id.name,
                                           'color': product_was_bn_obj.product_tmpl_id.id,
                                           'cost': product_was_bn_obj.product_tmpl_id.standard_price,
                                           'quantity': 0,
                                           'last_qty': last_qty,
                                           'price': product_was_bn_obj.product_tmpl_id.list_price,
                                           'tmpl': product_was_bn_obj.product_tmpl_id.id,
                                           'template': product_was_bn_obj.product_tmpl_id.id,
                                           'barcode': product_was_bn_obj.product_tmpl_id.barcode,
                                           'main_price': product_was_bn_obj.product_tmpl_id.main_price,
                                           'size': product_was_bn_list[0]['name'],
                                           'firstqty': qty
                                           })
        # if qty > 0.0:
        #     print 'Temka \n\n',cwb,qty

        # тухайн бараа нь тайлант хугацааны эхний үлдэгдлээр байхгүй байгаад тухайн хугацааны хооронд байсан ба одоогийн байдлаар зарагдсан(хасагдсан) барааг харуулах
        # Тухайн агуулахад орсон хөдөлгөөн дээр тулгуурлаж

        check_dur_move_by_in = []
        self._cr.execute("""SELECT  sm.product_id AS product_id,
                                                                   pt.id AS tmpl,
                                                                   sum(sm.product_uom_qty) AS qty
                                                                     FROM stock_move AS sm
                                                                     LEFT JOIN product_product AS pp
                                                                       ON pp.id = sm.product_id
                                                                     LEFT join product_template AS pt
                                                                       ON pp.product_tmpl_id = pt.id
                                                                     WHERE
                                                                       sm.state = 'done'
                                                                       AND sm.location_dest_id = %s
                                                                        %s
                                                                    GROUP BY sm.product_id,
                                                                               pt.id"""
                         % (self.stock_warehouse.lot_stock_id.id, where_date_sm))
        check_dur_move_list_by_in = self._cr.dictfetchall()
        dq_last3 = []
        if check_dur_move_list_by_in and data_quant:
            for dql_last3 in data_quant:
                dq_last3.append(dql_last3['product_id'])
        # Эхний үлдэгдэл болон эцсийн үлдэгдэл байхгүй барааг тайлант хугацаанд хөдөлгөөн орсон бол энд нэмэв by in
        # Тухайн хугацаанд орж ирчээд гарсан гэсэн үг
        if check_dur_move_list_by_in:
            for cdbyin in check_dur_move_list_by_in:
                # for d in data_quant:
                if cdbyin['product_id'] not in dq_last3:
                    self._cr.execute("""SELECT sm.product_id as product_id, ppp.default_code as code, coalesce(sum(sm.product_qty),0) AS qty
                                                                            FROM stock_move sm
                                                                                JOIN product_product ppp
                                                                                ON ppp.id=sm.product_id
                                                                            WHERE sm.state='done'
                                                                                 AND sm.location_id not in %s
                                                                                 AND sm.location_dest_id in %s
                                                                                 AND sm.product_id = %s
                                                                                 %s
                                                                GROUP BY sm.product_id,ppp.default_code
                                                                union
                                                                SELECT sm.product_id as product_id, ppp.default_code as code, -coalesce(sum(sm.product_qty),0) AS qty
                                                                            FROM stock_move sm
                                                                                JOIN product_product ppp ON (ppp.id=sm.product_id)
                                                                            WHERE sm.state='done'
                                                                                 AND sm.location_id in %s
                                                                                 AND sm.location_dest_id not in %s
                                                                                 AND sm.product_id = %s
                                                                                 %s
                                                                GROUP BY sm.product_id,ppp.default_code"""
                                     % (location, location, cdbyin['product_id'], last_date_where,
                                        location, location, cdbyin['product_id'], last_date_where))
                    check_last_qty_by_in = self._cr.dictfetchall()
                    last_qty = 0.0
                    if check_last_qty_by_in:
                        for i in check_last_qty_by_in:
                            last_qty += i['qty']
                    product_was_obj_by_in = self.env['product.product'].browse(cdbyin['product_id'])
                    self._cr.execute("""SELECT name FROM product_attribute_value pav
                                                                                                                   JOIN product_attribute_value_product_product_rel pavr
                                                                                                                       ON pavr.product_attribute_value_id = pav.id
                                                                                                               WHERE pavr.product_product_id = %s
                                                                                                                   ORDER BY pav.id ASC LIMIT 1""" % str(
                        product_was_obj_by_in.id))
                    product_were_list_by_in = self._cr.dictfetchall()

                    data_quant.append({'product_id': product_was_obj_by_in.id,
                                       'code': product_was_obj_by_in.default_code,
                                       'name': product_was_obj_by_in.product_tmpl_id.name,
                                       'color': product_was_obj_by_in.product_tmpl_id.id,
                                       'cost': product_was_obj_by_in.product_tmpl_id.standard_price,
                                       'quantity': 0,
                                       'last_qty': 0,
                                       'price': product_was_obj_by_in.product_tmpl_id.list_price,
                                       'tmpl': product_was_obj_by_in.product_tmpl_id.id,
                                       'template': product_was_obj_by_in.product_tmpl_id.id,
                                       'barcode': product_was_obj_by_in.product_tmpl_id.barcode,
                                       'main_price': product_was_obj_by_in.product_tmpl_id.main_price,
                                       'size': product_were_list_by_in[0]['name'],
                                       'firstqty': 0
                                       })

        data_quant = sorted(data_quant, key=lambda k: (int(k['code'].split("-")[0]), int(k['code'].split("-")[1]),int(k['size'])))
        if data_quant:
            # for each_data in data_quant:
                # if each_data['product_id'] == 78891:
                #     print 'each_data',each_data
            for each_data in data_quant:
                data = {}
                data_total = {}
                self._cr.execute("""SELECT so.id AS sale_order_id,
                                            sol.id AS sol_id,
                                           so.name AS order_name,
                                           sp.id AS stock_picking_id,
                                           sp.name AS picking_name,
                                           sp.origin AS origin,
                                           so.procurement_group_id AS procurement_group_id,
                                           sp.min_date AS min_date,
                                           so.date AS confirmation_date,
                                           sol.qty_delivered AS qty_delivered,
                                           sol.cash_payment AS cash_payment,
                                           sol.card_payment AS card_payment,
                                           sm.product_uom_qty AS product_uom_qty,
                                           sm.product_id AS product_id
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
                                      %s
                                      GROUP BY so.id,sol.id,sp.id,sm.product_uom_qty,sm.product_id"""
                                 % (each_data['product_id'], self.stock_warehouse.id, where_date_so))
                so_data = self._cr.dictfetchall()

                where_out = ''
                so_pickings = []
                for so in so_data:
                    # if so['product_id'] == 79802:
                    #     print 'SoLine \n', so
                    if so['stock_picking_id'] not in so_pickings:
                        so_pickings.append(so['stock_picking_id'])
                        # print 'SO \n\n',so
                if so_pickings:
                    # print 'so_pickings',so_pickings
                    where_out = 'AND sp.id not in (%s)' % ', '.join(map(repr, tuple(so_pickings)))


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

                self._cr.execute("""SELECT sp.id AS spid,
                                           sp.name AS name,
                                           sp.min_date AS min_date,
                                           sm.product_uom_qty AS out_qty,
                                           sm.product_id AS product_id
                                    FROM stock_picking AS sp
                                        JOIN stock_move AS sm
                                            ON sm.picking_id = sp.id
                                    WHERE sp.state = 'done'
                                          AND sp.location_id = %s
                                          AND sm.product_id = %s
                                      %s %s """
                                 % (self.stock_warehouse.lot_stock_id.id, each_data['product_id'], where_out, where_date_sp))
                # AND sp.location_dest_id not in (SELECT id FROM stock_location WHERE usage = 'customer')
                out_data = self._cr.dictfetchall()

                # prepare data

                data['code'] = each_data['code']
                data['product'] = each_data['name']
                data['template'] = each_data['template']
                data['color'] = each_data['color']
                data['cost'] = each_data['cost']
                data['quantity'] = each_data['quantity']
                data['firstQty'] = each_data['firstqty']
                data['last_qty'] = each_data['last_qty']
                data['dummyLastQty'] = str(each_data['size'])+": "+str(int(each_data['last_qty']))
                data['dummyFirstQty'] = str(each_data['size'])+": "+str(int(each_data['firstqty']))
                    # if data['dummyFirstQty'].split(":")[0] != str(each_data['size']) else ''
                data['price'] = each_data['price']
                data['size'] = each_data['size']
                data['barcode'] = each_data['barcode']
                data['main_price'] = each_data['main_price']
                data['total_size_qty_detail'] = each_data['size'] +': '+ str(int(each_data['last_qty']))
                data['sub_total'] = {}
                total_qty = 0
                total_size = ''
                total_in = 0
                total_out = 0
                total_benefit = 0
                for eachDate in range(0, daily):
                    inInt = 0
                    outInt = 0
                    dataDate = datetime.strftime(dateFrom + timedelta(days=eachDate), '%Y-%m-%d')
                    dataDateTime = dateFrom + timedelta(days=eachDate)
                    inData = ''
                    if in_data:
                        for i in in_data:
                            # in_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S') + timedelta(hours=8)
                            in_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S')
                            in_dt = in_dt.replace(hour=00, minute=00, second=00)
                            if in_dt == dataDateTime:
                                inData += ',\n%s: %s' % (i['name'], i['in_qty']) if inData else '%s: %s' % (i['name'], i['in_qty'])
                                inInt += i['in_qty']
                                # total
                                total_in += i['in_qty']
                    # data['total_size_qty_detail'] = each_data['size'] + ': ' + str(
                    #     int(each_data['quantity'] + total_in))
                    # data['quantity'] = each_data['quantity'] + total_in
                    outData = ''
                    if out_data:
                        for i in out_data:
                            # out_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S') + timedelta(hours=8)
                            out_dt = datetime.strptime(i['min_date'], '%Y-%m-%d %H:%M:%S')
                            out_dt = out_dt.replace(hour=00, minute=00, second=00)
                            if out_dt == dataDateTime:
                                outData += ',\n%s: %s' % (i['name'], i['out_qty']) if outData else '%s: %s' % (i['name'], i['out_qty'])
                                outInt += i['out_qty']
                                # total
                                total_out += i['out_qty']
                                # data['total_size_qty_detail'] = each_data['size'] + ': ' + str(int(each_data['quantity']-total_out))
                                # data['quantity'] = each_data['quantity'] - total_out
                    data[dataDate] = {'qty_delivered': 0,
                                      'picking_name': '',
                                      'cash_payment': 0,
                                      'card_payment': 0,
                                      'benefit': 0,
                                      'product_uom_qty': 0,
                                      'out_data': outData,
                                      'in_data': inData,
                                      'inInt': inInt,
                                      'outInt': outInt}
                    if so_data:
                        for soLine in so_data:
                            # if soLine['product_id'] == 79802:
                            #     print 'SoLine \n',soLine
                            # dt = datetime.strptime(soLine['confirmation_date'], '%Y-%m-%d %H:%M:%S') + timedelta(hours=8)
                            dt = datetime.strptime(soLine['confirmation_date'], '%Y-%m-%d %H:%M:%S')
                            dt = dt.replace(hour=00, minute=00, second=00)
                            if soLine['order_name'] == soLine['origin'] and dt == dataDateTime and soLine['product_id'] == each_data['product_id']:
                                each_data_cost = each_data['cost'] if each_data['cost'] else 0
                                each_data_cost = each_data_cost * soLine['qty_delivered']
                                data[dataDate]['qty_delivered'] += soLine['qty_delivered']
                                data[dataDate]['picking_name'] = soLine['picking_name']
                                data[dataDate]['cash_payment'] += soLine['cash_payment']
                                data[dataDate]['card_payment'] += soLine['card_payment']
                                data[dataDate]['benefit'] += (soLine['cash_payment'] + soLine['card_payment']) - each_data_cost
                                data[dataDate]['product_uom_qty'] += soLine['product_uom_qty']
                                data[dataDate]['inInt'] = inInt
                                data[dataDate]['outInt'] = outInt
                                # total
                                total_size = each_data['size']
                                total_qty += soLine['qty_delivered']
                                total_benefit += (soLine['cash_payment'] + soLine['card_payment']) - each_data_cost

                    # if data['total_size_qty_detail'] > 0 and data['quantity'] > 0:
                    data['total_size_qty_detail'] = each_data['size'] + ': ' + str(
                        int(each_data['firstqty']))
                    data['total_size_last_qty'] = each_data['size'] + ': ' + str(
                        int(each_data['last_qty']))
                    data['quantity'] = each_data['quantity']

                data['sub_total']['total_in'] = total_in
                data['sub_total']['total_out'] = total_out
                data['sub_total']['total_qty'] = total_qty
                data['sub_total']['total_size'] = total_size
                data['sub_total']['total_benefit'] = total_benefit
                # print 'data \n',data
                dataLine.append(data)
        # create workbook
        book = xlwt.Workbook(encoding='utf8')
        # create sheet
        report_name = _('Product sale report')
        sheet = book.add_sheet(report_name)

        # create report object
        report_excel_output = self.env['report.excel.output.extend'].with_context(filename_prefix='ProductSaleReport', form_title=report_name).create({})

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
                        dataEachPrdDict['firstQty'] += d['firstQty']
                        dataEachPrdDict['last_qty'] += d['last_qty']
                        dataEachPrdDict['barcode'] = d['barcode']
                        dataEachPrdDict['price'] = d['price'] if d['price'] else 0
                        dataEachPrdDict['main_price'] = d['main_price'] if d['main_price'] else 0
                        dataEachPrdDict['dummyFirstQty'] += ", "+d['dummyFirstQty'] if dataEachPrdDict['dummyFirstQty'] else d['dummyFirstQty']
                        dataEachPrdDict['dummyLastQty'] += ", "+d['dummyLastQty'] if dataEachPrdDict['dummyLastQty'] else d['dummyLastQty']
                        dataEachPrdDict['total_size_qty_detail'] += ", "+d['total_size_qty_detail'] if dataEachPrdDict['total_size_qty_detail'] else d['total_size_qty_detail']
                        dataEachPrdDict['total_size_last_qty'] += ", "+d['total_size_last_qty'] if dataEachPrdDict['total_size_last_qty'] else d['total_size_last_qty']
                        dataEachPrdDict['size'] += ", "+d['size'] if dataEachPrdDict['size'] else d['size']
                        for everyDl in header_daily:
                            dataEachPrdDict[everyDl]['qty_delivered'] += d[everyDl]['qty_delivered']
                            dataEachPrdDict[everyDl]['cash_payment'] += d[everyDl]['cash_payment']
                            dataEachPrdDict[everyDl]['card_payment'] += d[everyDl]['card_payment']
                            dataEachPrdDict[everyDl]['benefit'] += d[everyDl]['benefit']
                            dataEachPrdDict[everyDl]['out_data'] += ",\n"+d[everyDl]['out_data'] if dataEachPrdDict[everyDl]['out_data'] else d[everyDl]['out_data']
                            dataEachPrdDict[everyDl]['in_data'] += ",\n"+d[everyDl]['in_data'] if dataEachPrdDict[everyDl]['in_data'] else d[everyDl]['in_data']
                            dataEachPrdDict[everyDl]['inInt'] += d[everyDl]['inInt']
                            dataEachPrdDict[everyDl]['outInt'] += d[everyDl]['outInt']
                        dataEachPrdDict['sub_total']['total_qty'] += d['sub_total']['total_qty']
                        dataEachPrdDict['sub_total']['total_in'] += d['sub_total']['total_in']
                        dataEachPrdDict['sub_total']['total_out'] += d['sub_total']['total_out']
                        dataEachPrdDict['sub_total']['total_size'] += "- " + d['sub_total']['total_size'] if dataEachPrdDict['sub_total']['total_size'] else d['sub_total']['total_size']
                        dataEachPrdDict['sub_total']['total_benefit'] += d['sub_total']['total_benefit']
                    else:
                        dataEachPrdList.append(dataEachPrdDict)
                        dataEachPrdDict = d
                        template = d['template']
                else:
                    dataEachPrdDict = d
                    template = d['template']
                if lenb == lena:
                    dataEachPrdList.append(dataEachPrdDict)
            dataLine = dataEachPrdList
            # print 'dataLine\n',dataLine
            # Daily total
            dailySubTotal = {'ttlQuant': 0, 'ttlFirstQuant': 0, 'ttlMainPrice': 0, 'ttlLastQuant':0}
            dailyTotal = {}
            for d in header_daily:
                # total prepare empty
                dailySubTotal[d] = {'qty': 0,
                                    'cash': 0,
                                    'card': 0,
                                    'benefit': 0,
                                    'in': 0,
                                    'out': 0}
            ttl_out = 0
            ttl_in = 0
            ttl_qty = 0
            ttl_benefit = 0
            total = 0
            for l in dataLine:
                outInt = 0
                inInt = 0
                dailySubTotal['ttlQuant'] += l['quantity']
                dailySubTotal['ttlFirstQuant'] += l['firstQty']
                dailySubTotal['ttlLastQuant'] += l['last_qty']
                dailySubTotal['ttlMainPrice'] += l['main_price'] if l['main_price'] else 0
                for d in header_daily:
                    dailySubTotal[d]['qty'] += l[d]['qty_delivered']
                    dailySubTotal[d]['cash'] += l[d]['cash_payment']
                    dailySubTotal[d]['card'] += l[d]['card_payment']
                    dailySubTotal[d]['benefit'] += l[d]['benefit']
                    dailySubTotal[d]['in'] += l[d]['inInt']
                    dailySubTotal[d]['out'] += l[d]['outInt']
                    total += l[d]['cash_payment'] + l[d]['card_payment']
                ttl_out += l['sub_total']['total_out']
                ttl_in += l['sub_total']['total_in']
                ttl_qty += l['sub_total']['total_qty']
                ttl_benefit += l['sub_total']['total_benefit']
            dailySubTotal['total_out'] = ttl_out
            dailySubTotal['total_in'] = ttl_in
            dailySubTotal['total_qty'] = ttl_qty
            dailySubTotal['total'] = total
            dailySubTotal['total_benefit'] = ttl_benefit

        # define title and header
        if self.show_cost:
            title_list = [('Шинэ код'), ('Бараа нэр'), ('Баркод'), ('Үндсэн үнэ ₮'), ('Размерууд'), ('Өртөг үнэ ₮'), ('Тоо, ш'), ('Зарах үнэ')]
        else:
            title_list = [('Шинэ код'), ('Бараа нэр'), ('Размерууд'), ('Үндсэн үнэ ₮'), ('Тоо, ш'), ('Зарах үнэ')]
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
                if self.show_cost:
                    cola += 7
                else:
                    cola += 6
                sheet.write_merge(rowx, rowx, coly, cola, header_daily[x], style_title)
                sheet.write_merge(rowx+1, rowx+1, coly, coly, 'Зарсан ш', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+1, coly+1, 'Зарсан үнэ, бэлнээр ₮', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+2, coly+2, 'Зарсан үнэ, картаар ₮', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+3, coly+3, 'Буцсан, ш', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+4, coly+4, 'Буцсан, тэмдэглэл', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+5, coly+5, 'Агуулахаас, ш', style_title)
                sheet.write_merge(rowx+1, rowx+1, coly+6, coly+6, 'Агуулахаас, тэмдэглэл', style_title)
                if self.show_cost:
                    sheet.write_merge(rowx+1, rowx+1, coly+7, coly+7, 'Ашиг', style_title)
                cola += 1
                coly = cola
            if self.show_cost:
                sheet.write_merge(rowx, rowx, coly, cola+7, 'Нийт', style_title)
            else:
                sheet.write_merge(rowx, rowx, coly, cola+6, 'Нийт', style_title)
            sheet.write(rowx + 1, coly, 'Зарсан, ш', style_title)
            sheet.write(rowx + 1, coly + 1, 'Буцаалт, ш', style_title)
            sheet.write(rowx + 1, coly + 2, 'Агуулахаас , Ш', style_title)
            sheet.write(rowx + 1, coly + 3, 'ТАйлан хугацааны үлдэгдэл ш', style_title)
            sheet.write(rowx + 1, coly + 4, 'размерууд, ш', style_title)
            sheet.write(rowx + 1, coly + 5, 'Борлуулсан размерууд', style_title)
            sheet.write(rowx + 1, coly + 6, 'Бодит үлдэгдэл размерууд', style_title)
            if self.show_cost:
                sheet.write(rowx + 1, coly + 7, 'Нийт ашиг', style_title)
        sheet.write_merge(rowx, rowx, colx, colx + len(title_list) - 1, 'Үндсэн мэдээлэл', style_title)
        rowx += 1
        for i in xrange(0, len(title_list)):
            sheet.write_merge(rowx, rowx, i, i, title_list[i], style_title)
        rowx += 1
        num = 0
        if dataLine:
            for line in dataLine:
                if self.show_cost:
                    sheet.write(rowx, colx, line['code'])
                    sheet.write(rowx, colx + 1, line['product'])
                    sheet.write(rowx, colx + 2, line['barcode'])
                    sheet.write(rowx, colx + 3, line['main_price'])
                    sheet.write(rowx, colx + 4, line['dummyFirstQty'])
                    sheet.write(rowx, colx + 5, line['cost'])
                    sheet.write(rowx, colx + 6, line['firstQty'])
                    sheet.write(rowx, colx + 7, line['price'])
                else:
                    sheet.write(rowx, colx, line['code'])
                    sheet.write(rowx, colx + 1, line['product'])
                    sheet.write(rowx, colx + 2, line['dummyFirstQty'])
                    sheet.write(rowx, colx + 3, line['main_price'])
                    sheet.write(rowx, colx + 4, line['firstQty'])
                    sheet.write(rowx, colx + 5, line['price'])
                if header_daily:
                    colc = len(title_list)
                    cold = len(title_list)
                    for hd in header_daily:
                        if self.show_cost:
                            cold += 7
                        else:
                            cold += 6
                        sheet.write(rowx, colx + colc, line[hd]['qty_delivered'])
                        sheet.write(rowx, colx + colc+1, line[hd]['cash_payment'])
                        sheet.write(rowx, colx + colc+2, line[hd]['card_payment'])
                        sheet.write(rowx, colx + colc+3, line[hd]['outInt'])
                        sheet.write(rowx, colx + colc+4, line[hd]['out_data'])
                        sheet.write(rowx, colx + colc+5, line[hd]['inInt'])
                        sheet.write(rowx, colx + colc+6, line[hd]['in_data'])
                        if self.show_cost:
                            sheet.write(rowx, colx + colc+7, line[hd]['benefit'])
                        cold += 1
                        colc = cold
                    if line['sub_total']:
                        sheet.write(rowx, colx + colc, line['sub_total']['total_qty'])
                        sheet.write(rowx, colx + colc+1, line['sub_total']['total_out'])
                        sheet.write(rowx, colx + colc+2, line['sub_total']['total_in'])
                        sheet.write(rowx, colx + colc+3, line['last_qty'])
                        sheet.write(rowx, colx + colc+4, line['dummyLastQty'])
                        sheet.write(rowx, colx + colc+5, line['sub_total']['total_size'])
                        sheet.write(rowx, colx + colc+6, line['quantity'])
                        if self.show_cost:
                            sheet.write(rowx, colx + colc+7, line['sub_total']['total_benefit'])
                rowx += 1

            if dailySubTotal:
                rowx += 1
                sheet.write(rowx, colx, _("Product Quintity: "), style_footer)
                sheet.write(rowx, colx + 4, dailySubTotal['ttlFirstQuant'], style_footer)
                sheet.write(rowx+2, colx, _("Daily Sale: "), style_footer)
                sheet.write(rowx+3, colx, _("Daily Sale Quantity: "), style_footer)
                sheet.write(rowx+4, colx, _("Daily warehouse out: "), style_footer)
                sheet.write(rowx+5, colx, _("Daily warehouse in: "), style_footer)
                if self.show_cost:
                    sheet.write(rowx+6, colx, _("Өдрийн ашиг: "), style_footer)

                coli = len(title_list)
                colj = len(title_list)
                for hd in header_daily:
                    if self.show_cost:
                        colj += 7
                    else:
                        colj += 6
                    sheet.write(rowx+3, colx+coli, dailySubTotal[hd]['qty'], style_footer)
                    sheet.write(rowx+2, colx+coli+1, dailySubTotal[hd]['cash'], style_footer)
                    sheet.write(rowx+2, colx+coli+2, dailySubTotal[hd]['card'], style_footer)
                    sheet.write(rowx+4, colx+coli+3, dailySubTotal[hd]['out'], style_footer)
                    sheet.write(rowx+4, colx+coli+4, '', style_footer)
                    sheet.write(rowx+5, colx+coli+5, dailySubTotal[hd]['in'], style_footer)
                    sheet.write(rowx+5, colx+coli+6, '', style_footer)
                    if self.show_cost:
                        sheet.write(rowx+6, colx+coli+7, dailySubTotal[hd]['benefit'], style_footer)
                    colj += 1
                    coli = colj
                sheet.write(rowx, colx+coli, dailySubTotal['total_qty'], style_footer)
                sheet.write(rowx, colx+coli+1, dailySubTotal['total_out'], style_footer)
                sheet.write(rowx, colx+coli+2, dailySubTotal['total_in'], style_footer)
                sheet.write(rowx, colx+coli+3, dailySubTotal['ttlLastQuant'], style_footer)
                sheet.write(rowx, colx+coli+6, dailySubTotal['ttlQuant'], style_footer)
                sheet.write(rowx+2, colx+coli+1, _('Total: '), style_footer)
                sheet.write(rowx+2, colx+coli+2, dailySubTotal['total'], style_footer)
                if self.show_cost:
                    sheet.write(rowx+6, colx+coli+7, dailySubTotal['total_benefit'], style_footer)

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