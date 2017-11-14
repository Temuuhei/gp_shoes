# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv,fields
from openerp.tools.translate import _
from datetime import datetime, timedelta
from operator import itemgetter
from lxml import etree
import time
import logging
import xlwt
from StringIO import StringIO
import base64
_logger = logging.getLogger('stock.report')

class report_product_move_check(osv.osv_memory):
    _name = 'report.product.move.check'
    _description = 'Product Move Report'
    
    def get_report_type(self, cr, uid, context=None):
        res = [('owner',_('Quantity')),
               ('price',_('List Price')),]
        if self.pool.get('res.users').has_group(cr, uid, 'l10n_mn_account.account_view_cost'):
            res += [('cost',_('Cost Price'))]
        return res
    
    _columns = {
        'report_type':      fields.selection(get_report_type, 'Report Type', required=True),
        'level':            fields.selection([('owner','Owner'),('manager','Manager')], 'Level', required=True),
        'warehouse_id':     fields.many2one('stock.warehouse','Warehouse', required=True),
        'from_date':        fields.date('From Date', required=True),
        'to_date':          fields.date('To Date', required=True),
        'draft':            fields.boolean('Draft View'),
        'template_id':      fields.many2one('product.template', 'Product Template'),
        'category_id':      fields.many2one('product.category', 'Category'),
        'pos_categ_id':     fields.many2one('pos.category', 'Pos Category'),
        'product_id':       fields.many2one('product.product', 'Product', required=True),
        'prodlot_id':       fields.many2one('stock.production.lot', 'Production Lot'),
        'save':             fields.boolean('Save to document storage')
    }
    
    def _get_product(self, cr, uid, context=None):
        context = context or {}
        if 'active_id' in context and context['active_id']:
            return context['active_id']
        return False
    
    def _get_warehouse_id(self, cr, uid, context=None):
        context = context or {}
        res = 0
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user and user.allowed_warehouses:
            res = user.allowed_warehouses[0].id
        return res
    
    def _get_report_type(self, cr, uid, context=None):
        if self.pool.get('res.users').has_group(cr, uid, 'account.group_account_user'):
            res = 'price'
        else :
            res = 'owner'
        return res
    def _get_level(self, cr, uid, context=None):
        if self.pool.get('res.users').has_group(cr, uid, 'account.group_account_user'):
            level = 'manager'
        else :
            level = 'owner'
        return level
    
    _defaults = {
        'report_type':  _get_report_type,
        'from_date': lambda *a: time.strftime('%Y-%m-01'),
        'warehouse_id': _get_warehouse_id,
        'product_id': _get_product,
        'level': _get_level,
        'to_date': lambda *a: time.strftime('%Y-%m-%d'),
    }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(report_product_move_check, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        user_obj = self.pool.get('res.users')
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            for node in doc.xpath("//field[@name='warehouse_id']"):
                node.set('domain', [('id','in',map(lambda x:x.id,user.allowed_warehouses) or [-1])].__repr__())
            res['arch'] = etree.tostring(doc)
        return res
    
    def template_id_change(self, cr, uid, ids, template_id):
        res = {}
        if template_id:
            cr.execute("""SELECT p.id FROM product_product p 
                               JOIN product_template t on p.product_tmpl_id = t.id
                               WHERE t.id = %s"""%(template_id))
            prod_ids = [p[0] for p in cr.fetchall()]
            return ({'domain':{'product_id': [('id','in',prod_ids)]}})
        else:
            return res
        
    
    def poscateg_id_change(self, cr, uid, ids, poscateg_id):
        res = {}
        if poscateg_id:
            cr.execute("""SELECT t.id FROM product_product p 
                            JOIN product_template as t on p.product_tmpl_id = t.id
                           WHERE t.pos_categ_id = %s"""%(poscateg_id))
            templ_ids = [p[0] for p in cr.fetchall()]
            return ({'domain':{'product_id': [('product_tmpl_id','in',templ_ids)],
                               'template_id': [('id','in',templ_ids)]}})
        else:
            return res
    
    def categ_id_change(self, cr, uid, ids, categ_id):
        res = {}
        if categ_id:
            cr.execute("""SELECT p.id FROM product_template p 
                           WHERE categ_id = %s"""%(categ_id))
            templ_ids = [p[0] for p in cr.fetchall()]
            return ({'domain':{'product_id': [('product_tmpl_id','in',templ_ids)],
                               'template_id': [('id','in',templ_ids)]}})
        else:
            return res
        
    def prodlot_id_change(self, cr, uid, ids, prod_id):
        res = {}
        if prod_id:
            cr.execute("""SELECT p.id FROM stock_production_lot p 
                            WHERE product_id = %s"""%(prod_id))
            prodlot_ids = [p[0] for p in cr.fetchall()]
            return ({'domain':{'prodlot_id': [('id','in',prodlot_ids)]}})
        else:
            return res
    
    def get_log_message(self, cr, uid, ids, context=None):
        form = self.browse(cr, uid, ids)[0]
        message = u"Бүртгэл хяналтын баримт (Агуулах ='%s', Бараа = '%s', Эхлэх хугацаа = '%s', Дуусах хугацаа = '%s')" %(form.warehouse_id.name, form.product_id.name, form.from_date, form.to_date),
        return message
    
    def get_available(self, cr, uid, wiz, context=None):
        ''' 
            Эхний үлдэгдэл тооцож байна.
        '''
        qty = 0
        from_date = ''
        where = ''
        location_ids = []
        #if filters.get('from_date',False):
        from_date = wiz['from_date']+' 23:59:59'
        #if filters.get('prod_id', False):
        prod = wiz['prod_id']
        if wiz['lot_id']:
            where = ' AND prodlot_id = '+str(wiz['lot_id'])
        fdate = datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')
        oneday = timedelta(days=1)
        fdate = fdate - oneday
        cr.execute('select lot_stock_id from stock_warehouse where id=%s', (wiz['warehouse_id'],))
        res2 = cr.fetchone()
        if res2:
            location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', [res2[0]])])
        cr.execute("SELECT sum(product_qty)::decimal(16,2) AS product_qty from report_stock_inventory "
                    "where date <= %s and location_type = 'internal' "
                    "and location_id in %s and product_id = %s "+ where +" "
                    ,(fdate, tuple(location_ids), prod) )#from_date
        stock = cr.fetchone()
        if stock and stock[0]:
            qty = stock[0]
        return qty
    
    def get_price(self, cr, uid, wiz, ptype, context=None):
        context = context or {}
        from_date = wiz['from_date']+' 23:59:59'
        fdate = datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')
        oneday = timedelta(days=1)
        fdate = fdate - oneday
        price = 0.0
        if ptype == 'first':
            cr.execute("select h.list_price from product_price_history h "
                       "join product_template t on (h.product_template_id = t.id) "
                       "join product_product p on (t.id = p.product_tmpl_id) "
                       "where p.id = %s and h.datetime <= %s "
                       "and h.price_type = %s and h.company_id = %s "
                       "order by h.datetime desc limit 1",
                (wiz['prod_id'],fdate, wiz['price_type'], wiz['company_id']))
            fetched = cr.fetchone()
            if fetched and fetched[0]:
                price = fetched[0]
        else:
            price = self.pool.get('product.product').price_get(cr, uid, [wiz['prod_id']], 'list_price', context=context)[wiz['prod_id']]
            cr.execute("select h.list_price from product_price_history h "
                       "join product_template t on (h.product_template_id = t.id) "
                       "join product_product p on (t.id = p.product_tmpl_id) "
                       "where p.id = %s and h.datetime <= %s "
                       "and h.price_type = %s and h.company_id = %s "
                       "order by h.datetime desc limit 1",
                (wiz['prod_id'],wiz['to_date']+' 23:59:59', wiz['price_type'], wiz['company_id']))
            fetched = cr.fetchone()
            if fetched and fetched[0]:
                price = fetched[0]
        return price
    
    def get_first_cost(self, cr, uid, wiz):
        ''' Тухайн барааны эхний хугацаандах өртөгүүдийг олно.'''
        res = 0.0
        where = ''
        prod_id = wiz['prod_id']
        from_date = wiz['from_date']+' 23:59:59'
        wid = wiz['warehouse_id']
        company = wiz['company_id']
        cr.execute('select view_location_id from stock_warehouse where id=%s', (wid,))
        res2 = cr.fetchone()
        location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', [res2[0]]),('usage','=','internal')])
        location_tuple = tuple(location_ids)
        fdate = datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')
        oneday = timedelta(days=1)
        fdate = fdate - oneday
        fdate = fdate.strftime('%Y-%m-%d %H:%M:%S')
        cr.execute("""SELECT (m.price_unit * uom.factor / uom2.factor) AS cost,m.date AS date,
                        (m.product_qty / uom.factor * uom2.factor) AS in_qty,
                        (select 0) AS out_qty
                        FROM stock_move AS m 
                          LEFT JOIN stock_picking AS p ON m.picking_id = p.id 
                          LEFT JOIN res_partner AS rp ON p.partner_id = rp.id 
                          LEFT JOIN product_template AS pt ON m.product_id = pt.id 
                          LEFT JOIN product_uom AS uom ON m.product_uom = uom.id
                          LEFT JOIN product_uom AS uom2 ON pt.uom_id = uom2.id
                        WHERE m.location_id NOT IN %s
                          AND m.location_dest_id IN %s
                          AND m.product_id = %s
                          AND m.state = 'done'
                          AND m.product_qty is not null
                          AND m.date <= %s """+where+"""
                    UNION ALL
                    SELECT (m.price_unit * uom.factor / uom2.factor) AS cost,m.date AS date,
                        (select 0) AS in_qty,
                        (m.product_qty / uom.factor * uom2.factor) AS out_qty
                        FROM stock_move AS m 
                            LEFT JOIN stock_picking AS p ON m.picking_id = p.id 
                            LEFT JOIN res_partner AS rp ON p.partner_id = rp.id 
                            LEFT JOIN product_template AS pt ON m.product_id = pt.id 
                            LEFT JOIN product_uom AS uom ON m.product_uom = uom.id
                            LEFT JOIN product_uom AS uom2 ON pt.uom_id = uom2.id
                        WHERE m.location_id IN %s
                          AND m.location_dest_id NOT IN %s
                          AND m.product_id = %s
                          AND m.state = 'done'
                          AND m.product_qty is not null
                          AND m.date <= %s """+where+"""
                    ORDER BY date
                    """
                        ,(location_tuple,location_tuple,prod_id,fdate,
                          location_tuple,location_tuple,prod_id,fdate,))
        stock = cr.dictfetchall()
        if stock:
            tmp_cost = 0.0
            qty = 0
            for st in stock:
                if st['in_qty'] > 0:
                    qty += st['in_qty']
                if st['out_qty'] > 0:
                    qty -= st['out_qty']
                tmp_cost = st['cost']
            res = tmp_cost
        return res
    
    def get_move_data(self, cr, uid, wiz, context=None):
        context = context or {}
        res = []
        where = ''
        return_ids = []
        prod_id = wiz['prod_id']
        from_date = wiz['from_date']
        to_date = wiz['to_date'] + ' 23:59:59'
        wid = wiz['warehouse_id']
        company = wiz['company_id']
        select_in = ''
        select_out = ''
        select_coll = ''
        join = ''
        dugaar_query = ''
        group_by = ''
        mrp_obj = self.pool.get('mrp.production')
        collection_obj = self.pool.get('collection.collection')
        if collection_obj:
            select_coll = " WHEN m.collection_prod_line_id is not null THEN 'collection' "
        if mrp_obj:
            select_in = " WHEN m.production_id is not null THEN 'refund_mrp' "
            select_out = " WHEN m.production_id is not null THEN 'mrp' "
            dugaar_query = " WHEN m.production_id is not null THEN mrp.name "
            join = ' LEFT JOIN mrp_production AS mrp ON (m.production_id = mrp.id) '
            group_by = 'm.production_id,mrp.name,'
        if wiz['draft']:
            where += " AND m.state <> 'cancel' "
        else:
            where += " AND m.state = 'done' "
        if wiz['lot_id']:
            where += " AND (spo.lot_id = %s OR m.restrict_lot_id = %s)"  %(str(wiz['lot_id']),str(wiz['lot_id']))
        cr.execute('select view_location_id from stock_warehouse where id=%s', (wiz['warehouse_id'],))
        res2 = cr.fetchone()
        location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', [res2[0]]),('usage','=','internal')])
        location_tuple = tuple(location_ids)
        cr.execute("""SELECT m.date AS date, ('out') AS type, m.origin_returned_move_id AS return_id,
                        (CASE WHEN m.restrict_lot_id is not null THEN lot2.name WHEN link.move_id is not null THEN lot.name ELSE '' END) AS lot, 
                        (CASE WHEN m.picking_id is not null THEN rp.name WHEN m.warehouse_id is not null
                            and sw.partner_id is not null THEN rp2.name ELSE '' END) AS partner,
                        (CASE WHEN m.procurement_id is not null and so.sale_category_id is not null THEN sc.name||' борлуулалт'
                            WHEN m.picking_id is not null and m.purchase_line_id is not null THEN 'refund_purchase'
                            WHEN m.inventory_id is not null THEN 'inventory' """+select_out+""" """+select_coll+"""
                            WHEN sl.usage = 'transit' THEN 'procure'
                            WHEN sl.usage = 'consume' THEN 'consume'
                            WHEN m.procurement_id is not null and po.swap_line_id is not null THEN 'swap' WHEN m.origin_returned_move_id is not null THEN 'refund'
                            WHEN m.picking_id is not null and p.picking_type_id is not null and spt.code = 'internal' THEN 'internal'
                            ELSE 'pos' END) AS rep_type, m.state AS state, m.id AS move_id,
                        (CASE WHEN m.picking_id is not null THEN p.name 
                            """+dugaar_query+""" 
                            WHEN m.inventory_id is not null THEN i.name ELSE 'pos' END) AS dugaar,
                        (m.price_unit) AS cost, 
                        (m.list_price) AS price, sl.name AS location,
                        SUM(coalesce(CASE WHEN link.move_id is not null THEN (link.qty / u.factor * u2.factor)
                                    ELSE (m.product_qty / u.factor * u2.factor) END, 0)) AS qty
                    FROM stock_move AS m
                        LEFT JOIN stock_picking AS p ON (m.picking_id = p.id)
                        LEFT JOIN stock_picking_type AS spt ON (p.picking_type_id = spt.id)
                        """+join+"""
                        LEFT JOIN res_partner AS rp ON (p.partner_id = rp.id)
                        LEFT JOIN purchase_order_line AS pol ON (m.purchase_line_id = pol.id)
                        LEFT JOIN swap_order_line AS swl ON (m.swap_line_id = swl.id)
                        LEFT JOIN stock_inventory AS i ON (m.inventory_id = i.id)
                        LEFT JOIN procurement_order AS po ON (m.procurement_id = po.id)
                        LEFT JOIN sale_order_line AS sol ON (po.sale_line_id = sol.id)
                        LEFT JOIN sale_order AS so ON (sol.order_id = so.id)
                        LEFT JOIN sale_category AS sc ON (so.sale_category_id = sc.id)
                        JOIN product_product AS pp ON (m.product_id = pp.id)
                        JOIN product_template AS pt ON (pp.product_tmpl_id = pt.id)
                        JOIN product_uom AS u ON (m.product_uom = u.id)
                        JOIN product_uom AS u2 ON (pt.uom_id = u2.id)
                        JOIN stock_location AS sl ON (m.location_dest_id = sl.id)
                        LEFT JOIN stock_warehouse AS sw ON (m.warehouse_id = sw.id)
                        LEFT JOIN res_partner AS rp2 ON (sw.partner_id = rp2.id)
                        LEFT JOIN stock_move_operation_link AS link ON (m.id = link.move_id)
                        LEFT JOIN stock_pack_operation AS spo ON (link.operation_id = spo.id)
                        LEFT JOIN stock_production_lot lot ON (spo.lot_id = lot.id)
                        LEFT JOIN stock_production_lot lot2 ON (m.restrict_lot_id = lot2.id)
                    WHERE m.location_id IN %s AND m.location_dest_id NOT IN %s
                        AND m.product_id = %s AND m.product_qty is not null
                        AND m.date >= %s AND m.date <= %s """+where+"""
                    GROUP BY m.date,lot.name,m.picking_id,rp.name,m.warehouse_id,sw.partner_id,rp2.name,sl.usage,
                        m.procurement_id,so.sale_category_id,sc.name,m.purchase_line_id,m.inventory_id,p.picking_type_id,
                        po.transit_order_id,po.consume_order_id,m.origin_returned_move_id,spt.code,"""+group_by+"""
                        po.swap_line_id,i.name,m.list_price,link.move_id,sl.name,m.state,p.name,m.id,lot2.name,m.restrict_lot_id
                UNION ALL
                    SELECT m.date AS date, ('in') AS type, m.origin_returned_move_id AS return_id,
                        (CASE WHEN m.restrict_lot_id is not null THEN lot2.name WHEN link.move_id is not null THEN lot.name ELSE '' END) AS lot, 
                        (CASE WHEN m.picking_id is not null THEN rp.name WHEN m.warehouse_id is not null
                            and sw.partner_id is not null THEN rp2.name ELSE '' END) AS partner,
                        (CASE WHEN m.procurement_id is not null and so.sale_category_id is not null THEN sc.name||' буцаалт'
                            WHEN m.picking_id is not null and m.purchase_line_id is not null THEN 'purchase'
                            WHEN m.inventory_id is not null THEN 'inventory' """+select_in+"""  """+select_coll+"""
                            WHEN sl.usage = 'transit' THEN 'procure'
                            WHEN sl.usage = 'consume' THEN 'consume'
                            WHEN m.swap_line_id is not null THEN 'swap' WHEN m.origin_returned_move_id is not null THEN 'refund'
                            WHEN m.picking_id is not null and p.picking_type_id is not null and spt.code = 'internal' THEN 'internal'
                            ELSE 'pos' END) AS rep_type, m.state AS state, m.id AS move_id,
                        (CASE WHEN m.picking_id is not null THEN p.name 
                            """+dugaar_query+""" 
                            WHEN m.inventory_id is not null THEN i.name ELSE 'pos' END) AS dugaar,
                        (m.price_unit) AS cost, 
                        m.list_price AS price, sl.name AS location,
                        SUM(coalesce(CASE WHEN link.move_id is not null THEN (link.qty / u.factor * u2.factor) 
                                        ELSE (m.product_qty / u.factor * u2.factor) END, 0)) AS qty
                    FROM stock_move AS m
                        LEFT JOIN stock_picking AS p ON (m.picking_id = p.id)
                        LEFT JOIN stock_picking_type AS spt ON (p.picking_type_id = spt.id)
                        """+join+"""
                        LEFT JOIN res_partner AS rp ON (p.partner_id = rp.id)
                        LEFT JOIN purchase_order_line AS pol ON (m.purchase_line_id = pol.id)
                        LEFT JOIN swap_order_line AS swl ON (m.swap_line_id = swl.id)
                        LEFT JOIN stock_inventory AS i ON (m.inventory_id = i.id)
                        LEFT JOIN procurement_order AS po ON (m.procurement_id = po.id)
                        LEFT JOIN sale_order_line AS sol ON (po.sale_line_id = sol.id)
                        LEFT JOIN sale_order AS so ON (sol.order_id = so.id)
                        LEFT JOIN sale_category AS sc ON (so.sale_category_id = sc.id)
                        JOIN product_product AS pp ON (m.product_id = pp.id)
                        JOIN product_template AS pt ON (pp.product_tmpl_id = pt.id)
                        JOIN product_uom AS u ON (m.product_uom = u.id)
                        JOIN product_uom AS u2 ON (pt.uom_id = u2.id)
                        JOIN stock_location AS sl ON (m.location_id = sl.id)
                        LEFT JOIN stock_warehouse AS sw ON (m.warehouse_id = sw.id)
                        LEFT JOIN res_partner AS rp2 ON (sw.partner_id = rp2.id)
                        LEFT JOIN stock_move_operation_link AS link ON (m.id = link.move_id)
                        LEFT JOIN stock_pack_operation AS spo ON (link.operation_id = spo.id)
                        LEFT JOIN stock_production_lot lot ON (spo.lot_id = lot.id)
                        LEFT JOIN stock_production_lot lot2 ON (m.restrict_lot_id = lot2.id)
                    WHERE m.location_id NOT IN %s AND m.location_dest_id IN %s
                        AND m.product_id = %s AND m.product_qty is not null
                        AND m.date >= %s AND m.date <= %s """+where+"""
                    GROUP BY m.date,lot.name,m.picking_id,rp.name,m.warehouse_id,sw.partner_id,rp2.name,sl.usage,
                        m.procurement_id,so.sale_category_id,sc.name,m.purchase_line_id,m.inventory_id,p.picking_type_id,
                        po.transit_order_id,po.consume_order_id,m.origin_returned_move_id,spt.code,"""+group_by+"""
                        m.swap_line_id,i.name,m.list_price,link.move_id,sl.name,m.state,p.name,m.id,lot2.name,m.restrict_lot_id
                UNION 
                    SELECT h.datetime AS date, ('price') AS type, h.id AS return,
                        ('price') AS lot, 
                        (CASE WHEN rc.partner_id is not null THEN rp.name ELSE rc.name END) AS partner, ('price') AS rep_type, ('price') AS state, h.id AS move_id,
                        ('price') AS dugaar, (select 0) AS cost, h.list_price AS price,
                        ('price') AS location,
                        (select 0) AS qty
                    FROM product_price_history AS h
                        JOIN product_template AS t ON (h.product_template_id = t.id)
                        JOIN product_product AS p ON (t.id = p.product_tmpl_id)
                        JOIN res_company AS rc ON (h.company_id = rc.id)
                        LEFT JOIN res_partner AS rp ON (rc.partner_id = rp.id)
                    WHERE h.datetime >= %s AND h.datetime <= %s AND h.company_id = %s
                        AND p.id = %s AND h.price_type = %s
                ORDER BY date
                        """,(location_tuple,location_tuple,prod_id,from_date,to_date,
                             location_tuple,location_tuple,prod_id,from_date,to_date,
                             from_date,to_date,company,prod_id,wiz['price_type']))
        result = cr.dictfetchall()
        for r in result:
            lot = r['lot'] or ''
            in_qty = out_qty = 0.0
            if r['type'] == 'in':
                in_qty = r['qty']
            else:
                out_qty = r['qty']
            date = datetime.strptime(r['date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
            if wiz['report_type'] <> 'price' and r['type'] == 'price':
                continue
            res.append({'date': date,
                    'lot': lot,
                    'state': r['state'],
                    'location': r['location'],
                    'dugaar': r['dugaar'],
                    'rep_type': r['rep_type'],
                    'partner': r['partner'],
                    'move_id': r['move_id'],
                    'price': r['price'],
                    'in_qty': in_qty,
                    'out_qty': out_qty,
                    'cost': r['cost'] or 0.0})
        return res
    
    def export_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'stock.move'
        datas['form'] = self.read(cr, uid, ids)[0]
        if 'warehouse' not in context:
            context['warehouse'] = datas['form']['warehouse_id'][0]
        form = self.browse(cr, uid, ids[0], context=context)
        # Өгөгдлөө авах
        body = self.get_log_message(cr, uid, ids, context=context)
        message = u"[Бүртгэл хяналтын баримт][XLS][PROCESSING] %s" % body
        _logger.info(message)
        wiz = {}
        d1 = datetime.now()
        ctx = context.copy()
        warehouse = company = ''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if 'company' not in ctx:
            ctx.update({'company_id':user.company_id.id})
        wiz.update({'company_id': user.company_id.id})
        lot_name = due_date = '..................'
        from_date = to_date = ''
        max_qty = min_qty = '..................'
        wiz['draft'] = form.draft
        wiz.update({'draft': form.draft,
                    'report_type': form.report_type,
                    'warehouse_id': form.warehouse_id.id,
                    'prod_id': form.product_id.id,
                    'from_date': form.from_date,
                    'to_date': form.to_date})
        wiz.update({'report_type': form.report_type})
        wiz.update({'warehouse_id': form.warehouse_id.id})
        wiz.update({'price_type': form.warehouse_id.public_price_type.field})
        wiz.update({'prod_id': form.product_id.id})
        wiz.update({'lot_id': (form.prodlot_id and form.prodlot_id.id) or False})
        if form.prodlot_id:
            lot = self.pool.get('stock.production.lot').browse(cr, uid, form.prodlot_id.id, context=ctx)
            if lot and lot.name: lot_name = lot.name
            if lot and lot.life_date: due_date = lot.life_date
        first_avail = self.get_available(cr, uid, wiz) or 0
        result = self.get_move_data(cr, uid, wiz)
        cr.execute("""SELECT product_max_qty AS max_qty, product_min_qty AS min_qty 
                        FROM stock_warehouse_orderpoint WHERE product_id = %s AND warehouse_id = %s"""%(form.product_id.id,form.warehouse_id.id))
        point = cr.dictfetchone()
        if point and point['max_qty']: max_qty = str(point['max_qty'])
        if point and point['min_qty']: min_qty = str(point['min_qty'])
        
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Stock Product Check')
        report_name = u''
        mayagt = u''
        if form.report_type == 'price':
            mayagt = u'Маягт БМ-5-3'
            report_name = u"Агуулахын бүртгэл, хяналтын баримт /Худалдах үнээр/"
            sheet.write_merge(0, 0, 1, 14, user.company_id.partner_id.name, xlwt.easyxf('font:bold on;align:wrap on,vert centre,horiz right;borders: bottom double;'))
        elif form.report_type == 'cost':
            mayagt = u'Маягт БМ-5-2'
            report_name = u"Агуулахын бүртгэл, хяналтын баримт /Өртөгөөр/"
            sheet.write_merge(0, 0, 1, 13, user.company_id.partner_id.name, xlwt.easyxf('font:bold on;align:wrap on,vert centre,horiz right;borders: bottom double;'))
        else:
            mayagt = u'Маягт БМ-5-1'
            report_name = u"Агуулахын бүртгэл, хяналтын баримт"
            sheet.write_merge(0, 0, 1, 10, user.company_id.partner_id.name, xlwt.easyxf('font:bold on;align:wrap on,vert centre,horiz right;borders: bottom double;'))
        sheet.write(1, 2, mayagt, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;'))
        sheet.write_merge(2, 2, 1, 7, report_name, xlwt.easyxf('font:bold on, height 250;align:wrap off,vert centre,horiz center;'))
        now_date = time.strftime('%Y-%m-%d %H:%M')
        #styles
        number_xf = xlwt.easyxf('font: height 160; align: horz right; borders: top thin, left thin, bottom thin, right thin;', num_format_str='#,##0.00')
        number_gold_xf = xlwt.easyxf('font: height 160; align: horz right; borders: top thin, left thin, bottom thin, right thin; pattern: pattern solid, fore_colour gold', num_format_str='#,##0.00')
        number_bold_xf = xlwt.easyxf('font: height 160, bold on; align: horz right; borders: top thin, left thin, bottom thin, right thin;', num_format_str='#,##0.00')
        text_xf =  xlwt.easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin;')
        text_gold_xf =  xlwt.easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin; pattern: pattern solid, fore_colour gold')
        text_bold_xf =  xlwt.easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin;')
        text_center_xf =  xlwt.easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin;')
        text_center_gold_xf =  xlwt.easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin; pattern: pattern solid, fore_colour gold')
        text_center_bold_xf =  xlwt.easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin;')
        heading_xf =  xlwt.easyxf('font: bold on, height 180; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin; pattern: pattern solid, fore_colour gray25')
        footer_xf =  xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;')
        footer_right_xf =  xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz right;')
        footer_bold_xf =  xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;')
        
        sheet.write(4, 2, u"Салбар, нэгжийн нэр: %s"%(form.warehouse_id.name), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(4, 6, u"Баримтын дугаар: -----", xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(5, 2, u'Бараа материалын бар код: %s' % (form.product_id.ean13 or ''), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(5, 6, u'Дотоод код : %s' %(form.product_id.default_code or ''), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(6, 2, u'Бараа материалын нэр:   %s'%(form.product_id.name or ''), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(6, 6, u'Х.Н:   %s'%form.product_id.uom_id.name, xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(7, 2, u'Серийн дугаар: %s'%(lot_name), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(7, 6, u'Дуусах хугацаа: %s'%(due_date), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(8, 2, u'Аюулгүй нөөц: %s'%(min_qty), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(8, 6, u'Дээд нөөц: %s'%(max_qty), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(9, 2, u'Хэвлэсэн огноо: %s'%(now_date), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.write(9, 6, u'Хяналтын хугацаа: %s-аас %s хүртэл'%(form.from_date,form.to_date), xlwt.easyxf('font:bold on,color 0x0C;align:wrap off,vert centre,horiz left;'))
        sheet.row(1).height = 400
        rowx = 11
        count = 0
        inch = 300
        in_total = out_total = 0
        if form.report_type == 'owner':
            sheet.write_merge(rowx, rowx+1, 1, 1, u'Д/д', heading_xf)
            sheet.write_merge(rowx, rowx, 2, 6, u'Баримтын', heading_xf)
            sheet.write(rowx+1, 2, u'Огноо', heading_xf)
            sheet.write(rowx+1, 3, u'Төрөл', heading_xf)
            sheet.write(rowx+1, 4, u'Дугаар', heading_xf)
            sheet.write(rowx+1, 5, u'Хөдөлгөөн', heading_xf)
            sheet.write(rowx+1, 6, u'Сери', heading_xf)
            sheet.write_merge(rowx, rowx+1, 7, 7, u'Харилцагч', heading_xf)
            sheet.write_merge(rowx, rowx, 8, 10, u'Тоо хэмжээ', heading_xf)
            sheet.write(rowx+1, 8, u'Орлого', heading_xf)
            sheet.write(rowx+1, 9, u'Зарлага', heading_xf)
            sheet.write(rowx+1, 10, u'Үлдэгдэл', heading_xf)
            rowx += 2
            sheet.write(rowx, 1, u'X', text_center_xf)
            sheet.write(rowx, 2, u'X', text_center_xf)
            sheet.write(rowx, 3, u'X', text_center_xf)
            sheet.write(rowx, 4, u'X', text_center_xf)
            sheet.write(rowx, 5, u'X', text_center_xf)
            sheet.write(rowx, 6, u'X', text_center_xf)
            sheet.write(rowx, 7, u'Эхний үлдэгдэл', text_center_bold_xf)
            sheet.write(rowx, 8, u'X', text_center_xf)
            sheet.write(rowx, 9, u'X', text_center_xf)
            sheet.write(rowx, 10, first_avail, number_bold_xf)
            rowx += 1
            if result:
                for r in result:
                    count += 1  
                    rep_type = ''
                    dugaar = partner = seri = moves = ''
                    in_qty = out_qty = avail = 0
                    
                    if r['rep_type'] == 'procure':
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        if move.procurement_id:
                            if move.procurement_id.transit_order_id:
                                moves +=  move.procurement_id.transit_order_id.supply_warehouse_id.name
                                moves += ' --> ' + move.procurement_id.transit_order_id.warehouse_id.name
                        else:
                            transit_ids = self.pool.get('stock.transit.order').search(cr, uid, [('name', '=', move.origin)])
                            if transit_ids:
                                transit = self.pool.get('stock.transit.order').browse(cr, uid, transit_ids, context=context)[0]
                                moves +=  transit.supply_warehouse_id.name
                                moves += ' --> ' + transit.warehouse_id.name
                    
                    if r['dugaar']: 
                        if r['dugaar'] == 'pos':
                            dugaar = r['location']
                        else:
                            dugaar = r['dugaar']
                    if r['partner']: partner = r['partner']
                    if r['lot']: seri = r['lot']
                    if r['in_qty'] and r['in_qty'] <> 0:
                        in_total += r['in_qty']
                        in_qty = r['in_qty']
                        first_avail += r['in_qty'] or 0
                    if r['out_qty'] and r['out_qty'] <> 0: 
                        out_total += r['out_qty']
                        out_qty = r['out_qty']
                        first_avail -= r['out_qty'] or 0
                    if r['rep_type']:
                        if r['rep_type'] == 'purchase': rep_type = u'Худалдан авалт'
                        elif r['rep_type'] == 'inventory': rep_type = u'Тооллого'
                        elif r['rep_type'] == 'swap': rep_type = u'Солилцоо'
                        elif r['rep_type'] == 'consume': rep_type = u'Дотоод зарлага'
                        elif r['rep_type'] == 'procure': rep_type = u'Нөхөн дүүргэлт'
                        elif r['rep_type'] == 'refund_purchase': rep_type = u'Худалдан авалтын буцаалт'
                        elif r['rep_type'] == 'refund': rep_type = u'Буцаалт'
                        elif r['rep_type'] == 'internal': rep_type = u'Дотоод хөдөлгөөн'
                        elif r['rep_type'] == 'pos': rep_type = u'Посын борлуулалт'
                        elif r['rep_type'] == 'mrp': rep_type = u'Үйлдвэрлэл'
                        elif r['rep_type'] == 'refund_mrp': rep_type = u'Үйлдвэрлэлийн буцаалт'
                        elif r['rep_type'] == 'collection': rep_type = u'Түүвэр'
                        else: rep_type = r['rep_type']
                    if r['rep_type'] in ('pos','internal') and r['partner'] is None:
                        rep_type = r['location']
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        partner = move.location_id.name
                    if form.draft and  r['state'] != 'done':
                        sheet.write(rowx, 1, count, text_center_gold_xf)
                        sheet.write(rowx, 2, r['date'], text_center_gold_xf)
                        sheet.write(rowx, 3, rep_type, text_center_gold_xf)
                        sheet.write(rowx, 4, dugaar, text_center_gold_xf)
                        sheet.write(rowx, 5, moves, text_center_gold_xf)
                        sheet.write(rowx, 6, seri, text_center_gold_xf)
                        sheet.write(rowx, 7, partner, text_gold_xf)
                        sheet.write(rowx, 8, (in_qty <> 0 and in_qty) or '', number_gold_xf)
                        sheet.write(rowx, 9, (out_qty <> 0 and out_qty) or '', number_gold_xf)
                        sheet.write(rowx, 10, first_avail, number_gold_xf)
                    else:
                        sheet.write(rowx, 1, count, text_center_xf)
                        sheet.write(rowx, 2, r['date'], text_center_xf)
                        sheet.write(rowx, 3, rep_type, text_center_xf)
                        sheet.write(rowx, 4, dugaar, text_center_xf)
                        sheet.write(rowx, 5, moves, text_center_xf)
                        sheet.write(rowx, 6, seri, text_xf)
                        sheet.write(rowx, 7, partner, text_xf)
                        sheet.write(rowx, 8, (in_qty <> 0 and in_qty) or '', number_xf)
                        sheet.write(rowx, 9, (out_qty <> 0 and out_qty) or '', number_xf)
                        sheet.write(rowx, 10, first_avail, number_xf)
                    rowx += 1
            sheet.write(rowx, 1, '', text_center_xf)
            sheet.write(rowx, 2, '', text_center_xf)
            sheet.write(rowx, 3, 'Бүгд дүн', text_center_bold_xf)
            sheet.write(rowx, 4, '', text_center_xf)
            sheet.write(rowx, 5, '', text_center_xf)
            sheet.write(rowx, 6, '', text_center_xf)
            sheet.write(rowx, 7, '', text_xf)
            sheet.write(rowx, 8, in_total, number_bold_xf)
            sheet.write(rowx, 9, out_total, number_bold_xf)
            sheet.write(rowx, 10, first_avail, number_bold_xf)
            
            sheet.write(rowx+1, 2, u'Хяналтаар: ', footer_bold_xf)
            sheet.write(rowx+1, 8, u'Бодит үлдэгдэл: ', footer_xf)
            sheet.write(rowx+2, 8, u'Зөрүү', footer_xf)
            sheet.write(rowx+1, 10, '', heading_xf)
            sheet.write(rowx+2, 10, '', heading_xf)
            
            rowx += 3
            sheet.write(rowx, 3, u'Эд хариуцагчийн тайлбар: ................................................................................................', footer_xf)
            sheet.write(rowx+1, 6, u'.........................................................................................................................', footer_right_xf)
            sheet.write(rowx+2, 3, u'Хяналтын талаарх дүгнэлт, шийдвэр: ......................................................................................', footer_xf)
            sheet.write(rowx+3, 6, u'.........................................................................................................................', footer_right_xf)
            sheet.write(rowx+4, 3, u'Хянасан эрх бүхий албан тушаалтан: ...................................ажилтай.............................................', footer_xf)
            sheet.write(rowx+5, 6, u'гарын үсэг: ........................................................................./......................................./', footer_right_xf)
            sheet.write(rowx+6, 3, u'байлцсан: гарын үсэг: .............................................................../......................................./', footer_xf)
            sheet.write(rowx+7, 6, u'гарын үсэг: ........................................................................./......................................./', footer_right_xf)
            sheet.write(rowx+8, 3, u'Эд хариуцагч: ......................................................................./......................................./', footer_xf)
            sheet.write(rowx+9, 6, u'...................................................................................../......................................./', footer_right_xf)
            sheet.write(rowx+10, 3, u'Огноо: .................................', footer_xf)
            sheet.col(0).width = 2*inch
            sheet.col(1).width = 5*inch
            sheet.col(2).width = 15*inch
            sheet.col(3).width = 15*inch
            sheet.col(4).width = 15*inch
            sheet.col(5).width = 25*inch
            sheet.col(6).width = 15*inch
            sheet.col(7).width = 35*inch
            sheet.col(8).width = 12*inch
            sheet.col(9).width = 12*inch
            sheet.col(10).width = 15*inch
        elif form.report_type == 'price':
            first_price = self.get_price(cr, uid, wiz, 'first', context=context)
            last_price = self.get_price(cr, uid, wiz, 'last', context=context)
            sheet.write_merge(rowx, rowx+1, 1, 1, u'Д/д', heading_xf)
            sheet.write_merge(rowx, rowx, 2, 6, u'Баримтын', heading_xf)
            sheet.write(rowx+1, 2, u'Огноо', heading_xf)
            sheet.write(rowx+1, 3, u'Төрөл', heading_xf)
            sheet.write(rowx+1, 4, u'Дугаар', heading_xf)
            sheet.write(rowx+1, 5, u'Хөдөлгөөн', heading_xf)
            sheet.write(rowx+1, 6, u'Сери', heading_xf)
            sheet.write_merge(rowx, rowx+1, 7, 7, u'Харилцагч', heading_xf)
            sheet.write_merge(rowx, rowx+1, 8, 8, u'Тоо хэмжээ', heading_xf)
            sheet.write_merge(rowx, rowx+1, 9, 9, u'Нэгж үнэ', heading_xf)
            sheet.write_merge(rowx, rowx, 10, 13, u'Нийт дүн /төгрөгөөр/', heading_xf)
            sheet.write(rowx+1, 10, u'Орлого', heading_xf)
            sheet.write(rowx+1, 11, u'Зарлага', heading_xf)
            sheet.write(rowx+1, 12, u'Үнийн өөрчлөлт', heading_xf)
            sheet.write(rowx+1, 13, u'Үлдэгдэл', heading_xf)
            sheet.write_merge(rowx, rowx+1, 14, 14, u'Үлдэгдэл тоо хэмжээ', heading_xf)
            rowx += 2
            sheet.write(rowx, 1, u'X', text_center_xf)
            sheet.write(rowx, 2, u'X', text_center_xf)
            sheet.write(rowx, 3, u'X', text_center_xf)
            sheet.write(rowx, 4, u'X', text_center_xf)
            sheet.write(rowx, 5, u'X', text_center_xf)
            sheet.write(rowx, 6, u'X', text_center_xf)
            sheet.write(rowx, 7, u'Эхний үлдэгдэл', text_center_bold_xf)
            sheet.write(rowx, 8, first_avail, number_bold_xf)
            sheet.write(rowx, 9, first_price, number_bold_xf)
            sheet.write(rowx, 10, u'X', text_center_xf)
            sheet.write(rowx, 11, u'X', text_center_xf)
            sheet.write(rowx, 12, u'X', text_center_xf)
            sheet.write(rowx, 13, (first_avail <> 0 and first_price <> 0) and (first_avail * first_price) or '', number_bold_xf)
            sheet.write(rowx, 14, first_avail, number_bold_xf)
            rowx += 1
            change = in_total_qty = 0
            change_total = 0
            diff_total = 0
            if first_price <> 0:
                change = first_price
            if result:
                for r in result:
                    diff = 0
                    unit = 0
                    count += 1
                    price = 0 #form.product_id.lst_price
                    rep_type = ''
                    dugaar = partner = seri = moves = ''
                    in_qty = out_qty = avail = 0
                    diff_price = 0
                    
                    if r['rep_type'] == 'procure':
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        if move.procurement_id:
                            if move.procurement_id.transit_order_id:
                                moves +=  move.procurement_id.transit_order_id.supply_warehouse_id.name
                                moves += ' --> ' + move.procurement_id.transit_order_id.warehouse_id.name
                        else:
                            transit_ids = self.pool.get('stock.transit.order').search(cr, uid, [('name', '=', move.origin)])
                            if transit_ids:
                                transit = self.pool.get('stock.transit.order').browse(cr, uid, transit_ids, context=context)[0]
                                moves +=  transit.supply_warehouse_id.name
                                moves += ' --> ' + transit.warehouse_id.name
                            
                    if r['partner']: 
                        partner = r['partner']
                    if r['lot']: 
                        if r['lot'] <> 'price':
                            seri = r['lot']
                    if r['in_qty'] and r['in_qty'] <> 0:
                        in_total_qty += r['in_qty']
                        in_qty = r['in_qty']
                        first_avail += r['in_qty'] or 0
                        diff  = r['in_qty']
                        if r['price']: in_total += (in_qty * r['price'])
                    if r['out_qty'] and r['out_qty'] <> 0:
                        in_total_qty -= r['out_qty']
                        out_qty = r['out_qty']
                        first_avail -= r['out_qty'] or 0
                        diff = r['out_qty']
                        if r['price']: out_total += (out_qty * r['price'])
                    if r['price']:
                        if change == 0: change = r['price']
                        if change <> r['price']:
                            if r['dugaar'] and r['dugaar'] == 'price':
                                unit = (r['price'] - change)
                                change_total += (unit * first_avail)
                        price = r['price']
                    if r['dugaar']: 
                        if r['dugaar'] == 'pos':
                            dugaar = r['location']
                        elif r['dugaar'] == 'price':
                            if r['price']: change = r['price']
                            dugaar = u'Үнэ өөрчлөлт'
#                            diff = first_avail
                        else:
                            dugaar = r['dugaar']
                    if r['rep_type']:
                        if r['rep_type'] == 'purchase': rep_type = u'Худалдан авалт'
                        elif r['rep_type'] == 'inventory': rep_type = u'Тооллого'
                        elif r['rep_type'] == 'swap': rep_type = u'Солилцоо'
                        elif r['rep_type'] == 'consume': rep_type = u'Дотоод зарлага'
                        elif r['rep_type'] == 'procure': rep_type = u'Нөхөн дүүргэлт'
                        elif r['rep_type'] == 'refund_purchase': rep_type = u'Худалдан авалтын буцаалт'
                        elif r['rep_type'] == 'refund': rep_type = u'Буцаалт'
                        elif r['rep_type'] == 'internal': rep_type = u'Дотоод хөдөлгөөн'
                        elif r['rep_type'] == 'pos': rep_type = u'Посын борлуулалт'
                        elif r['rep_type'] == 'mrp': rep_type = u'Үйлдвэрлэл'
                        elif r['rep_type'] == 'refund_mrp': rep_type = u'Үйлдвэрлэлийн буцаалт'
                        elif r['rep_type'] == 'price': rep_type = u'Үнэ өөрчлөлт'
                        else: rep_type = r['rep_type']
                    if r['rep_type'] in ('pos','internal') and r['partner'] is None:
                        rep_type = r['location']
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        partner = move.location_id.name
                    if form.draft and r['state'] != 'done':
                        sheet.write(rowx, 1, count, text_center_gold_xf)
                        sheet.write(rowx, 2, r['date'], text_center_gold_xf)
                        sheet.write(rowx, 3, rep_type, text_center_gold_xf)
                        sheet.write(rowx, 4, dugaar, text_center_gold_xf)
                        sheet.write(rowx, 5, moves, text_center_gold_xf)
                        sheet.write(rowx, 6, seri, text_center_gold_xf)
                        sheet.write(rowx, 7, partner, text_gold_xf)
                        sheet.write(rowx, 8, (diff <> 0 and diff) or '', number_gold_xf)
                        sheet.write(rowx, 9, (price <> 0 and price) or '', number_gold_xf)
                        sheet.write(rowx, 10, (in_qty <> 0 and in_qty * price) or '', number_gold_xf)
                        sheet.write(rowx, 11, (out_qty <> 0 and out_qty * price) or '', number_gold_xf)
                        sheet.write(rowx, 12, ((unit > 0 and first_avail > 0 and unit * first_avail) or 
                                             (unit < 0 and first_avail > 0 and '('+str(abs(unit * first_avail))+')')) or '', number_gold_xf)
                        sheet.write(rowx, 13, (change <> 0 and (change * first_avail)) or '', number_gold_xf)
                        sheet.write(rowx, 14, first_avail, number_gold_xf)
                    else:
                        sheet.write(rowx, 1, count, text_center_xf)
                        sheet.write(rowx, 2, r['date'], text_center_xf)
                        sheet.write(rowx, 3, rep_type, text_center_xf)
                        sheet.write(rowx, 4, dugaar, text_center_xf)
                        sheet.write(rowx, 5, moves, text_center_xf)
                        sheet.write(rowx, 6, seri, text_center_xf)
                        sheet.write(rowx, 7, partner, text_xf)
                        sheet.write(rowx, 8, (diff <> 0 and diff) or '', number_xf)
                        sheet.write(rowx, 9, (price <> 0 and price) or '', number_xf)
                        sheet.write(rowx, 10, (in_qty <> 0 and in_qty * price) or '', number_xf)
                        sheet.write(rowx, 11, (out_qty <> 0 and out_qty * price) or '', number_xf)
                        sheet.write(rowx, 12, ((unit > 0 and first_avail > 0 and unit * first_avail) or 
                                             (unit < 0 and first_avail > 0 and '('+str(abs(unit * first_avail))+')')) or '', number_xf)
                        sheet.write(rowx, 13, (change <> 0 and (change * first_avail)) or '', number_xf)
                        sheet.write(rowx, 14, first_avail, number_xf)
                    rowx += 1
            sheet.write(rowx, 1, '', text_center_xf)
            sheet.write(rowx, 2, '', text_center_xf)
            sheet.write(rowx, 3, '', text_center_xf)
            sheet.write(rowx, 4, '', text_center_xf)
            sheet.write(rowx, 5, '', text_center_xf)
            sheet.write(rowx, 6, '', text_center_xf)
            sheet.write(rowx, 7, u'Орлого, Зарлагын дүн', text_center_bold_xf)
            sheet.write(rowx, 8, '', text_center_xf)
            sheet.write(rowx, 9, '', text_center_xf)
            sheet.write(rowx, 10, in_total, number_bold_xf)
            sheet.write(rowx, 11, out_total, number_bold_xf)
            sheet.write(rowx, 12, change_total, number_bold_xf)
            sheet.write(rowx, 13, '', text_center_xf)
            sheet.write(rowx, 14, '', text_center_xf)
            rowx += 3
            sheet.write(rowx, 3, u'Нягтлан бодогч: ......................................................................./......................................./', footer_xf)
            rowx += 2
            sheet.write(rowx, 3, u'Огноо: .................................', footer_xf)
            sheet.col(0).width = 2*inch
            sheet.col(1).width = 5*inch
            sheet.col(2).width = 15*inch
            sheet.col(3).width = 15*inch
            sheet.col(4).width = 15*inch
            sheet.col(5).width = 25*inch
            sheet.col(6).width = 15*inch
            sheet.col(7).width = 35*inch
            sheet.col(8).width = 10*inch
            sheet.col(9).width = 10*inch
            sheet.col(10).width = 12*inch
            sheet.col(11).width = 12*inch
            sheet.col(12).width = 12*inch
            sheet.col(13).width = 12*inch
            sheet.col(14).width = 12*inch
        else:
            first_cost = self.get_first_cost(cr, uid, wiz) or 0
            sheet.write_merge(rowx, rowx+1, 1, 1, u'Д/д', heading_xf)
            sheet.write_merge(rowx, rowx, 2, 6, u'Баримтын', heading_xf)
            sheet.write(rowx+1, 2, u'Огноо', heading_xf)
            sheet.write(rowx+1, 3, u'Төрөл', heading_xf)
            sheet.write(rowx+1, 4, u'Дугаар', heading_xf)
            sheet.write(rowx+1, 5, u'Хөдөлгөөн', heading_xf)
            sheet.write(rowx+1, 6, u'Сери', heading_xf)
            sheet.write_merge(rowx, rowx+1, 7, 7, u'Харилцагч', heading_xf)
            sheet.write_merge(rowx, rowx+1, 8, 8, u'Тоо хэмжээ', heading_xf)
            sheet.write_merge(rowx, rowx+1, 9, 9, u'Нэгж Өртөг', heading_xf)
            sheet.write_merge(rowx, rowx, 10, 12, u'Нийт дүн /Өртөгөөр/', heading_xf)
            sheet.write(rowx+1, 10, u'Орлого', heading_xf)
            sheet.write(rowx+1, 11, u'Зарлага', heading_xf)
            sheet.write(rowx+1, 12, u'Үлдэгдэл', heading_xf)
            sheet.write_merge(rowx, rowx+1, 13, 13, u'Үлдэгдэл тоо хэмжээ', heading_xf)
            rowx += 2
            sheet.write(rowx, 1, u'X', text_center_xf)
            sheet.write(rowx, 2, u'X', text_center_xf)
            sheet.write(rowx, 3, u'X', text_center_xf)
            sheet.write(rowx, 4, u'X', text_center_xf)
            sheet.write(rowx, 5, u'X', text_center_xf)
            sheet.write(rowx, 6, u'X', text_center_xf)
            sheet.write(rowx, 7, u'Эхний үлдэгдэл', text_center_bold_xf)
            sheet.write(rowx, 8, first_avail, number_bold_xf)
            sheet.write(rowx, 9, first_cost, number_bold_xf)
            sheet.write(rowx, 10, u'X', text_center_xf)
            sheet.write(rowx, 11, u'X', text_center_xf)
            sheet.write(rowx, 12, (first_avail <> 0 and first_cost <> 0) and (first_avail * first_cost) or '', number_bold_xf)
            sheet.write(rowx, 13, first_avail, number_bold_xf)
            rowx += 1
            last_cost = first_cost
            qty = 0
            in_total = out_total = 0
            if result:
                for r in result:
                    diff = 0
                    tmp_cost = 0
                    count += 1
                    cost = 0#form.product_id.standard_price
                    rep_type = ''
                    dugaar = partner = seri = moves =  ''
                    in_qty = out_qty = 0
                    
                    if r['rep_type'] == 'procure':
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        if move.procurement_id:
                            if move.procurement_id.transit_order_id:
                                moves +=  move.procurement_id.transit_order_id.supply_warehouse_id.name
                                moves += ' --> ' + move.procurement_id.transit_order_id.warehouse_id.name
                        else:
                            transit_ids = self.pool.get('stock.transit.order').search(cr, uid, [('name', '=', move.origin)])
                            if transit_ids:
                                transit = self.pool.get('stock.transit.order').browse(cr, uid, transit_ids, context=context)[0]
                                moves +=  transit.supply_warehouse_id.name
                                moves += ' --> ' + transit.warehouse_id.name
                            
                    if r['partner']: 
                        partner = r['partner']
                    if r['lot']: 
                        if r['lot'] <> 'price':
                            seri = r['lot']
                    if r['in_qty'] and r['in_qty'] <> 0:
                        qty += r['in_qty']
                        in_qty = r['in_qty']
                        
                        #last_cost = r['cost']
                        diff  = r['in_qty']
                        if r['cost']: in_total += (in_qty * r['cost'])
                        tmp_cost = in_qty * r['cost']
                        if last_cost > 0 and first_avail > 0:
                            ftotal = last_cost * first_avail
                            mtotal = r['cost'] * r['in_qty']
                        else:
                            ftotal = 0
                            mtotal = r['cost'] * r['in_qty']
                        first_avail += r['in_qty'] or 0
                        if ftotal > 0 and mtotal > 0:
                            last_cost = (ftotal+mtotal)/first_avail
                    if r['out_qty'] and r['out_qty'] <> 0:
                        qty += r['out_qty']
                        out_qty = r['out_qty']
                        first_avail -= r['out_qty'] or 0
                        #last_cost = r['cost']
                        diff = r['out_qty']
                        if r['cost']: out_total += (out_qty * r['cost'])
                        tmp_cost = out_qty * r['cost']
                    if r['cost']:
                        cost = r['cost']
                    if r['dugaar']: 
                        if r['dugaar'] == 'pos':
                            dugaar = r['location']
                        else:
                            dugaar = r['dugaar']
                    if r['rep_type']:
                        if r['rep_type'] == 'purchase': rep_type = u'Худалдан авалт'
                        elif r['rep_type'] == 'inventory': rep_type = u'Тооллого'
                        elif r['rep_type'] == 'swap': rep_type = u'Солилцоо'
                        elif r['rep_type'] == 'consume': rep_type = u'Дотоод зарлага'
                        elif r['rep_type'] == 'procure': rep_type = u'Нөхөн дүүргэлт'
                        elif r['rep_type'] == 'refund_purchase': rep_type = u'Худалдан авалтын буцаалт'
                        elif r['rep_type'] == 'refund': rep_type = u'Буцаалт'
                        elif r['rep_type'] == 'internal': rep_type = u'Дотоод хөдөлгөөн'
                        elif r['rep_type'] == 'pos': rep_type = u'Посын борлуулалт'
                        elif r['rep_type'] == 'mrp': rep_type = u'Үйлдвэрлэл'
                        elif r['rep_type'] == 'refund_mrp': rep_type = u'Үйлдвэрлэлийн буцаалт'
                        else: rep_type = r['rep_type']
                    if r['rep_type'] in ('pos','internal') and r['partner'] is None:
                        rep_type = r['location']
                        move = self.pool.get('stock.move').browse(cr, uid, r['move_id'], context=context)[0]
                        partner = move.location_id.name
                    if form.draft and r['state'] != 'done':
                        sheet.write(rowx, 1, count, text_center_gold_xf)
                        sheet.write(rowx, 2, r['date'], text_center_gold_xf)
                        sheet.write(rowx, 3, rep_type, text_center_gold_xf)
                        sheet.write(rowx, 4, dugaar, text_center_gold_xf)
                        sheet.write(rowx, 5, moves, text_center_gold_xf)
                        sheet.write(rowx, 6, seri, text_center_gold_xf)
                        sheet.write(rowx, 7, partner, text_gold_xf)
                        sheet.write(rowx, 8, (diff <> 0 and diff) or '', number_gold_xf)
                        sheet.write(rowx, 9, (cost <> 0 and cost) or '', number_gold_xf)
                        sheet.write(rowx, 10, (in_qty <> 0 and in_qty * cost) or '', number_gold_xf)
                        sheet.write(rowx, 11, (out_qty <> 0 and out_qty * cost) or '', number_gold_xf)
                        sheet.write(rowx, 12, (first_avail <> 0 and first_avail * cost) or '', number_gold_xf)
                        sheet.write(rowx, 13, first_avail, number_gold_xf)
                    else:
                        sheet.write(rowx, 1, count, text_center_xf)
                        sheet.write(rowx, 2, r['date'], text_center_xf)
                        sheet.write(rowx, 3, rep_type, text_center_xf)
                        sheet.write(rowx, 4, dugaar, text_center_xf)
                        sheet.write(rowx, 5, moves, text_center_xf)
                        sheet.write(rowx, 6, seri, text_center_xf)
                        sheet.write(rowx, 7, partner, text_xf)
                        sheet.write(rowx, 8, (diff <> 0 and diff) or '', number_xf)
                        sheet.write(rowx, 9, (cost <> 0 and cost) or '', number_xf)
                        sheet.write(rowx, 10, (in_qty <> 0 and in_qty * cost) or '', number_xf)
                        sheet.write(rowx, 11, (out_qty <> 0 and out_qty * cost) or '', number_xf)
                        sheet.write(rowx, 12, (first_avail <> 0 and first_avail * cost) or '', number_xf)
                        sheet.write(rowx, 13, first_avail, number_xf)
                    rowx += 1
            sheet.write(rowx, 1, '', text_center_xf)
            sheet.write(rowx, 2, '', text_center_xf)
            sheet.write(rowx, 3, '', text_center_xf)
            sheet.write(rowx, 4, '', text_center_xf)
            sheet.write(rowx, 5, '', text_center_xf)
            sheet.write(rowx, 6, '', text_center_xf)
            sheet.write(rowx, 7, u'Орлого, Зарлагын дүн', text_center_bold_xf)
            sheet.write(rowx, 8, '', text_center_xf)
            sheet.write(rowx, 9, '', text_center_xf)
            sheet.write(rowx, 10, in_total, number_bold_xf)
            sheet.write(rowx, 11, out_total, number_bold_xf)
            sheet.write(rowx, 12, '', text_center_xf)
            sheet.write(rowx, 13, '', text_center_xf)
            rowx += 1
            last_total = last_total_qty = 0
            sheet.write(rowx, 1, u'X', text_center_xf)
            sheet.write(rowx, 2, u'X', text_center_xf)
            sheet.write(rowx, 3, u'X', text_center_xf)
            sheet.write(rowx, 4, u'X', text_center_xf)
            sheet.write(rowx, 5, u'X', text_center_xf)
            sheet.write(rowx, 6, u'X', text_center_xf)
            sheet.write(rowx, 7, u'', text_center_xf)
            sheet.write(rowx, 8, (qty and qty) or '0.0', number_bold_xf)
            sheet.write(rowx, 9, (last_cost and last_cost) or '0.0', number_bold_xf)
            sheet.write(rowx, 10, u'X', text_center_xf)
            sheet.write(rowx, 11, u'X', text_center_xf)
            sheet.write(rowx, 12, (last_cost and first_avail and (last_cost * first_avail)) or '0.0', number_bold_xf)
            sheet.write(rowx, 13, first_avail, number_bold_xf)
            rowx += 1
            rowx += 2
            sheet.write(rowx, 3, u'Нягтлан бодогч: ......................................................................./......................................./', footer_xf)
            rowx += 2
            sheet.write(rowx, 3, u'Огноо: .................................', footer_xf)
            sheet.col(0).width = 2*inch
            sheet.col(1).width = 5*inch
            sheet.col(2).width = 15*inch
            sheet.col(3).width = 15*inch
            sheet.col(4).width = 15*inch
            sheet.col(5).width = 25*inch
            sheet.col(6).width = 15*inch
            sheet.col(7).width = 35*inch
            sheet.col(8).width = 10*inch
            sheet.col(9).width = 10*inch
            sheet.col(10).width = 12*inch
            sheet.col(11).width = 12*inch
            sheet.col(12).width = 12*inch
            sheet.col(13).width = 12*inch
        buffer = StringIO()
        book.save(buffer)
        buffer.seek(0)
        
        out = base64.encodestring(buffer.getvalue())
        buffer.close()
        filename = self._name.replace('.', '_')
        filename = "%s_%s.xls" % (filename, time.strftime('%Y%m%d_%H%M'),)
        excel_id = self.pool.get('report.excel.output').create(cr, uid, {
                                'data':out,
                                'name':filename
        }, context=context)
        
        dta = datetime.now() - d1
        if dta.seconds > 60 :
            tm = '%sm %ss' %(dta.seconds / 60, dta.seconds % 60)
        else :
            tm = '%ss' % dta.seconds
        message = u"[Бүртгэл хяналтын баримт][XLS][COMPLETE (%s)] %s" % (tm, body)
        #self.pool.get('res.log').write(cr, uid, [log_id], {'name': message,'create_date':time.strftime('%Y-%m-%d %H:%M:%S')})
        _logger.info(message)
        mod_obj = self.env['ir.model.data']
        form_res = mod_obj.get_object_reference(cr, uid, 'l10n_mn_report_base', 'action_excel_output_view')
        form_id = form_res and form_res[1] or False
        return {
            'name': _('Stock Product Check'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.excel.output',
            'res_id': excel_id,
            'view_id': False,
            'views': [(form_id, 'form')],#[(form_id, 'form')],
            'context': context,
            'type': 'ir.actions.act_window',
            'target':'new',
            'nodestroy': True,
        }
    
    def print_report(self, cr, uid, ids, context=None):
        context = context or {}
        form = self.browse(cr, uid, ids[0], context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        wiz = {}
        wiz.update({'company_id': user.company_id.id})
        wiz['draft'] = form.draft
        lot_name = ''
        due_date = ''
        if form.prodlot_id:
            lot = self.pool.get('stock.production.lot').browse(cr, uid, form.prodlot_id.id, context=ctx)
            if lot and lot.name: lot_name = lot.name
            if lot and lot.life_date: due_date = lot.life_date
        wiz.update({'draft': form.draft,
                    'report_type': form.report_type,
                    'warehouse_id': form.warehouse_id.id,
                    'wname': form.warehouse_id.name,
                    'prod_id': form.product_id.id,
                    'from_date': form.from_date,
                    'to_date': form.to_date})
        wiz.update({'report_type': form.report_type})
        wiz.update({'warehouse_id': form.warehouse_id.id})
        wiz.update({'prod_id': form.product_id.id})
        wiz.update({'lot_id': (form.prodlot_id and form.prodlot_id.id) or False})
        first_avail = self.get_available(cr, uid, wiz)
        first_cost = self.get_first_cost(cr, uid, wiz) or 0
        first_price = self.get_price(cr, uid, wiz, 'first', context=context)
        result = self.get_move_data(cr, uid, wiz, context=context)
        data = {
            'ids': [],
            'model': 'report.product.move.check',
            'form': self.read(cr, uid, ids, [])[0],
            'wizard':{'from_date': form.from_date,
                      'to_date': form.to_date,
                      'prod_id': form.product_id.id,
                      'company': user.company_id.name,
                      'company_id': user.company_id.id,
                      'lot_name': lot_name,
                      'life_date': due_date,
                      'warehouse_id': form.warehouse_id.id,
                      'wname': form.warehouse_id.name,
                      'report_type': form.report_type,
                      'first_avail': first_avail,
                      'first_cost': first_cost,
                      'first_price': first_price,}
        }
        
        if data['form']['report_type'] == 'owner':
            
            body = (u"Агуулах бүртгэл, хяналтын баримт (Эхлэх Огноо='%s',Дуусах Огноо='%s', Бараа_id='%s',Агуулах='%s',prodlot_id='%s'" 
                    )% (form.from_date,form.to_date,form.product_id.name,form.warehouse_id.name,
                        form.prodlot_id and form.prodlot_id.name)
            message = u"[Тайлан][PDF][PROCESSING] %s" % body
            _logger.info(message)
            
        elif data['form']['report_type'] == 'price':
            
            body = (u"Агуулах бүртгэл, хяналтын баримт(Худалдах үнээр)(Эхлэх Огноо='%s',Дуусах Огноо='%s', Бараа_id='%s',Агуулах='%s',prodlot_id='%s'"
                    ) % (form.from_date,form.to_date,form.product_id.name,form.warehouse_id.name,
                        form.prodlot_id and form.prodlot_id.name)
            message = u"[Тайлан][PDF][PROCESSING] %s" % body
            _logger.info(message)
        elif data['form']['report_type'] == 'cost':

            body = (u"Агуулах бүртгэл, хяналтын баримт(Өртөгөөр)(Эхлэх Огноо='%s',Дуусах Огноо='%s', Бараа_id='%s',Агуулах='%s',prodlot_id='%s'"
                    ) % (form.from_date,form.to_date,form.product_id.name,form.warehouse_id.name,
                        form.prodlot_id and form.prodlot_id.name)
            message = u"[Тайлан][PDF][PROCESSING] %s" % body
            context.update({'report_log':True})
            #log_id = self.log(cr, uid, ids[0], message, context=context)
            _logger.info(message)
        return self.pool.get("report").get_action(cr, uid, [], 'l10n_mn_stock.report_product_move_check', data=data, context=context)
    
report_product_move_check()