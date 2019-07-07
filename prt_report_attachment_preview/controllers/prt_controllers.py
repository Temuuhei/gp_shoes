from odoo import http
from odoo.http import request, Response
#from odoo.addons.web.controllers.main import ReportController, Binary
import werkzeug
import json
import imghdr
from werkzeug.urls import url_decode
from odoo.tools.safe_eval import safe_eval
from odoo.tools import crop_image, html_escape
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
import time
import io
import os
import odoo
import base64
import functools
import logging
_logger = logging.getLogger(__name__)
import unicodedata
from odoo.modules import get_resource_path
db_monodb = http.db_monodb

# List of content types that will be opened in browser
OPEN_BROWSER_TYPES = ['application/pdf']

######################
# Report Controllers #
######################

class ReportController(http.Controller):

    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['report']._get_report_from_name(reportname)
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])
        if converter == 'html':
            html = request.env['report'].get_html(docids, reportname, data=data)
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = request.env['report'].get_pdf(docids, reportname, data=data)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @http.route(['/report/barcode', '/report/barcode/<type>/<path:value>'], type='http', auth="public")
    def report_barcode(self, type, value, width=600, height=100, humanreadable=0):
        """Contoller able to render barcode images thanks to reportlab.
        Samples:
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
        'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
        'UPCA', 'USPS_4State'
        :param humanreadable: Accepted values: 0 (default) or 1. 1 will insert the readable value
        at the bottom of the output image
        """
        try:
            barcode = request.env['report'].barcode(type, value, width=width, height=height, humanreadable=humanreadable)
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type == 'qweb-pdf':
                reportname = url.split('/report/pdf/')[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter='pdf')
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter='pdf', **dict(data))

                report = request.env['report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, "pdf")
                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, "pdf")
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

    @http.route(['/report/check_wkhtmltopdf'], type='json', auth="user")
    def check_wkhtmltopdf(self):
        return request.env['report']._check_wkhtmltopdf()

    def binary_content(xmlid=None, model='ir.attachment', id=None, field='datas', unique=False,
                   filename=None, filename_field='datas_fname', download=False, mimetype=None,
                   default_mimetype='application/octet-stream', access_token=None, env=None):
        return request.registry['ir.http'].binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token, env=env)

class Binary(http.Controller):
    def placeholder(self, image='placeholder.png'):
        addons_path = http.addons_manifest['web']['addons_path']
        return open(os.path.join(addons_path, 'web', 'static', 'src', 'img', image), 'rb').read()

    def force_contenttype(self, headers, contenttype='image/png'):
        dictheaders = dict(headers)
        dictheaders['Content-Type'] = contenttype
        return list(dictheaders.items())

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<int:id>-<string:unique>',
        '/web/content/<int:id>-<string:unique>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='datas_fname', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, **kw):
        status, headers, content = binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            access_token=access_token)
        if status == 304:
            response = werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            response = request.not_found()
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        if token:
            response.set_cookie('fileToken', token)
        return response

    @http.route(['/web/image',
        '/web/image/<string:xmlid>',
        '/web/image/<string:xmlid>/<string:filename>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>',
        '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>',
        '/web/image/<int:id>/<string:filename>',
        '/web/image/<int:id>/<int:width>x<int:height>',
        '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>-<string:unique>',
        '/web/image/<int:id>-<string:unique>/<string:filename>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='datas_fname', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None):
        status, headers, content = binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', access_token=access_token)
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200 and download:
            return request.not_found()

        if headers and dict(headers).get('Content-Type', '') == 'image/svg+xml':  # we shan't resize svg images
            height = 0
            width = 0
        else:
            height = int(height or 0)
            width = int(width or 0)

        if crop and (width or height):
            content = crop_image(content, type='center', size=(width, height), ratio=(1, 1))

        elif content and (width or height):
            # resize maximum 500*500
            if width > 500:
                width = 500
            if height > 500:
                height = 500
            content = odoo.tools.image_resize_image(base64_source=content, size=(width or None, height or None), encoding='base64', filetype='PNG')
            # resize force png as filetype
            headers = self.force_contenttype(headers, contenttype='image/png')

        if content:
            image_base64 = base64.b64decode(content)
        else:
            image_base64 = self.placeholder(image='placeholder.png')  # could return (contenttype, content) in master
            headers = self.force_contenttype(headers, contenttype='image/png')

        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status_code = status
        return response

    # backward compatibility
    @http.route(['/web/binary/image'], type='http', auth="public")
    def content_image_backward_compatibility(self, model, id, field, resize=None, **kw):
        width = None
        height = None
        if resize:
            width, height = resize.split(",")
        return self.content_image(model=model, id=id, field=field, width=width, height=height)

class PrtReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        res = super(PrtReportController, self).report_download(data, token)
        res.headers['Content-Disposition'] = res.headers['Content-Disposition'].replace('attachment', 'inline')
        return res


######################
# Binary Controllers #
######################
class PrtBinaryController(Binary):
    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<int:id>-<string:unique>',
        '/web/content/<int:id>-<string:unique>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='datas_fname', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, **kw):

        res = super(PrtBinaryController, self).content_common(xmlid=xmlid, model=model, id=id, field=field,
                                                              filename=filename, filename_field=filename_field,
                                                              unique=unique, mimetype=mimetype,
                                                              download=download, data=data, token=token,
                                                              access_token=access_token, **kw)
        if res.headers.get('Content-type', 'other') in OPEN_BROWSER_TYPES:
            res.headers['Content-Disposition'] = res.headers['Content-Disposition'].replace('attachment', 'inline')
        return res
