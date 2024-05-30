# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class MrpBiomedicalTemplate(models.Model):
    _name = 'mrp.biomedical.template'
    _description = 'MRP Biomedical Templates'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text(string='Template Description', tracking=True)
    signature_required = fields.Boolean(string='Signature Required?',
                                        help="Check this if a signature is required for the template.", tracking=True)
    html_content = fields.Html(string='HTML Content', help="Enter the HTML content for the template.")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], string='State', default='draft', tracking=True)

    def action_draft(self):
        for template in self:
            if template.state == 'confirm':
                operations = self.env['mrp.biomedical.bom.operation'].search([('template_id', '=', template.id)])
                if operations:
                    raise ValidationError(f"Please remove the template first from the Operations '{', '.join(operations.mapped('name'))}' in BoMs '{', '.join(operations.mapped('bom_id.reference'))}' before Setting template '{template.name}' to Draft.")
            template.write({'state': 'draft'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def unlink(self):
        for template in self:
            operations = self.env['mrp.biomedical.bom.operation'].search([('template_id', '=', template.id)])
            if operations:
                raise ValidationError(f"Please remove the template first from the Operations '{', '.join(operations.mapped('name'))}' in BoMs '{', '.join(operations.mapped('bom_id.reference'))}' before deleting the template '{template.name}'.")

        res = super().unlink()
        return res

    def action_archive(self):
        for template in self:
            if template.state == 'confirm':
                raise ValidationError(
                    f"Please Set the template '{template.name}' to Draft before archiving it.")

        return super().action_archive()
