# -*- coding: utf-8 -*-
##############################################################################
#
#    Game of Code LLC, Enterprise Management Solution
#    Copyright Game of Code LLC (C) 2017 . All Rights Reserved
#
#    Address :
#    Email :
#    Phone :
#
##############################################################################

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp

class account_payment_term(models.Model):
    _inherit = "account.payment.term"
    type = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mixed', 'Mixed'),
        ], string='Payment Type')

    # def name_get(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     if isinstance(ids, (int, long)):
    #         ids = [ids]
    #     res = []
    #     for record in self.browse(cr, uid, ids, context=context):
    #         name = record.name
    #         emp_ids = self.pool.get('hr.employee').search(cr, uid, [('address_home_id', '=', record.id)])
    #         if emp_ids:
    #             emp_obj = self.pool.get('hr.employee').browse(cr, uid, emp_ids)
    #             for emp in emp_obj:
    #                 if emp.department_id.short_name:
    #                     name += ' [%s] ' % (emp.department_id.short_name,)
    #                 if emp.job_id:
    #                     name += ' %s' % (emp.job_id.name,)
    #         res.append((record.id, name))
    #     return res
    default = fields.Boolean ('Default')