# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from openerp import models, fields, api
from openerp.tools.translate import _, translate

class ReportExcelOutput(models.TransientModel):
    _name = 'report.excel.output.extend'

    filename = fields.Char('File name', readonly=True)
    filedata = fields.Binary('File data', readonly=True)

    @api.multi
    def export_report(self):
        self.ensure_one()

        # get time
        if self.env.user.partner_id.tz:
            tz = pytz.timezone(self.env.user.partner_id.tz)
        else:
            tz = pytz.utc
        now_utc = datetime.now(pytz.timezone('UTC'))
        now_user_zone = now_utc.astimezone(tz)

        filename_prefix = self.env.context.get('filename_prefix', 'report_excel_output')
        filename = "%s_%s.xls" % (filename_prefix, now_user_zone.strftime('%Y%m%d_%H%M%S'))
        self.filename = filename

        form_title = self.env.context.get('form_title', _('Report Result'))

        mod_obj = self.env['ir.model.data']
        form_res = mod_obj.get_object_reference('gp_product_sale_report', 'report_excel_output_view_form')
        form_id = form_res and form_res[1] or False
        return {
            'name': form_title,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.excel.output.extend',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def _(self, source):
        '''
        Translation method for selection field
        '''
        # currently only in selection fields
        result = translate(self.env.cr, False, 'selection', self.env.context['lang'], source) or source
        return result