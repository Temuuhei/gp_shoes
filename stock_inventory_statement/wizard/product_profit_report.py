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
from datetime import datetime
import time
from operator import itemgetter
import datetime

class product_profit_report(osv.osv_memory):
    _name = 'product.profit.report'
    _inherit = 'abstract.report.model'
    _description = 'Product Profit Report'
        
    
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'warehouse_ids': fields.many2many('stock.warehouse', 'product_profit_report_warehouse_rel', 'wizard_id', 'warehouse_id', 'Warehouse'),
        'prod_categ_ids': fields.many2many('product.category', 'product_profit_report_prod_categ_rel', 'wizard_id', 'prod_categ_id', 'Product Category',domain=['|',('parent_id','=',False),('parent_id.parent_id','=',False)]),
        'product_ids': fields.many2many('product.product', 'product_profit_report_product_rel', 'wizard_id', 'product_id', 'Product'),
        'partner_ids': fields.many2many('res.partner', 'product_profit_report_partner_rel', 'wizard_id', 'partner_id', 'Partner'),
        'team_ids': fields.many2many('crm.case.section', 'product_profit_report_team_rel',
                            'wizard_id', 'team_id', 'Sales Team'),
                                    
        'sorting': fields.selection([('default_code','Default Code'),
                                     ('name','Product Name')], 'Sorting', required = True),        
        'date_to': fields.date('To Date',),
        'date_from': fields.date('From Date',),
        'period_to': fields.many2one('account.period', 'To Period',),
        'period_from': fields.many2one('account.period', 'From Period',),
        'type': fields.selection([('detail','Detail'),
                                     ('summary','Summary'),
                                     ('branch','Branch')], 'Type', required = True),
    }


    def _get_period_to(self, cr, uid, context=None):        
        period_id = self.pool.get('account.period').search(cr, uid, [('date_stop', '=', time.strftime("%Y-12-31"))])
        return period_id[0]

    def _get_period_from(self, cr, uid, context=None):        
        period_id = self.pool.get('account.period').search(cr, uid, [('date_start', '=', time.strftime("%Y-01-01")),('date_stop', '=', time.strftime("%Y-01-31"))])
        return period_id[0]
    
    _defaults = {
        'company_id': lambda obj,cr,uid,c:obj.pool.get('res.company')._company_default_get(cr, uid, 'product.profit.report'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),        
        'sorting': 'default_code',
        'type': 'detail',
        'period_to': _get_period_to,
        'period_from': _get_period_from,
    }

    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)



    def get_export_data(self, cr, uid, ids, report_code, context=None):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        wiz = self.read(cr, uid, ids[0], context=context)
        data, titles, row_span = self.prepare_report_data(cr, uid, wiz, context=context)
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, wiz['warehouse_ids'], context=context)
        widths = [2,15,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5]
        sale_team = self.pool.get('crm.case.section')
        header_span = []
        if wiz['type'] == 'detail':
            headers = [
                [u'№', u'Бүтээгдэхүүний нэр', u'Борлуулалтын орлого', u'Өртөгийн зөрүү', u'Борлуулсан бүтээгдэхүүний өртөг', u'Хөнгөлөлт', u'Борлуулалтын хөнгөлөлт гэрээт', u'Акт', u'Маркетингийн зардал', u'Борлуулалтын зардал',
                 u'БУЗ', u'ЕУЗ', u'Санхүү', u'Бусад', u'Нийт зардал', u'Нийт ашиг', u'ТӨА', u'ТӨАХ'],                
            ]
            header_span = []

        if wiz['type'] == 'summary':
            headers = [
                 [u'№', u'Бүтээгдэхүүний нэр'],
                 [None,None],                 
            ]
            per_to = int(wiz['period_to'][1].split('/')[0])
            per_from = int(wiz['period_from'][1].split('/')[0])
            for i in range(per_from,per_to+1):
                title = u'' + str(i) + u' сар'
                headers[0].append(title)
            for i in range(per_from,per_to+1):                
                headers[1].append(u'Цэвэр ашиг')

            header_span = [((0,0),(0,1)),((1,0),(1,1))]
        if wiz['type'] == 'branch':
            headers = [
                 [u'№', u'Үзүүлэлт']
            ]
            if wiz['team_ids'] != []:
                sale_team_ids = sale_team.search(cr, uid, [('id','=',wiz['team_ids'])])
            else:
                sale_team_ids = sale_team.search(cr, uid, [])

            for team in sale_team.browse(cr, uid, sale_team_ids):
                headers[0].append(team.name)

        datas = {
            'title': u'Барааны ашгийн тайлан',
            'headers': headers,
            'header_span': header_span,
            'row_span': row_span,
            'titles': titles,
            'rows': data,
            'widths': widths,
        }
        return {'datas':datas}

    def get_product_all_sales(self, cr, uid, pid, loc_ids, date_start, date_stop, where, context=None):
        if context is None:
            context = {}
        cr.execute("SELECT m.product_id AS prod, u2.id AS uom, s.section_id, ccs.name AS tname, m.date as m_date, "
                                        "coalesce(SUM(m.product_qty/u.factor*u2.factor),0) AS q, "
                                        "pt.manufacturer AS fact, pt.categ_id AS categ, pp.ean13 AS barcode,"
                                        "SUM(tax.tax_id) AS tax, s.user_id AS uid, s.partner_id AS pid, "
                                        "coalesce(SUM(l.price_unit*m.product_qty/u.factor*u2.factor),0) AS s, "
                                        "coalesce(SUM(m.product_qty * l.price_unit * (l.discount / 100)/u.factor*u2.factor),0) AS d, "
                                        "coalesce(SUM(m.price_unit*m.product_qty),0) AS c, "
                                        "0 AS refund_q, 0 as refund_s, 0 as refund_d, 0 as refund_c "
                                   "FROM stock_move m "
                                        "JOIN product_product pp ON (pp.id=m.product_id) "
                                        "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                                        "JOIN product_uom u ON (u.id=m.product_uom) "
                                        "JOIN product_uom u2 ON (u2.id=pt.uom_id) "
                                        "JOIN procurement_order o ON (o.id=m.procurement_id) "
                                        "JOIN sale_order_line l ON (o.sale_line_id=l.id) "
                                        "JOIN sale_order s ON (l.order_id=s.id) "
                                        "LEFT JOIN sale_order_tax tax ON (l.id = tax.order_line_id) "
                                        "LEFT JOIN crm_case_section ccs ON s.section_id = ccs.id "
                                   "WHERE m.state = 'done' "+where+" and m.product_id in ("+','.join(map(str,pid))+") "
                                        "AND m.location_id in %s AND m.location_dest_id not in %s "
                                        "AND m.date >= %s AND m.date <= %s "
                                   "GROUP BY m.date,pp.ean13,m.product_id,u2.id,s.section_id,ccs.name,pt.manufacturer,pt.categ_id,s.user_id,s.partner_id ", 
                                (tuple(loc_ids), tuple(loc_ids), date_start + ' 00:00:00', date_stop + ' 23:59:59'))
        fetched = cr.dictfetchall()

        cr.execute("SELECT m.product_id AS prod, u2.id AS uom, s.section_id, ccs.name AS tname, m.date as m_date, "
                        "coalesce(SUM(m.product_qty/u.factor*u2.factor),0) AS refund_q, "
                        "pt.manufacturer AS fact, pt.categ_id AS categ, pp.ean13 AS barcode,"
                        "SUM(tax.tax_id) AS tax, s.user_id AS uid, s.partner_id AS pid, "
                        "0 as q, 0 as s, 0 as d, 0 as c, "
                        "coalesce(SUM(l.price_unit*m.product_qty/u.factor*u2.factor),0) AS refund_s, "
                        "coalesce(SUM(m.product_qty * l.price_unit * (l.discount / 100)/u.factor*u2.factor),0) AS refund_d, "
                        "coalesce(SUM(m.price_unit*m.product_qty),0) AS refund_c "
                   "FROM stock_move m "
                        "JOIN product_product pp ON (pp.id=m.product_id) "
                        "JOIN product_template pt ON (pt.id=pp.product_tmpl_id) "
                        "JOIN product_uom u ON (u.id=m.product_uom) "
                        "JOIN product_uom u2 ON (u2.id=pt.uom_id) "
                        "JOIN procurement_order o ON (o.id=m.procurement_id) "
                        "JOIN sale_order_line l ON (o.sale_line_id=l.id) "
                        "JOIN sale_order s ON (l.order_id=s.id) "
                        "LEFT JOIN sale_order_tax tax ON (l.id = tax.order_line_id) "
                        "LEFT JOIN crm_case_section ccs ON s.section_id = ccs.id "
                   "WHERE m.state = 'done' "+where+" and m.product_id in ("+','.join(map(str,pid))+") "
                        "AND m.location_id not in %s AND m.location_dest_id in %s "
                        "AND m.date >= %s AND m.date <= %s "
                   "GROUP BY m.date,pp.ean13,m.product_id,u2.id,s.section_id,ccs.name,pt.manufacturer,pt.categ_id,s.user_id,s.partner_id ", 
                (tuple(loc_ids), tuple(loc_ids), date_start + ' 00:00:00', date_stop + ' 23:59:59'))
        fetched1 = cr.dictfetchall()
        fetched += fetched1
        return fetched


    def get_root_categ(self, cr, uid, categ, context=None):        
        cr.execute("select parent_id from product_category where id = '"+str(categ)+"'")
        parent_categ = cr.fetchone()
        if parent_categ[0] == 1 and parent_categ[0] != None:
            return categ
        elif parent_categ[0] == None:
            return categ
        else:
            return self.get_root_categ(cr, uid, parent_categ[0], context=context)


    def get_all_expense(self, cr, uid, date_start, date_stop, loc_ids, where, context=None):
        if context is None:
            context = {}

        profit_config_obj = self.pool.get('product.profit.report.config').browse(cr, uid, [1])
        account_obj = self.pool.get('account.account')    
        '''
            Борлуулалтын орлогын данснаас сонгосон хугацаан дахь бүх орлогыг тооцох
        '''
        sale_income = 0.0
        all_product_ids = self.pool.get('product.product').search(cr, uid, [])
        all_sales = self.get_product_all_sales(cr, uid, all_product_ids, loc_ids, date_start, date_stop, where, context=context)
        for i in all_sales:
            sale_income += (i['s'] - i['refund_s']) - (((i['s'] - i['refund_s']) / 110) * 10)
        # for i in profit_config_obj.sale_income_ids:
        #         for account in account_obj.browse(cr, uid, [i.id], context=context):                    
        #             sale_income += (account.credit - account.debit)

        '''
            Өртөгийн зөрүүний данснаас сонгосон хугацаан дахь дүнг авах, Мөн өртөгийн зөрүүг хувиарлах барааны ангилалыг сонгох
        '''
        cost_diff = 0.0
        for i in profit_config_obj.cost_diff_ids:
                for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                    cost_diff += (account.debit)       

        cost_diff_categ = []
        for i in profit_config_obj.cost_product_category:
            cost_diff_categ.append(i.id)
        
        if cost_diff_categ != []:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',cost_diff_categ)])
            cost_product_id = self.pool.get('product.product').search(cr, uid, [('categ_id', 'in', categ_ids)])
        else:
            raise osv.except_osv(_('Warning !'), _(u'Өртөгийн зөрүүг хувиарлах барааны ангилалыг сонгоно уу!'))

        cost_diff_sales = self.get_product_all_sales(cr, uid, cost_product_id, loc_ids, date_start, date_stop, where, context=context)
        cost_diff_sum = 0.0
        for i in cost_diff_sales:
            income = (i['s'] - i['refund_s']) - (((i['s'] - i['refund_s']) / 110) * 10)
            cost_diff_sum += income  
                
        '''
            Борлуулалтын хөнгөлөлт гэрээт данснаас сонгосон хугацаан дахь дүнг авах
        '''
        sale_discount = 0.0
        for i in profit_config_obj.sale_discount_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                sale_discount += (account.debit)
        
        '''
            Актын зардал тооцох
        '''
        act_expense = 0.0        
        act_ids = []
        for i in profit_config_obj.acts_expense_ids:        
            act_ids.append(i.id)
            for account in account_obj.browse(cr, uid, [i.id], context=context):
                act_expense += (account.debit)
        
        cr.execute("select distinct(sm.product_id) from stock_move sm join stock_picking sp on sp.id = sm.picking_id "
                   "left join stock_consume_order co on co.id = sp.consume_order_id "
                   "where sm.state = 'done' and sm.date >= %s and sm.date <= %s and sp.consume_order_id is not null and co.expense_account_id in ("+','.join(map(str,act_ids))+") "
                   "group by sm.product_id "
                   "order by sm.product_id ",(date_start + ' 00:00:00', date_stop + ' 23:59:59'))
        act = cr.fetchall()
        act_product_id = []
        if act != []:
            for a in act:
                act_product_id.append(a[0])

        act_product_sum = 0.0
        if act_product_id != []:
            act_product_sales = self.get_product_all_sales(cr, uid, act_product_id, loc_ids, date_start, date_stop, where, context=context)            
            for i in act_product_sales:
                income = (i['s'] - i['refund_s']) - (((i['s'] - i['refund_s']) / 110) * 10)
                act_product_sum += income

        '''
            Маркетингийн зардлыг тооцох
        '''
        marketing_expense = 0.0        
        marketing_ids = []
        for i in profit_config_obj.marketing_analytic_account:        
            marketing_ids.append(i.id)

        if marketing_ids != []:            
            marketing_parent_categ_ids = self.pool.get('product.category').search(cr, uid, [('analytic_id','in',marketing_ids)])
            marketing_categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',marketing_parent_categ_ids)])
        else:
            raise osv.except_osv(_('Warning !'), _(u'Маркетингийн зардлын шинжилгээний данснуудыг сонгоно уу!'))

        if marketing_categ_ids != []:            
            marketing_prod_ids = self.pool.get('product.product').search(cr, uid, [('categ_id', 'in', marketing_categ_ids)], order="categ_id desc")
        else:
            raise osv.except_osv(_('Warning !'), _(u'Барааны ангилал дээр шинжилгээний данснуудыг сонгоно уу!'))            

        marketing_prod_sales = self.get_product_all_sales(cr, uid, marketing_prod_ids, loc_ids, date_start, date_stop, where, context=context)        
        categ_list = {}
        marketing_list = {}
        for i in marketing_prod_sales:            
            root_categ_id = self.get_root_categ(cr, uid, i['categ'], context=context)
            if root_categ_id not in categ_list:
                categ_list[root_categ_id] = {'income': (i['s'] - i['refund_s'])/1.1}
            else:
                categ_list[root_categ_id]['income'] += (i['s'] - i['refund_s'])/1.1

        for i in marketing_ids:
            cr.execute("select sum(amount) from account_analytic_line where account_id = '"+str(i)+"' and date >= '"+date_start+"' and date <= '"+date_stop+"'")
            marketing_fetched = cr.fetchone()

            if marketing_fetched[0] != None:
                marketing_list[i] = {'sum': marketing_fetched[0]}
            else:
                marketing_list[i] = {'sum': 0}
        
        '''
            Борлуулалтын зардлыг тооцох
        '''
        sale_expense_sum = 0.0
        for i in profit_config_obj.sale_expense_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                sale_expense_sum += (account.debit)

        '''
            Борлулуулалт удирдлагын зардлыг тооцох
        '''
        sale_management_sum = 0.0
        for i in profit_config_obj.sale_management_expense_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                sale_management_sum += (account.debit)

        cr.execute("select id from product_category where sale_discount > 0.0 and sale_discount is not null")
        sale_discount_categ_ids = cr.fetchall()
        categ_ids = []
        if sale_discount_categ_ids != []:
            for categ in sale_discount_categ_ids:
                categ_ids.append(categ[0])
        
        sale_discount_diff = sale_management_sum
        sale_income_diff = sale_income
        sale_management_categs = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',categ_ids)])
        if categ_ids != []:
            for categ in categ_ids:
                discount = self.pool.get('product.category').browse(cr, uid, categ).sale_discount                
                categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',[categ])])                
                prod_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)])
                prod_sales = self.get_product_all_sales(cr, uid, prod_ids, loc_ids, date_start, date_stop, where, context=context)
                for i in prod_sales:
                    sale = (((i['s'] - i['refund_s'])/1.1)/100)*discount
                    sale_discount_diff -= sale
                    sale = (i['s'] - i['refund_s'])
                    sale_income_diff -= sale

        '''
            Ерөнхий удирдлагын зардлыг тооцох
        '''
        general_management_sum = 0.0
        for i in profit_config_obj.general_management_expense_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                general_management_sum += (account.debit)

        '''
            Санхүүгийн зардлыг тооцох
        '''
        finance_sum = 0.0
        for i in profit_config_obj.finance_expense_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):                    
                finance_sum += (account.debit)

        '''
            Бусад зардлыг тооцох
        '''
        other_sum = 0.0
        for i in profit_config_obj.other_expense_ids:
            for account in account_obj.browse(cr, uid, [i.id], context=context):               
                other_sum += (account.debit)

        return cost_product_id,cost_diff_sum,cost_diff,sale_discount,sale_income,act_product_id,act_expense,act_product_sum,categ_list,marketing_list,sale_expense_sum,sale_management_categs,sale_management_sum,sale_income_diff,sale_discount_diff,general_management_sum,finance_sum,other_sum


    def prepare_report_data(self, cr, uid, wiz, context=None):
        if context is None:
            context = {}

        ctx = context.copy()        
        ctx['date_from'] = wiz['date_from']
        ctx['date_to'] =  wiz['date_to']
        
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [])
        warehouses = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_ids, context=context)
        company = self.pool.get('res.company').browse(cr, uid, wiz['company_id'][0], context=context)        
        titles = []
        data = []
        row_span = {}
        prices = {}
        total_dict = {}
        loc_ids = []
        where = ""
        date_start = wiz['date_from']
        date_stop = wiz['date_to']
        for warehouse in warehouses:
            locations = self.pool.get('stock.location').search(cr, uid, [('usage','=','internal'),
                                            ('location_id','child_of',[warehouse.view_location_id.id])], context=context)
            loc_ids.append(locations[0])

        if wiz['partner_ids']:
            where += " AND pt.manufacturer IN ("+','.join(map(str,wiz['partner_ids']))+") "
        if wiz['team_ids']:
            where += " AND s.section_id IN ("+','.join(map(str,wiz['team_ids']))+") "        
        if wiz['prod_categ_ids']:
            categ_ids = self.pool.get('product.category').search(cr, uid, [('parent_id','child_of',wiz['prod_categ_ids'])])
            where += ' AND pt.categ_id IN ('+','.join(map(str,categ_ids))+') '

        product_ids = []
        if wiz['product_ids'] != []:
            product_ids = wiz['product_ids']
        else:
            product_ids = product_obj.search(cr, uid, [('sale_ok','=',True)])

        per_to = int(wiz['period_to'][1].split('/')[0])
        per_from = int(wiz['period_from'][1].split('/')[0])
        year = int(wiz['period_from'][1].split('/')[1])
        months_sale = []
        number = 1
        col_sum = []
        if wiz['type'] == 'detail':
            sum1,sum2,sum3,sum4,sum5,sum6,sum7,sum8,sum9,sum10,sum11,sum12,sum13,sum14,sum15 = 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
            cost_product_id,cost_diff_sum,cost_diff,sale_discount,sale_income,act_product_id,act_expense,act_product_sum,categ_list,marketing_list,sale_expense_sum,sale_management_categs,sale_management_sum,sale_income_diff,sale_discount_diff,general_management_sum,finance_sum,other_sum = self.get_all_expense(cr, uid, date_start, date_stop, loc_ids, where, context=ctx)
            for pid in product_obj.browse(cr, uid, product_ids):                
                fetched = self.get_product_all_sales(cr, uid, [pid.id], loc_ids, date_start, date_stop, where, context=context)
                income = 0.0
                cost = 0.0
                discount = 0.0
                refund_income = 0.0
                refund_cost = 0.0
                refund_discount = 0.0
                diff_cost = 0.0       
                act = 0.0
                marketing = 0.0
                sale_expense = 0.0
                s_discount = 0.0
                sale_managment = 0.0
                general_expense = 0.0
                finance_expense = 0.0
                other_expense = 0.0
                diff = 0.0
                for i in fetched:
                    income += i['s']
                    cost += i['c']
                    discount += i['d']
                    refund_income += i['refund_s']
                    refund_cost += i['refund_c']
                    refund_discount += i['refund_d']                    

                ''' 
                Өгөгдөл зурах хэсэг
                '''
                row = []            
                row += ['<str><c>%s</c></str>' % (number)]
                prods = dict([(x['id'], x) for x in product_obj.read(cr, uid, [pid.id], 
                                            ['name','default_code'], context=context)])

                for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):                            
                    row += [u'<space/><space/>[%s] %s'%((prod['default_code'] or ''),(prod['name'] or ''))]

                income = (income - refund_income)/1.1
                sum1 += income
                discount = (discount - refund_discount)/1.1
                sum2 += discount
                row += [income]
                if pid.id in cost_product_id:
                    if cost_diff_sum != 0.0 and cost_diff != 0.0:
                        diff_cost = (income / cost_diff_sum) * cost_diff
                        if diff_cost < 0.0:
                            diff_cost *= -1
                        sum3 += diff_cost
                        row += [diff_cost]
                    else:
                        row += [0.0]
                else:
                    row += [0.0]
                row += [cost - refund_cost]
                sum4 += (cost-refund_cost)
                row += [discount]
                if sale_discount != 0.0 and sale_income != 0.0:
                    diff = (income / sale_income) * sale_discount
                    if diff < 0.0:
                        diff *= -1
                    sum5 += diff
                    row += [diff]
                else:
                    row += [0.0]
                if pid.id in act_product_id:
                    if act_expense != 0.0 and act_product_sum != 0.0:
                        act = (income / act_product_sum) * act_expense
                        if act < 0.0:
                            act *= -1
                        sum6 += act
                        row += [act]
                    else:
                        row += [0.0]
                else:
                    row += [0.0]
                if pid.categ_id.parent_id:                    
                    root_categ_id = self.get_root_categ(cr, uid, pid.categ_id.id, context=context)                    
                    if root_categ_id in categ_list:
                        cr.execute("select analytic_id from product_category where id = '"+str(root_categ_id)+"'")
                        analycic_id = cr.fetchone()
                        marketing = (income / categ_list[root_categ_id]['income']) * marketing_list[analycic_id[0]]['sum']
                        if marketing < 0.0:
                            marketing *= -1                       
                        sum7 += marketing
                        row += [marketing]          
                    else:
                        row += [0.0]                                    
                else:                    
                    row += [0.0]
                if sale_expense_sum != 0.0 and sale_income != 0.0:
                    sale_expense = (income / sale_income) * sale_expense_sum
                    if sale_expense < 0.0:
                        sale_expense *= -1
                    sum8 += sale_expense
                    row += [sale_expense]
                else:
                    row += [0.0]
                if sale_management_sum != 0.0:
                    if pid.categ_id.id in sale_management_categs:
                        root_categ_id = self.get_root_categ(cr, uid, pid.categ_id.id, context=context)
                        discount = self.pool.get('product.category').browse(cr, uid, root_categ_id).sale_discount
                        s_discount = (income/100)*discount
                        if s_discount < 0.0:
                            s_discount *= -1
                        sum9 += s_discount
                        row += [s_discount]
                    else:                    
                        if sale_income_diff != sale_income and sale_discount_diff != sale_management_sum:
                            sale_managment = (income / sale_income_diff) * sale_discount_diff
                            if sale_managment < 0.0:
                                sale_managment *= -1
                            sum9 += sale_managment
                            row += [sale_managment]
                        else:
                            row += [0.0]                    
                else:
                    row += [0.0]
                if general_management_sum != 0.0 and sale_income != 0.0:
                    general_expense = (income / sale_income) * general_management_sum
                    if general_expense < 0.0:
                        general_expense *= -1
                    sum10 += general_expense
                    row += [general_expense]
                else:
                    row += [0.0]
                if finance_sum != 0.0 and sale_income != 0.0:
                    finance_expense = (income / sale_income) * finance_sum
                    if finance_expense < 0.0:
                        finance_expense *= -1
                    sum11 += finance_expense
                    row += [finance_expense]
                else:
                    row += [0.0]
                if other_sum != 0.0 and sale_income != 0.0:
                    other_expense = (income / sale_income) * other_sum
                    if other_expense < 0.0:
                        other_expense *= -1
                    sum12 += other_expense
                    row += [other_expense]
                else:
                    row += [0.0]
                all_expense = act + marketing + sale_expense + s_discount + sale_managment + general_expense + finance_expense + other_expense
                sum13 += all_expense
                row += [all_expense]
                # all_profit = income - (cost - refund_cost + diff_cost) - all_expense
                all_profit = income - (cost - refund_cost + diff_cost) - (discount + diff) 
                sum14 += all_profit
                row += [all_profit]
                profit = all_profit - all_expense
                sum15 += profit
                row += [profit]
                row += ['']

                data.append(row)
                number += 1

            row = ['', u'<b><c>НИЙТ</c></b>','<b>%s</b>'%sum1,'<b>%s</b>'%sum2,'<b>%s</b>'%sum3,'<b>%s</b>'%sum4,'<b>%s</b>'%sum5,'<b>%s</b>'%sum6,'<b>%s</b>'%sum7,'<b>%s</b>'%sum8,'<b>%s</b>'%sum9,'<b>%s</b>'%sum10,'<b>%s</b>'%sum11,'<b>%s</b>'%sum12,'<b>%s</b>'%sum13,'<b>%s</b>'%sum14,'<b>%s</b>'%sum15,'']
            data.append(row)
        if wiz['type'] == 'summary':
            count = 0                   
            for i in range(per_from,per_to+1):
                date_start = str(year) + "-"+str(i) + "-01"
                date_stop = str(self.last_day_of_month(datetime.date(year, i, 1)))
                ctx = context.copy() 
                ctx['date_from'] = date_start
                ctx['date_to'] =  date_stop
                cost_product_id,cost_diff_sum,cost_diff,sale_discount,sale_income,act_product_id,act_expense,act_product_sum,categ_list,marketing_list,sale_expense_sum,sale_management_categs,sale_management_sum,sale_income_diff,sale_discount_diff,general_management_sum,finance_sum,other_sum = self.get_all_expense(cr, uid, date_start, date_stop, loc_ids, where, context=ctx)                                                
                index = 0
                sum1 = 0.0
                for pid in product_obj.browse(cr, uid, product_ids):
                    fetched = self.get_product_all_sales(cr, uid, [pid.id], loc_ids, date_start, date_stop, where, context=context)
                    '''
                    Өгөгдөл зурах хэсэг
                    '''                    
                    row = []
                    row += ['<str><c>%s</c></str>' % (number)]
                    prods = dict([(x['id'], x) for x in product_obj.read(cr, uid, [pid.id], 
                                                ['ean13','name','default_code','uom_id','standard_price'], context=context)]) 
                    for prod in sorted(prods.values(), key=itemgetter(wiz['sorting'])):
                        row += [u'<space/><space/>[%s] %s'%((prod['default_code'] or ''),(prod['name'] or ''))]
                    income = 0.0
                    cost = 0.0
                    discount = 0.0
                    refund_income = 0.0
                    refund_cost = 0.0
                    refund_discount = 0.0
                    diff_cost = 0.0       
                    act = 0.0
                    marketing = 0.0
                    sale_expense = 0.0
                    s_discount = 0.0
                    sale_managment = 0.0
                    general_expense = 0.0
                    finance_expense = 0.0
                    other_expense = 0.0
                    diff = 0.0
                    for i in fetched:
                        income += i['s']
                        cost += i['c']
                        discount += i['d']
                        refund_income += i['refund_s']
                        refund_cost += i['refund_c']
                        refund_discount += i['refund_d']                  
                    income = (income - refund_income)/1.1
                    discount = (discount - refund_discount)/1.1                    
                    if pid.id in cost_product_id:
                        if cost_diff_sum != 0.0 and cost_diff != 0.0:
                            diff_cost = (income / cost_diff_sum) * cost_diff
                            if diff_cost < 0.0:
                                diff_cost *= -1                                        
                    if sale_discount != 0.0 and sale_income != 0.0:
                        diff = (income / sale_income) * sale_discount
                        if diff < 0.0:
                            diff *= -1                        
                    if pid.id in act_product_id:
                        if act_expense != 0.0 and act_product_sum != 0.0:
                            act = (income / act_product_sum) * act_expense
                            if act < 0.0:
                                act *= -1                            
                    if pid.categ_id.parent_id:                    
                        root_categ_id = self.get_root_categ(cr, uid, pid.categ_id.id, context=context)                    
                        if root_categ_id in categ_list:
                            cr.execute("select analytic_id from product_category where id = '"+str(root_categ_id)+"'")
                            analycic_id = cr.fetchone()
                            marketing = (income / categ_list[root_categ_id]['income']) * marketing_list[analycic_id[0]]['sum']
                            if marketing < 0.0:
                                marketing *= -1                                                   
                    if sale_expense_sum != 0.0 and sale_income != 0.0:
                        sale_expense = (income / sale_income) * sale_expense_sum
                        if sale_expense < 0.0:
                            sale_expense *= -1                        
                    if sale_management_sum != 0.0:
                        if pid.categ_id.id in sale_management_categs:
                            root_categ_id = self.get_root_categ(cr, uid, pid.categ_id.id, context=context)
                            discount = self.pool.get('product.category').browse(cr, uid, root_categ_id).sale_discount
                            s_discount = (income/100)*discount
                            if s_discount < 0.0:
                                s_discount *= -1                        
                        else:
                            if sale_income_diff != sale_income and sale_discount_diff != sale_management_sum:
                                sale_managment = (income / sale_income_diff) * sale_discount_diff
                                if sale_managment < 0.0:
                                    sale_managment *= -1                            
                    if general_management_sum != 0.0 and sale_income != 0.0:
                        general_expense = (income / sale_income) * general_management_sum
                        if general_expense < 0.0:
                            general_expense *= -1                        
                    if finance_sum != 0.0 and sale_income != 0.0:
                        finance_expense = (income / sale_income) * finance_sum
                        if finance_expense < 0.0:
                            finance_expense *= -1                        
                    if other_sum != 0.0 and sale_income != 0.0:
                        other_expense = (income / sale_income) * other_sum
                        if other_expense < 0.0:
                            other_expense *= -1                        
                    all_expense = act + marketing + sale_expense + s_discount + sale_managment + general_expense + finance_expense + other_expense                    
                    # all_profit = income - (cost - refund_cost + diff_cost) - all_expense
                    all_profit = income - (cost - refund_cost + diff_cost) - (discount + diff)
                    profit = all_profit - all_expense
                    row += [profit]
                    sum1 += profit
                    number += 1
                    if count != 0: 
                        data[index].append(profit)
                        index += 1
                    else:
                        data.append(row)
                col_sum += [sum1]                
                count += 1
            row = ['', u'<b><c>НИЙТ</c></b>']
            for i in col_sum:
                row += ['<b>%s</b>'%i]
            data.append(row)
        if wiz['type'] == 'branch':
            sale_team_ids = self.pool.get('crm.case.section').search(cr, uid, [])
            if wiz['team_ids']:
                sale_team_ids = wiz['team_ids']

            profit_config_obj = self.pool.get('product.profit.report.config').browse(cr, uid, [1])            
            sale_team = {}    

            for account in profit_config_obj.sale_team_account_ids:
                sale_team[account.id] = {'analytic': {}}
                for analytic in profit_config_obj.sale_team_analytic_ids:
                    cr.execute("select sum(debit) from account_move_line where account_id = '"+str(account.id)+"' and date_created >= '"+str(date_start)+"' and date_created <= '"+str(date_stop)+"' and analytic_account_id = '"+str(analytic.id)+"'")
                    analytic_sum = cr.fetchone()
                    if analytic_sum != [] and analytic_sum != None:
                        sale_team[account.id]['analytic'][analytic.id] = {'sum': analytic_sum[0]}
                    else:
                        sale_team[account.id]['analytic'][analytic.id] = {'sum': 0.0}

            for account in profit_config_obj.sale_team_account_ids:
                row = []
                row += ['<str><c>%s</c></str>' % (number)]                
                row += [u'<space/><space/>[%s] %s'%((account.code or ''),(account.name or ''))]
                for team in self.pool.get('crm.case.section').browse(cr, uid, sale_team_ids):
                    if team.analytic_id.id in sale_team[account.id]['analytic']:
                        if sale_team[account.id]['analytic'][team.analytic_id.id]['sum'] != None:
                            row += [sale_team[account.id]['analytic'][team.analytic_id.id]['sum']]
                        else:
                            row += [0.0]
                    else:
                        row += [0.0]
                data.append(row)
                number += 1
                            

        return data, titles, row_span



