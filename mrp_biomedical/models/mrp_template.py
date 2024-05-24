# -*- coding: utf-8 -*-
from odoo import models, fields


class MrpBiomedicalTemplate(models.Model):
    _name = 'mrp.biomedical.template'
    _description = 'MRP Biomedical Templates'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text(string='Template Description', tracking=True)
    signature_required = fields.Boolean(string='Signature Required?',
                                        help="Check this if a signature is required for the template.", tracking=True)
    html_content = fields.Html(string='HTML Content', help="Enter the HTML content for the template.")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], string='State', default='draft', tracking=True)

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_confirm(self):
        self.write({'state': 'confirm'})
