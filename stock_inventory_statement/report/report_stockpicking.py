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

from openerp.osv import osv
from openerp.tools.translate import _
from operator import itemgetter
from openerp.addons.l10n_mn_report_base.report_helper import verbose_numeric,comma_me
import sys
        
class ReportPicking(osv.AbstractModel):
    _name = 'report.l10n_mn_stock.report_stockpicking'
    
    def render_html(self, cr, uid, ids, data=None, context=None):
        if context is None:
            context = {}
        report_obj = self.pool['report']
        picking_obj = self.pool['stock.picking']
        uom_obj = self.pool['product.uom']
        if data and not ids:
            ids = data['ids']
        pickings = picking_obj.browse(cr, uid, ids, context=context)
        report = report_obj._get_report_from_name(cr, uid, 'l10n_mn_stock.report_stockpicking')
        pack_datas = {}
        datas = {}
        weights = {'volume': 0.0,
                   'weight': 0.0,
                   'weight_net': 0.0}
        total = {'pack': 0.0,
                 'loose': 0.0,
                 'total': 0.0}
        local = {'yes': 'False',
                'driver': '',
                'team': '',
                'wname': ''}
        if data and 'driver_id' in data and data['driver_id']:
            emp = self.pool.get('hr.employee').browse(cr, uid, data['driver_id'], context=context)
            local['yes'] = 'True'
            local['driver'] = emp.name
            if emp.mobile_phone:
                local['driver'] += ' ('
                local['driver'] += emp.mobile_phone
                local['driver'] += ')'
        if data and 'team_id' in data and data['team_id']:
            crm = self.pool.get('crm.case.section').browse(cr, uid, data['team_id'], context=context)
            local['yes'] = 'True'
            local['team'] = crm.name
        if data and 'warehouse_id' in data and data['warehouse_id']:
            wh = self.pool.get('stock.warehouse').browse(cr, uid, data['warehouse_id'], context=context)
            local['yes'] = 'True'
            local['wname'] = wh.name
        pick_names = ''
        team_names_list = []
        team_names_str = ''
        lot_dict = {}
        for pick in pickings:
            pick_names += pick.name
            pick_names += ', '
            
            if pick.section_id.name not in team_names_list and pick.section_id.name:
                team_names_str += pick.section_id.name+','
                team_names_list.append(pick.section_id.name)
            
            if pick.pack_operation_ids:
                for oper in pick.pack_operation_ids:
                    key = '%s.%s'%(oper.product_id.id,oper.lot_id and oper.lot_id.id or False)
                    pack_qty = 0.0
                    product_qty = oper.product_qty
                    packaging = (oper.product_id.packaging_ids and oper.product_id.packaging_ids[0]) or False
                    if packaging:
                        pack_qty = packaging.qty
                    if oper.product_id.uom_id.id <> oper.product_uom_id.id:
                        product_qty = uom_obj._compute_qty(cr, uid, oper.product_uom_id.id, 
                                    oper.product_qty, oper.product_id.uom_id.id)
                    if oper.product_id.id not in pack_datas:
                        pack_datas[oper.product_id.id] = {'package': pack_qty,
                                                          'qty': 0.0,
                                                          'count': 0}
                    if key not in datas:                        
                        ean13 = oper.product_id.ean13 if oper.product_id.ean13 else ''
                        datas[key] = {'name': oper.product_id.name_get(context=context)[0][1] + " [" + ean13 + "]",
                                      'uom': oper.product_id.uom_id.name,
                                      'id': oper.product_id.id,
                                      'qty': 0.0,
                                      'pack': 0.0,
                                      'loose': 0.0,
                                      'total': 0.0,
                                      'lot': oper.lot_id.name or '',                                      
#                                     'lot': oper.lot_id and oper.lot_id.name or '', #initial
                                      'date': oper.lot_id and oper.lot_id.life_date or '',
                                      'ean': ean13}
                        pack_datas[oper.product_id.id]['count'] += 1
                    pack_datas[oper.product_id.id]['qty'] += product_qty
                    datas[key]['qty'] += product_qty
                    weights['volume'] += oper.product_id.volume or 0.0
                    weights['weight'] += oper.product_id.weight or 0.0
                    weights['weight_net'] += oper.product_id.weight_net or 0.0
            else:
                for move in pick.move_lines:
                    key = '%s.%s'%(move.product_id.id,False)
                    pack_qty = 0.0
                    product_qty = move.product_qty
                    packaging = (move.product_id.packaging_ids and move.product_id.packaging_ids[0]) or False
                    if packaging:
                        pack_qty = packaging.qty
                    if move.product_id.uom_id.id <> move.product_uom.id:
                        product_qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)
                    if move.product_id.id not in pack_datas:
                        pack_datas[move.product_id.id] = {'package': pack_qty,
                                                          'qty': 0.0,
                                                          'count': 0}
                    if key not in datas:
                        ean13 = move.product_id.ean13 if move.product_id.ean13 else ''
                        datas[key] = {'name': move.product_id.name_get(context=context)[0][1] + " [" + ean13 + "]",
                                       'uom': move.product_id.uom_id.name,
                                       'id': move.product_id.id,
                                       'qty': 0.0,
                                       'pack': 0.0,
                                       'loose': 0.0,
                                       'total': 0.0,
                                       'lot': '',
                                       'date': '',
                                       'ean': ean13}
                        pack_datas[move.product_id.id]['count'] += 1
                    pack_datas[move.product_id.id]['qty'] += product_qty
                    datas[key]['qty'] += product_qty
                    weights['volume'] += move.product_id.volume or 0.0
                    weights['weight'] += move.product_id.weight or 0.0
                    weights['weight_net'] += move.product_id.weight_net or 0.0
        pdatas = {}
        if pack_datas:
            for k,v in pack_datas.iteritems():
                pack = 0.0
                loose = v['qty']
                if v['package'] > 0:
                    pack = (v['qty'] <> 0 and int(int(v['qty'])/ int(v['package']))) or 0
                    loose = (v['qty'] <> 0 and v['qty'] % v['package']) or 0
                if k not in pdatas:
                    pdatas[k] = {'pack': comma_me(pack),
                                 'loose': comma_me(loose),
                                 'total': comma_me(v['qty']),
                                 'count': v['count']}
                total['pack'] += pack
                total['loose'] += loose
                total['total'] += v['qty']
        total['pack'] = comma_me(total['pack'])
        total['loose'] = comma_me(total['loose'])
        total['total'] = comma_me(total['total'])        
        docargs = {
            'pack_datas': sorted(datas.values(), key=itemgetter('name')),
            'packs': pdatas,
            'pick_names': pick_names,
            'team_names': team_names_str,
            'weights': weights,
            'total': total,
            'local': local,
            'docs': [pickings[0]],
            'doc_model': report.model,
            'data_report_margin_top': 5,
            'data_report_header_spacing': 5
        }
        return report_obj.render(cr, uid, ids, 'stock.report_picking', docargs, context=context)
