# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-2014 Monos Group (<http://monos.mn>).
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


from StringIO import StringIO
from openerp.tools.translate import _
from xlwt import *
import datetime
from openerp import netsvc
import base64, os
import time
import logging
import traceback, sys
from tempfile import NamedTemporaryFile
from lxml import etree
from dateutil.relativedelta import relativedelta
from types import ListType
import xmlrpclib
import xlsxwriter

from odoo import  fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class ReplicatedRPCProxyOne(object):
    def __init__(self, server, ressource):
        self.server = server
        local_url = 'http://%s:%d/xmlrpc/common' % (server.server_url,)
        rpc = xmlrpclib.ServerProxy(local_url)
        self.uid = rpc.login(server.server_db, server.login, server.password)
        local_url = 'http://%s:%d/xmlrpc/object' % (server.server_url,)
        self.rpc = xmlrpclib.ServerProxy(local_url)
        self.ressource = ressource
    def __getattr__(self, name):
        return lambda cr, uid, *args, **kwargs: self.rpc.execute(self.server.server_db, self.uid, self.server.password, self.ressource, name, *args)

class ReplicatedRPCProxy(object):
    def __init__(self, server):
        self.server = server
    def get(self, ressource):
        return ReplicatedRPCProxyOne(self.server, ressource)

_logger = logging.getLogger('abstract.report.model')


class report_mirror_server(models.TransientModel):
    _name = "report.mirror.server"
    _description = "Report Mirror Server"

    name = fields.Char('Server name', size=64, required=True)
    server_url = fields.Char('Server URL', size=64, required=True)
    server_db = fields.Char('Server Database', size=64, required=True)
    login = fields.Char('User Name', size=50, required=True)
    password = fields.Char('Password', size=64, required=True)
    active = fields.Boolean('Active')

    
    _defaults = {
        'server_url': 'localhost:8069'
    }
report_mirror_server()

class ReportExcelOutput(models.TransientModel):
    _name = 'report.excel.output'
    _description = "Excel Report Output"

    name=fields.Char('Filename', readonly=True)
    data=fields.Binary('File', readonly=True, required=True)

    
    def get_default_data(self, cr, uid, context=None):
        if context is None:
            context = {}
        temp_file_name = context.get('report_output_temporary', False)
        output = False
        if temp_file_name:
            temp_file = open(temp_file_name)
            buffer = StringIO(temp_file.read())
            buffer.seek(0)
            output = base64.encodestring(buffer.getvalue())
            temp_file.close()
            buffer.close()
            # os.unlink(temp_file_name)
            
        return output
    
    def get_default_name(self, cr, uid, context=None):
        if context.get('report_output_filename', False):
            return context['report_output_filename']
        return 'report_output.tmp'
    
    _defaults = {
        'data': get_default_data,
        'name': get_default_name
    }
class Abstract_Report_Model(models.Model):
    _name = 'abstract.report.model'
    _description = 'Abstract Report Model'

    save = fields.Boolean('Save to document storage')

    
    def get_report_code(self):
        ''' Unimplemented method.
        '''
        return False, False
    
    def get_log_message(self):
        return u"Unimplemented log"
    
    def create_log_message(self, report_type, automatic=False):
        logging_obj = self.env['abstract.report.logging']
        model_ids = self.env['ir.model'].search([('model', '=', self._name[0])])
        if not model_ids:
            return False
        body = self.get_log_message()
        log_id = logging_obj.create({
            'report_model': model_ids[0],
            'name': body,
            'type': report_type,
            'automatic': automatic
        })
        message = u"[Тайлан][%s][PROCESSING] %s" % (report_type, body)
        uname = self.pool.get('res.users').read(['name'])['name'] or ''
        message += u", (Хэрэглэгч='%s', uid=%s)" % (uname, self.env.uid)
        _logger.info(message)
        return log_id
    
    def get_replicated_service_datas(self, cr, uid, service_name, datas, method, params, context=None):
        if context is None:
            context = {}
        synchro_obj = self.env['report.mirror.server']
        server_ids = synchro_obj.search(cr, uid, [], context=context)
        if server_ids:
            server = synchro_obj.browse(cr, uid, server_ids[0], context=context)
            replicated_pool = ReplicatedRPCProxy(server)
            if params:
                params = (uid,) + params
            result = replicated_pool.get('abstract.report.model').redirect_replicated_service(cr,
                        uid, service_name, datas, method, params, context)
            evaled_result = eval(result['safe_result'])
            if result.get('error_message', False):
                if context.get('log_id', False):
                    self.pool.get('abstract.report.logging').exception(cr, uid, [context['log_id']], context=context)
                error_message = traceback.format_exc()
                raise Exception(result['error_message'])
            return evaled_result
        else :
            service = netsvc.LocalService(service_name)
            service.cr = cr
            service.uid = uid
            service.datas = datas
            service.context = context
            service.pool = self.pool
            service.lang = context.get('lang', False)
            if params:
                params = (cr, uid) + params
            result = getattr(service, method)(*params)
            
            return result
    
    def force_make_attachment(self, cr, uid, datas, directory_name,
            attache_name, context=None):
        ''' Excel тайланг шууд баримтын серверт хадгална.
        '''
        if context is None:
            context = {}
        if attache_name:
            aname = "%s_%s.xls" % (attache_name, time.strftime('%Y%m%d_%H%M'))
        else :
            aname = '%s_%s.xls' % (self._name.replace('.', '_'), time.strftime('%Y%m%d%H%M%S'))
        directory = False
        if directory_name:
            directory_ids = self.pool.get('document.directory').search(cr, 1,
                        [('name', '=', directory_name)], context=context)
            if directory_ids :
                directory = directory_ids[0]
        try:
            model_name = self._name
            res_id = False
            if 'generator_id' in context:
                model_name = 'report.schedule.generator'
                res_id = context['generator_id']
            document_name = context.get('force_document_name', context.get('attache_name', aname))
            self.pool.get('ir.attachment').create(cr, uid, {
                'name': document_name + ' [%s]' % time.strftime('%Y%m%d%H%M%S'),
                'datas': datas,
                'datas_fname': aname,
                'res_model': model_name,
                'res_id': res_id,
                'parent_id': directory
                }, context=context)
            if context.get('other_users', []):
                for uid2 in context['other_users']:
                    self.pool.get('ir.attachment').create(cr, uid2, {
                        'name': document_name + ' [%s]' % time.strftime('%Y%m%d%H%M%S'),
                        'datas': datas,
                        'datas_fname': aname,
                        'res_model': model_name,
                        'res_id': res_id,
                        'parent_id': directory
                    }, context=context)
        except Exception:
            # TODO: should probably raise a proper osv_except instead, shouldn't we? see LP bug #325632
            logging.getLogger('report').error('Could not create saved report attachment', exc_info=True)
        return aname
    
    def export_report(self):
        context = self._context or {}
        
        if 'generator_id' in context:
            log_id = self.create_log_message(report_type='XLS', automatic=True)
        else :
            log_id = self.create_log_message(report_type='XLS', automatic=False)
        user = self.env['res.users'].browse()
        
        report_code, directory_name = self.get_report_code()
        attache_name = report_code and report_code.replace('.', '_') or False
        
        d1 = datetime.datetime.now()
        res = self.get_export_data(report_code)
        if 'data' in res:
            book = res['data']  # Workbook object instance.
            buffer = StringIO()
            book.save(buffer)
        else :  # Generic excel builder
            datas = res['datas']
            title = datas.get('title', 'Generic Report')
            subtitle = datas.get('subtital', '')
            headers = datas.get('headers', [])
            header_span = datas.get('header_span', [])
            titles = datas.get('titles', [])
            footers = datas.get('footers', [])
            rows = datas.get('rows', [])
            row_span = datas.get('row_span', {})
            widths = datas.get('widths', [])
            orientation = datas.get('orientation', [])
            header_font_size = datas.get('header_font_size', 9)
            footer_font_size = datas.get('footer_font_size', 7)
            font_size_offset = datas.get('font_size_offset', 7)
            row_height=datas.get('row_height',20)
            margin= datas.get('margin',1.3)
            buffer = StringIO()
                
            book = xlsxwriter.Workbook(buffer)
            sheet = book.add_worksheet(title[:25])
            sheet.set_margins(top=margin, left=margin ,right=margin)
            if orientation and orientation == 'landscape':
                sheet.set_landscape()
            title_xf = book.add_format({'align':'left', 'bold':True, 'font_size':14})
            footer_xf = book.add_format({'align':'left', 'bold':True, 'font_size':footer_font_size})
            small_title_xf = book.add_format({'align':'left', 'bold':True, 'font_size':9})
            heading_xf = book.add_format({'align':'center', 'bold':True, 'font_size':header_font_size, 'border':1, 'pattern':1, 'bg_color':'#50fffc', 'text_wrap':1})
            
            rowx = 0
            if subtitle:
                sheet.write(rowx, 1, subtitle, small_title_xf)
                rowx += 1
            sheet.write(rowx, 1, u'Байгууллагын нэр: %s' % (user.company_id.name,), small_title_xf)
            rowx += 1
            sheet.write(rowx, 1, title, title_xf)
            sheet.set_row(rowx, 35)
            rowx += 1
            
            for title in titles:
                sheet.write(rowx, 1, title, small_title_xf)
                sheet.set_row(rowx, 20)
                rowx += 1
            
            sheet.write(rowx, 1, u'%s: %s' % (_('Date'), time.strftime('%Y-%m-%d'),), small_title_xf)
            
            rowx += 3
            fixed = rowx
            ix = 0
            banned = []
            for tr in headers:
                iy = 0
                colx = 0
                for hr in tr:
                    if hr is None:
                        colx += 1
                        iy += 1
                        continue
                    tobespan = filter(lambda tup: tup[0][1] == ix and tup[0][0] == iy, header_span)
                    if tobespan:
                        tobespan = tobespan[0]
                        rowincrement = tobespan[1][1] - tobespan[0][1]
                        colincrement = tobespan[1][0] - tobespan[0][0]
                        sheet.merge_range(rowx, colx, rowx + rowincrement, colx + colincrement, hr, heading_xf)
                    else:
                        sheet.write(rowx, colx, hr, heading_xf)
                    colx += 1
                    iy += 1
                ix += 1
                rowx += 1
            
            for x in range(fixed, rowx):
                sheet.set_row(x, row_height)
            
            
            if datas.get('freeze', False):
                sheet.freeze_panes(rowx, 0)
            
            style_store = {}
            ix = 0
            for tr in rows:
                colx = 0
                iy = 0
                if row_span.has_key(ix):
                    tobespan = row_span[ix]
                else:
                    tobespan = False
                for td in tr:
                    if td is None:
                        colx += 1
                        iy += 1
                        continue
                    _style = {'font_size':font_size_offset, 'border':1}
                    setlevel = False
                    if type(td) in (unicode, str):
                        str_td = u'%s' % td
                        if '<b>' in str_td:
                            _style['bold'] = True
                            td = td.replace('<b>', '').replace('</b>', '')
                        if '<c>' in str_td:
                            _style['align'] = 'center'
                            td = td.replace('<c>', '').replace('</c>', '')
                        if '<center>' in str_td:
                            _style['align'] = 'center'
                            td = td.replace('<center>', '').replace('</center>', '')
                        if '<color>' in str_td:
                            _style['pattern'] = 1
                            _style['bg_color'] = '#8FBC8F'
                            td = td.replace('<color>', '').replace('</color>', '')
                        if '<gold>' in str_td:
                            _style['pattern'] = 1
                            _style['bg_color'] = '#FF7F50'
                            td = td.replace('<gold>', '').replace('</gold>', '')
                        if '<wrap>' in str_td:
                            _style['text_wrap'] = True
                            td = td.replace('<wrap>', '').replace('</wrap>', '')
                        if '<percent/>' in str_td:
                            td = td.replace('<percent/>', '')
                            _style['num_format'] = '0.00%'
                        if '<str>' in str_td:
                            _style['align'] = 'left'
                            td = td.replace('<str>', '').replace('</str>', '')
                        if '<right>' in str_td:
                            _style['align'] = 'right'
                            td = td.replace('<right>', '').replace('</right>', '')
                        if '<formula>' in str_td:
                            _style['num_format'] = '#,##0.00'
                            _style['align'] = 'right'
                            td = td.replace('<formula>', '').replace('</formula>', '')
                            td = Formula(td)
                        if '<str>' not in str_td:
                            try:
                                td = float(td)
                            except :
                                pass
                         
                        if type(td) in (int, long, float):
                            _style['num_format'] = '#,##0.00'
                            _style['align'] = 'right'
                            _style['text_wrap'] = False
                        elif not _style :
                            _style['align'] = 'left'
                            _style['text_wrap'] = True
                        if '<head>' in str_td:
                            _style['bold'] = True
                            _style['font_size'] = 10
                            _style['text_wrap'] = True
                            _style['pattern'] = 1
                            _style['bg_color'] = '#FF7F50'
                            td = td.replace('<head>', '').replace('</head>', '')
                        if '<space/>' in str_td:
                            td = td.replace('<space/>', '  ')
                         
                        if '<level1/>' in str_td:
                            td = td.replace('<level1/>', '')
                            setlevel = 1
                        if '<level2/>' in str_td:
                            td = td.replace('<level2/>', '')
                            setlevel = 2
                        if '<level3/>' in str_td:
                            td = td.replace('<level3/>', '')
                            setlevel = 3
                        if '<level4/>' in str_td:
                            td = td.replace('<level4/>', '')
                            setlevel = 4
                     
                    elif type(td) is Formula or type(td) in (type(1), type(1.1)):
                        _style['num_format'] = '#,##0.00'
                        _style['align'] = 'right'
                        _style['text_wrap'] = False
                    else :
                        _style['align'] = 'left'
                        _style['text_wrap'] = 1
                    # тайлангийн дунд хэсэгт хүснэгтийн толгой гаргах
                     
                    _style_key = _style.__repr__()
                    if _style_key in style_store:
                        _style = style_store[_style_key]
                    else:
                        _style = book.add_format(_style)
                        style_store[_style_key] = _style
                    if tobespan:
                        tobespan1 = filter(lambda tup: tup[0] == iy, tobespan)
                        if tobespan1:
                            tobespan1 = tobespan1[0]
                            if len(tobespan1) == 3:
                                rowincrement = tobespan1[2] - ix
                            else: rowincrement = 0
                            colincrement = tobespan1[1] - tobespan1[0]
                            sheet.merge_range(rowx, colx, rowx + rowincrement, colx + colincrement, td, _style)
                    sheet.write(rowx, colx, td, _style)
                    if setlevel:
                        sheet.set_row(rowx, None, None, {'level':setlevel})
                    colx += 1
                    iy += 1
                ix += 1
                rowx += 1
            inch = 3
            colx = 0
            for w in widths:
                sheet.set_column(colx, colx, w * inch)
                colx += 1
            i=0
            rowx += 1
            if footers:
                while i < len(footers):
                    rowx += 1
                    sheet.write(rowx, 1, footers[i], footer_xf)
                    if len(footers) > i + 1:
                        sheet.write(rowx, 4, footers[i + 1], footer_xf)
                    i += 2
            else:
                rowx += 1
                sheet.write(rowx, 1, _('Executive Director .................................. (                                   )'), footer_xf)
                sheet.write(rowx + 2, 1, _('General Accountant .................................. (                                   )'), footer_xf)
            
            book.close()
            
        buffer.seek(0)
        buffer_value = buffer.getvalue()
        buffer.close()
        
        out = base64.b64encode(buffer_value)
        # Force save if needed.
        if res.get('force_save', False) == True :
            log_name = self.pool.get('abstract.report.logging').read(log_id, ['name'])['name']
            context.update({'force_document_name': log_name[:128]})
            filename = self.force_make_attachment(out, directory_name or 'default',
                        attache_name)
            if 'xlsx' in res or 'data' not in res:
                filename += 'x'  # Office 2007
        else :
            filename = self._name.replace('.', '_')
            filename = "%s_%s.xls" % (filename, time.strftime('%Y%m%d_%H%M'),)
            if 'xlsx' in res or 'data' not in res:
                filename += 'x'  # Office 2007
        
        tempf = NamedTemporaryFile(prefix="openerp.report.output.", delete=False)
        tempf.write(buffer_value)
        tempf.close()
        
        excel_id = self.env['report.excel.output'].create({
                                'data':out,
                                'name':filename
        })
        
        mod_obj = self.env['ir.model.data']
        form_res = mod_obj.get_object_reference('l10n_mn_report_base_2', 'action_excel_output_view')
        form_id = form_res and form_res[1] or False
        logging = self.env['abstract.report.logging'].browse(log_id)
        # logging.done()
        # context.update({'report_output_temporary': tempf.name, 'report_output_filename':filename})
        return {
            'name': _('Export Result'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.excel.output',
            'view_id': False,
            'views': [(form_id, 'form')],
            'res_id': excel_id.id,
            'context': context,
            'type': 'ir.actions.act_window',
            'target':'new',
            'nodestroy': True,
        }
    
    def print_report(self, cr, uid, ids, context=None):
        ''' Use Replicated Server resources if needed.
        '''
        context = context or {}
        data = self.get_print_data(cr, uid, ids, context=context)
        log_id = self.create_log_message(cr, uid, ids, report_type='PDF', automatic=False, context=context)
        if 'datas' in data:
            data['datas']['log_id'] = log_id
        else:
            data['data']['log_id'] = log_id
        context = data.get('context', context)
        context.update({'redirect_replicated_server':True})
        data.update({'context':context})
#         report_code, dir_name = self.get_report_code(cr, uid, ids, context=context)
#         if report_code:
#             data['datas'].update({'report_code':report_code})
#         if dir_name:
#             data['datas'].update({'directory_name':dir_name})
        return data
    
    def get_print_data(self, cr, uid, ids, context=None):
        raise UserError(_('Programming Error!'), _('Unimplemented method.'))
    
    def get_export_data(self, report_name):
        raise UserError(_('Programming Error!'), _('Unimplemented method.'))
    
    def mirror_prepare_report_data(self, cr, uid, wiz, model, context=None):
        if context is None:
            context = {}
        synchro_obj = self.pool.get('report.mirror.server')
        server_ids = synchro_obj.search(cr, uid, [], context=context)
        if server_ids:
            server = synchro_obj.browse(cr, uid, server_ids[0], context=context)
            replicated_pool = ReplicatedRPCProxy(server)
            result = replicated_pool.get('abstract.report.model').redirect_replicated_method(cr,
                        uid, model, 'prepare_report_data', (uid, wiz, context), context)
        else :
            result = self.redirect_replicated_method(cr, uid, model, 'prepare_report_data', (uid, wiz, context), context)
        evaled_result = eval(result['safe_result'])
        if result.get('error_message', False):
            # if context.get('log_id', False):
            #    self.pool.get('abstract.report.logging').exception(cr, uid, [context['log_id']], context=context)
            error_message = traceback.format_exc()
            raise Exception(result['error_message'])
        
        return evaled_result
    
    def redirect_replicated_method(self, cr, uid, model_name, method, params, context=None):
        ''' Тайлангийн серверийн LocalService обьектод хандаж
            холбогдох report service -ын тайлангийн өгөгдөл боловсруулах
            method -г дуудаж ажиллуулна. үр дүнг төв сервер лүү буцаана.
        '''
        if context is None:
            context = {}
        try:
            res = getattr(self.pool.get(model_name), method)(cr, *tuple(params))
        except Exception, e:
            _logger.error(traceback.print_exc())
            return {'safe_result': '{}', 'error_message':sys.exc_info()}
        return {'safe_result': res.__repr__()}
    
    def redirect_replicated_service(self, cr, uid, service_name, datas, method, params, context):
        ''' Тайлангийн серверийн LocalService обьектод хандаж
            холбогдох report service -ын тайлангийн өгөгдөл боловсруулах
            method -г дуудаж ажиллуулна. үр дүнг төв сервер лүү буцаана.
        '''
        if context is None:
            context = {}
        service = netsvc.LocalService(service_name)
        service.cr = cr
        service.uid = uid
        service.datas = datas
        service.context = context
        service.pool = self.pool
        service.lang = context.get('lang', False)
        try:
            res = getattr(service, method)(cr, *tuple(params))
        except Exception, e:
            error_message = traceback.format_exc()
            _logger.error(error_message)
            return {'safe_result': '{}', 'error_message':error_message}
            
        return {'safe_result': res.__repr__()}
    
Abstract_Report_Model()

def update_date(dd, k, new):
    if k == 'start':
        if 'date_start' in dd:
            dd['date_start'] = new
        elif 'date_from' in dd:
            dd['date_from'] = new
        elif 'start_date' in dd:
            dd['start_date'] = new
        elif 'from_date' in dd:
            dd['from_date'] = new
        else:
            dd['date'] = new
    else :
        if 'date_stop' in dd:
            dd['date_stop'] = new
        elif 'date_to' in dd:
            dd['date_to'] = new
        elif 'stop_date' in dd:
            dd['stop_date'] = new
        elif 'to_date' in dd:
            dd['to_date'] = new
        else:
            dd['date'] = new

def get_period(dd):
    if 'period_stop' in dd:
        return dd['period_stop']
    elif 'period_to' in dd:
        return dd['period_to']
    elif 'stop_period' in dd:
        return dd['stop_period']
    elif 'to_period' in dd:
        return dd['to_period']

def get_date(dd):
    if 'date_stop' in dd:
        return dd['date_stop']
    elif 'date_to' in dd:
        return dd['date_to']
    elif 'stop_date' in dd:
        return dd['stop_date']
    elif 'to_date' in dd:
        return dd['to_date']
    else:
        return dd['date']
    return False

def update_period(dd, k, new):
    if k == 'start':
        if 'period_start' in dd:
            dd['period_start'] = new
        elif 'period_from' in dd:
            dd['period_from'] = new
        elif 'start_period' in dd:
            dd['start_period'] = new
        elif 'from_period' in dd:
            dd['from_period'] = new
    else :
        if 'period_stop' in dd:
            dd['period_stop'] = new
        elif 'period_to' in dd:
            dd['period_to'] = new
        elif 'stop_period' in dd:
            dd['stop_period'] = new
        elif 'to_period' in dd:
            dd['to_period'] = new

def get_check_report_name(report_name):
    res = {'report_name': report_name,
           'expense': False,
           'income': False}
    if report_name == 'report.product.ledger.expense':
        res['report_name'] = 'report.product.ledger'
        res['expense'] = True
    elif report_name == 'report.product.ledger.income':
        res['report_name'] = 'report.product.ledger'
        res['income'] = True
    else:
        res['report_name'] = report_name
    return res

class abstract_report_logging(models.Model):
    _name = 'abstract.report.logging'
    _description = 'Report Loader Logging'
    _order = 'date_start desc'

    name = fields.Char('Log message', size=256, required=True)
    date_start = fields.Datetime('Start Time', required=True)
    date_stop = fields.Datetime('End Time', required=True)
    report_model = fields.Many2one('ir.model', 'Report Model', required=True, select=True)
    state = fields.Selection([('running', 'Running'), ('done', 'Success'), ('error', 'Error Occured')], 'Status', required=True)
    user_id = fields.Many2one('res.users', 'User', required=True, select=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, select=True)
    type = fields.Selection([('XLS', 'Excel Report'), ('PDF', 'PDF Report')], 'Report Format')
    automatic = fields.Boolean('Automatic Report?')
    duration = fields.Char('Duration', size=32)

    
    _defaults = {
        'user_id': lambda obj, cr, uid, c:uid,
        'state': 'running',
        'company_id': lambda obj, cr, uid, c:obj.pool.get('res.company')._company_default_get(cr, uid, 'abstract.report.logging', context=c),
        'date_start': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_stop': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': '--'
    }
    
    def done(self):
        log = self

        stop_date = datetime.datetime.now()
        dta = stop_date - datetime.datetime.strptime(log.date_start, '%Y-%m-%d %H:%M:%S')
        if dta.seconds > 60 :
            tm = '%sm %ss' % (dta.seconds / 60, dta.seconds % 60)
        else :
            tm = '%ss' % dta.seconds
        if log.automatic:
            prefix = u"[Автомат тайлан][%s][COMPLETE (%s)]" % (log.type, tm)
        else :
            prefix = u"[Тайлан][%s][COMPLETE (%s)]" % (log.type, tm)
        message = u"%s %s" % (prefix, log.name)
        self.write({'state':'done',
                                  'date_stop':stop_date.strftime('%Y-%m-%d %H:%M:%S'),
                                  'duration': tm})
        _logger.info(message)
        return log.name
    
    def exception(self, cr, uid, ids, context=None):
        log = self.browse(cr, uid, ids[0], context=context)
        stop_date = datetime.datetime.now()
        dta = stop_date - datetime.datetime.strptime(log.date_start, '%Y-%m-%d %H:%M:%S')
        if dta.seconds > 60 :
            tm = '%sm %ss' % (dta.seconds / 60, dta.seconds % 60)
        else :
            tm = '%ss' % dta.seconds
        if log.automatic:
            prefix = u"[Автомат тайлан][%s][ERROR (%s)]" % (log.type, tm)
        else :
            prefix = u"[Тайлан][%s][ERROR (%s)]" % (log.type, tm)
        message = u"%s %s" % (prefix, log.name)
        self.write(cr, uid, ids, {'state':'error',
                                  'date_stop':stop_date.strftime('%Y-%m-%d %H:%M:%S'),
                                  'duration': tm})
        _logger.info(message)
        return True
    
abstract_report_logging()

class report_schedule_generator(models.Model):
    _name = 'report.schedule.generator'
    _description = 'Report Schedule Generator'
    
    REPORT_SELECTION = [
        ('stock.level.info.pdf', u'Агуулахын нөөцийн мэдээлэл'),
        ('report.pos.stock.level.info', u'Агуулахын нөөцийн мэдээлэл /Пос ар тал/'),
        ('report.move.by_cip', u'Барааны хөдөлгөөний тайлан (Cip үнээр)'),
        ('report.move.by_price', u'Барааны хөдөлгөөний тайлан (Худалдах үнээр)'),
        ('report.move.by_supplier', u'Барааны хөдөлгөөний тайлан (Нийлүүлэгчээр)'),
        ('product.compare', u'Барааны харицуулалт хийсэн тайлан'),
        ('report.expiring.products', u'Бараа материалын дуусах хугацааны тайлан'),
        ('report.stock.two', u'Барааны нөөцийн тайлан 2'),
        ('report.product.ledger', u'Бараа материалын товчоо тайлан'),
        ('report.product.ledger.expense', u'Бараа материалын зарлагын тайлан'),
        ('report.product.ledger.income', u'Бараа материалын орлогын тайлан'),
        ('account.product.ledger.report', u'Бараа материалын дэлгэрэнгүй бүртгэл'),
        ('report.sales.gain.loss.partner', u'Борлуулалтын ашиг алдагдлын тайлан /Харилцагч/'),
        ('report.sales.gain.loss.product', u'Борлуулалтын ашиг алдагдлын тайлан /Бараа/'),
        ('report.sales.product.qty', u'Борлуулалтын тайлан /Тоо ширхэг/'),
        ('report.sales.shop', u'Борлуулалтын тайлан /Салбар/'),
        ('report.sales.productgainandloss', u'Борлуулалтын ашиг алдагдлын тайлан'),
        ('sales.info.graph', u'Борлуулалтын мэдээний хүснэгт'),
        ('report.sales.salesman.month', u'Захиалгын тайлан /Сараар/'),
        ('queue.report', u'Дарааллаар ажиллах тайлан'),
        ('report.internal.expense', u'Дотоод зарлагын тайлан'),
        ('report.purchase', u'Татан авалтын тайлан'),
        ('report.sales.shop.days', u'Өдрийн борлуулалтын тайлан'),
        ('report.sales.day.month', u'Өдрийн захиалгын тайлан'),
        ('report.sales.salesman.day', u'Өдрийн захиалгын тайлан-Харилцагчаар'),
        ('report.stock.move.complex', u'Бараа материалын дэлгэрэнгүй тайлан')
    ]
    
    INCRE_SELECTION = [
        ('month', 'Month'),
        ('week', 'Week'),
        ('period', 'Period'),
        ('day', 'Day')
    ]
    
    def _get_remaining(self, cr, uid, ids, name, args, context=None):
        res = {}
        for id in ids:
            res.setdefault(id, 0)
        cr.execute("select g.id, (select count(g2.id) from report_schedule_generator g2 "
                   "where g2.id <> g.id and g2.type = 'queued' and g2.queued_success = false "
                   "and g2.queued_date < g.queued_date) "
                   "from report_schedule_generator g "
                   "where g.id in %s and g.type = 'queued' and g.queued_success = false "
                   , (tuple(ids),))
        for gid, gcount in cr.fetchall() or []:
            res[gid] = gcount or 0
        return res

    name =             fields.Char('Name', size=256, required=True)
    # 'attache_name' :    fields.char('Attache Name', size=256, required=True)
    report_name =      fields.Selection(REPORT_SELECTION, 'Report', size=256, required=True)
    user_id =          fields.Many2one('res.users', 'Report Requester', required=True)
    active =           fields.Boolean('Active')
    params =           fields.Text('Report Data', readonly=True)
    date_last =        fields.Datetime('Last Generated Date', readonly=True)
    date_next =        fields.Date('Next Date', required=True)
    increment =        fields.Integer('Increment', required=True)
    increment_type =   fields.Selection(INCRE_SELECTION, 'Increment Mode', required=True)
    fixed =            fields.Boolean('Fixed start date?')
    user_ids =         fields.Many2many('res.users', 'report_schedule_generator_users_rel', 'generator_id', 'user_id', 'Other Users')

    type =             fields.Selection([('scheduled', 'Scheduled'), ('queued', 'Queued')], 'Type', required=True)
    queued_date =      fields.Datetime('Added Date')
    queued_success_date =   fields.Datetime('Success Date')
    queued_success =   fields.Boolean('Report Success')
    logging =              fields.Text('Report Log', readonly=True)
    remaining =        fields.Integer(compute = _get_remaining, method=True, string="Remaining Report", store=False)
    subject =          fields.Char('Subject', size=128)
    email_from =       fields.Char('From', size=128, help='Message sender, taken from user preferences. If empty, this is not a mail but a message.')
    email_to =         fields.Char('To', size=256, help='Message recipients')
    email_cc =         fields.Char('Cc', size=256, help='Carbon copy message recipients')
    email_bcc =        fields.Char('Bcc', size=256, help='Blind carbon copy message recipients')
    template_id =      fields.Many2one('email.template', 'Template')
    server_id =        fields.Many2one('ir.mail_server', 'Outgoing Mail Server')
    body_text =        fields.Text('Text contents', translate=True)

    
    _defaults = {
        'user_id': lambda obj, cr, uid, c:uid,
        'date_next': lambda *a: time.strftime('%Y-%m-%d'),
        'email_from': 'monoserp@monos.mn',
        'increment_type': 'day',
        'fixed': False,
        'type': 'scheduled'
    }
    
    def onchange_template_id(self, cr, uid, ids, template_id, context=None):
        res = {}
        context = context or {}
        if template_id:
            res.update({'value':{}})
            temp = self.pool.get('email.template').browse(cr, uid, template_id, context=context)
            if temp and temp.mail_server_id:
                res['value'].update({'server_id':temp.mail_server_id.id})
            if temp and temp.subject:
                res['value'].update({'subject':temp.subject})
        return res
    
    def onchange_report_name(self, cr, uid, ids, report, context=None):
        if report:
            return {'value':{'name':dict(self.REPORT_SELECTION).get(report, ''),
                             'subject':dict(self.REPORT_SELECTION).get(report, ''),
                             'body_text':dict(self.REPORT_SELECTION).get(report, '')}}
        return {}
    
    def auto_sendmail(self, cr, uid, ids, context=None):
        ''' Автомат тайланг ажиллаж дууссаны дараагаар 
            И-мэйлээр илгээнэ.
        '''
        context = context or {}
        template_obj = self.pool.get('email.template')
        message_obj = self.pool.get('mail.message')
        mail_server = self.pool.get('ir.mail_server')
        attachment_obj = self.pool.get('ir.attachment')
        for gen in self.browse(cr, uid, ids, context=context):
            if gen.server_id:
                body_text = ''
                if gen.body_text:
                    body_text += gen.body_text
                search_val = [('res_id', '=', gen.id), ('res_model', '=', 'report.schedule.generator')]
                attachment_ids = attachment_obj.search(cr, uid, search_val, limit=1, order='create_date desc', context=context)
                msg = mail_server.build_email(
                        email_from=gen.email_from,
                        email_to=[gen.email_to],
                        subject=gen.subject,
                        body=body_text,
                        body_alternative=None,
                        email_cc=gen.email_cc,
                        reply_to=False,
                        attachments=attachment_ids,
                        message_id=None,
                        references=False,
                        object_id=('%s-%s' % (gen.id, 'report.schedule.generator')),
                        subtype='plain',
                        subtype_alternative='plain')
                mail_server.send_email(cr, uid, msg,
                    mail_server_id=gen.server_id.id, context=context)
        return True
    
    def run_report_generator(self, cr, uid, ids, context=None):
        ''' Автомат тайлангуудыг ажиллуулна.
        '''
        if context is None:
            context = {}
        if not ids:
            ids = self.search(cr, uid, [('type', '=', 'scheduled')], context=context)
        generator_ids = self.search(cr, uid, [('active', '=', True),
                    ('date_next', '<=', time.strftime('%Y-%m-%d')),
                    ('id', 'in', ids)], context=context)
        for gen in self.browse(cr, uid, generator_ids, context=context):
            check_dict = get_check_report_name(gen.report_name)
            report_name = check_dict['report_name']
            if check_dict['expense']:
                context['each_report'] = 'expense'
            elif check_dict['income']:
                context['each_report'] = 'income'
            report_obj = self.pool.get(report_name)
            
            wizard_data = eval(gen.params)
            wizard_data.update({'save':True})
            for key in wizard_data:
                if isinstance(wizard_data.get(key), ListType):
                    wizard_data[key] = [[6, 0, wizard_data.get(key)]]
            generate_type = wizard_data.pop('generate_type')
            report_wiz_id = report_obj.create(cr, gen.user_id.id, wizard_data, context=context)
            context.update({'generator_id': gen.id})
            context.update({'attache_name':gen.name})
            if gen.user_ids:
                other_users = map(lambda x:x.id, gen.user_ids)
                context.update({'other_users':other_users})
            if generate_type == 'excel':
                result = report_obj.export_report(cr, gen.user_id.id,
                        [report_wiz_id], context=context)
            else :
                result = report_obj.print_report(cr, gen.user_id.id,
                        [report_wiz_id], context=context)
                report_service = netsvc.LocalService('report.' + result['report_name'])
                report_service.cr = cr
                report_service.uid = gen.user_id.id
                report_service.datas = result['datas']
                report_service.context = context
                report_service.pool = self.pool
                report_service.lang = context.get('lang', None)
                report_service.create(cr, uid, [], result['datas'], context)
            
            vals = {}
            wizard_data = eval(gen.params)
            if gen.increment_type <> 'period':
                date_start = get_date(wizard_data)
                date_start = datetime.datetime.strptime(date_start, '%Y-%m-%d')
                date_stop = date_start
                if gen.increment_type == 'day':
                    date_stop += relativedelta(days=gen.increment)
                elif gen.increment_type == 'month':
                    date_stop += relativedelta(months=gen.increment + 1)
                    date_stop = datetime.datetime.strptime(date_stop.strftime('%Y-%m-01'), '%Y-%m-%d') - relativedelta(days=1)
                else :  # 'week'
                    date_stop += relativedelta(days=gen.increment * 7)
                date_start += relativedelta(days=1)
                vals.update({'date_next':date_stop.strftime('%Y-%m-%d')})
                if not gen.fixed:
                    update_date(wizard_data, 'start', date_start.strftime('%Y-%m-%d'))  # Old date
                update_date(wizard_data, 'stop', date_stop.strftime('%Y-%m-%d'))
            else :  # by sales period
                period_obj = self.pool.get('stock.period')
                current_period_id = get_period(wizard_data)
                if not current_period_id:
                    current_period_id = period_obj.find(cr, uid, context=context)[0]
                current_period = period_obj.browse(cr, uid, current_period_id, context)
                next_period_id = period_obj.next(cr, uid, current_period, step=1, context=context)
                if next_period_id:
                    next_period = period_obj.browse(cr, uid, next_period_id, context)
                else :
                    next_period = current_period
                next_period0 = next_period
                if gen.increment > 1:
                    next_period_id = period_obj.next(cr, uid, next_period, step=gen.increment - 1, context=context)
                    next_period = period_obj.browse(cr, uid, next_period_id, context)
                
                vals.update({'date_next':next_period.date_stop})
                if not gen.fixed:
                    update_period(wizard_data, 'start', next_period0.id)
                update_period(wizard_data, 'stop', next_period.id)
            
            vals.update({'date_last': time.strftime('%Y-%m-%d %H:%M:%S'),
                         'params':wizard_data.__repr__()})
            self.write(cr, uid, [gen.id], vals, context=context)
            self.auto_sendmail(cr, uid, ids, context=context)
        return True
    
report_schedule_generator()

class report_schedule_generator_wizard(models.TransientModel):
    _name = 'report.schedule.generator.wizard'
    _description = 'Report Schedule Generator Wizard'

    # 'report_type': fields.selection([('excel','Excel'),('pdf','PDF')], 'Report Type', required=True)
    wizard_id = fields.Integer('Wizard Object ID')

    
    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        
        generator = self.pool.get('report.schedule.generator').browse(cr,
                        uid, context['active_id'], context=context)
        check_dict = get_check_report_name(generator.report_name)
        report_name = check_dict['report_name']
        if check_dict['expense']:
            context['each_report'] = 'expense'
        elif check_dict['income']:
            context['each_report'] = 'income'
        report_obj = self.pool.get(report_name)
        report_fields = report_obj.fields_get_keys(cr, uid, context)
        res = report_obj.default_get(cr, generator.user_id.id, report_fields, context=context)
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        """
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view.
         
        """
        if context.get('active_model', False) == 'report.schedule.generator':
            generator = self.pool.get('report.schedule.generator').browse(cr,
                            uid, context['active_id'], context=context)
            check_dict = get_check_report_name(generator.report_name)
            report_name = check_dict['report_name']
            if check_dict['expense']:
                context['each_report'] = 'expense'
            elif check_dict['income']:
                context['each_report'] = 'income'
            report_obj = self.pool.get(report_name)
            report_fields = report_obj.fields_get_keys(cr, uid, context)
            res = report_obj.fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                context=context, toolbar=toolbar, submenu=False)
            doc = etree.XML(res['arch'])
            nodes = doc.xpath('//group[@name="control_bar"]')
            for node in nodes:
                doc.remove(node)
            nodes = doc.xpath('//footer')
            for node in nodes:
                doc.remove(node)
            root_nodes = doc.xpath('//form')
            if root_nodes:
                group = etree.SubElement(root_nodes[0], 'footer')
                etree.SubElement(group, 'button', attrib={
                        'name': "print_report",
                        'string': _("Print"),
                        'type': "object",
                        'class':"oe_highlight",
                })
                etree.SubElement(group, 'button', attrib={
                        'name': "export_report",
                        'string': _("Export"),
                        'type': "object",
                        'class':"oe_highlight",
                })
                etree.SubElement(group, 'label', attrib={'string':'or'})
                etree.SubElement(group, 'button', attrib={
                        'special': "cancel",
                        'string': _("Close"),
                        'type': "object",
                        'class':"oe_link",
                })
            res['arch'] = etree.tostring(doc)
            
            # report_fields = report_obj.fields_get_keys(cr, uid, context)
            # print 'fields_get :', report_obj.fields_get(cr, uid, report_fields, context)
            # res0 = super(report_schedule_generator_wizard, self).fields_view_get(cr, uid, 
            #    view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        else :
            res = super(report_schedule_generator_wizard, self).fields_view_get(cr, uid,
                view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        return res
    
    def create(self, cr, uid, vals, context=None):
        generator = self.pool.get('report.schedule.generator').browse(cr,
                        uid, context['active_id'], context=context)
        check_dict = get_check_report_name(generator.report_name)
        report_name = check_dict['report_name']
        if check_dict['expense']:
            context['each_report'] = 'expense'
        elif check_dict['income']:
            context['each_report'] = 'income'
        report_obj = self.pool.get(report_name)
        wizard_id = report_obj.create(cr, uid, vals, context=context)
        vals = {'wizard_id': wizard_id}
        return super(report_schedule_generator_wizard, self).create(cr, uid, vals, context=context)
    
    def make_params(self, cr, uid, ids, extra, context=None):
        if context is None:
            context = {}
        generator = self.pool.get('report.schedule.generator').browse(cr,
                            uid, context['active_id'], context=context)
        check_dict = get_check_report_name(generator.report_name)
        report_name = check_dict['report_name']
        if check_dict['expense']:
            context['each_report'] = 'expense'
        elif check_dict['income']:
            context['each_report'] = 'income'
        report_obj = self.pool.get(report_name)
        
        obj = self.browse(cr, uid, ids[0], context=context)
        data = report_obj.read(cr, uid, obj.wizard_id, context=context)
        del data['id']
        del data['save']
        # fix many2one data -------------------------------------------------
        for f, d in report_obj.fields_get(cr, uid, context=context).iteritems():
            if d['type'] == 'many2one' and data[f]:
                data[f] = data[f][0]
        
        next_date = get_date(data)
        incr_type = 'day'
        if not next_date:
            period = get_period(data)
            if period:
                next_date = self.pool.get('stock.period').browse(cr, uid, period).date_stop
                incr_type = 'period'
        if not next_date:
            next_date = time.strftime('%Y-%m-%d')
        data.update(extra)
        self.pool.get('report.schedule.generator').write(cr, uid, context['active_id'],
               {'params':data.__repr__(), 'date_next':next_date,
                'increment_type':incr_type}, context=context)
        return True
    
    def print_report(self, cr, uid, ids, context=None):
        self.make_params(cr, uid, ids, {'generate_type':'pdf'}, context=context)
        
        return {'type':'ir.actions.act_window.close'}
    
    def export_report(self):
        self.make_params({'generate_type':'excel'})
        
        return {'type':'ir.actions.act_window.close'}

report_schedule_generator_wizard()
