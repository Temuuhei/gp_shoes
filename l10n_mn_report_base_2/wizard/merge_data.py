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

from openerp import api, fields, models, _
import logging

_logger = logging.getLogger('tool')

class DataMergeTool(models.Model):
    _name = 'tool.data.merge'
    _description = 'Data Merge Tool'
    
    merge_model_id = fields.Many2one('ir.model', 'Merging Model', required=True)
    merge_resource_from = fields.Integer('From Resource', digits=(10,0))
    merge_resource_to = fields.Integer('To Resource', digits=(10,0))
    
    @api.one
    def domerge(self):
        def _merge(cr, merge_table, from_id, to_id):
            cr.execute("""SELECT
                    tc.constraint_name, tc.table_name, kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    tc.table_name AS parent_table_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                WHERE constraint_type = 'FOREIGN KEY' AND ccu.table_name = '%s';
            """ % merge_table)
            fetched = cr.fetchall()
            
            for cname, table, column, ft, pt in fetched:
                if table in relation_tables:
                    cr.execute("select * from "+table+" where \""+ column +"\" = "+ str(from_id))
                    for m2m_value in cr.dictfetchall():
                        another_column = False
                        for col, val in m2m_value.iteritems():
                            if col == column:
                                continue
                            else:
                                another_column = col
                        cr.execute("select count(*) from "+table+" where \""+column+"\" = "+ str(to_id)+
                                   " and \""+another_column+"\" = "+ str(m2m_value[another_column]))
                        f = cr.fetchone()[0]
                        if f:
                            cr.execute("delete from "+ table +" where \""+column+"\" = "+ str(from_id)+
                                   " and \""+another_column+"\" = "+ str(m2m_value[another_column]))
                        
                
                cr.execute("update "+ table + " set \""+ column + "\" = " + str(to_id) 
                   + " where \"" + column +"\" = "+str(from_id)+" ")
                
            cr.execute("delete from %s where id = %s" % (merge_table, from_id))
        
        model_pool = self.env[self.merge_model_id.model]
        relation_tables = self.env['ir.model.relation'].search([]).mapped("name")
        
        todo_merge = [(model_pool._table, self.merge_resource_from, self.merge_resource_to)]
        if model_pool._inherits:
            for inh_model, inh_field in model_pool._inherits.iteritems():
                inh_model_pool = self.env[inh_model]
                inh_resource_from = model_pool.browse(self.merge_resource_from)[inh_field].id
                inh_resource_to = model_pool.browse(self.merge_resource_to)[inh_field].id
                
                todo_merge += [(inh_model_pool._table, inh_resource_from, inh_resource_to)]
        
        for todo in todo_merge:
            _merge(self._cr, *todo)
        
        _logger.info('%s data merged from %s id to %s id.' % (model_pool._description, self.merge_resource_from,
                                                              self.merge_resource_to))
    