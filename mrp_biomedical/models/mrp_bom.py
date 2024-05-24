# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MrpBiomedicalBom(models.Model):
    _name = 'mrp.biomedical.bom'
    _description = 'Mrp Biomedical, Bill of Materials'
    _rec_name = 'product_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    active = fields.Boolean('Active', default=True)
    reference = fields.Char(string='Reference', tracking=True, reequired=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True, domain=[('detailed_type', '=', 'product')])
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True,
        help="This should be the smallest quantity that this product can be produced in.")

    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_product_uom_id, required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    component_ids = fields.One2many('mrp.biomedical.bom.component', 'bom_id', tracking=True)
    operation_ids = fields.One2many('mrp.biomedical.bom.operation', 'bom_id', tracking=True)

    _sql_constraints = [
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.constrains('component_ids')
    def _check_duplicate_components(self):
        for bom in self:
            components = bom.component_ids
            component_ids = components.mapped('product_id.id')
            if len(component_ids) != len(components):
                raise ValidationError('You cannot select the same components twice.')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.component_ids:
            self.component_ids = False
        if self.operation_ids:
            self.operation_ids = False

    def name_get(self):
        return [(record.id, "%s - %s" % (record.product_id.name, record.reference)) if record.reference else (record.id, "%s" % record.product_id.name) for record in self]


class MrpBiomedicalBomComponent(models.Model):
    _name = 'mrp.biomedical.bom.component'
    _description = 'Mrp Biomedical, BoM Components'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    bom_id = fields.Many2one('mrp.biomedical.bom', ondelete='cascade')
    bom_product_id = fields.Many2one('product.product', related='bom_id.product_id')
    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True)
    product_ids = fields.Many2one('product.product', string='Product Domain', compute='_compute_product_ids')
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_product_uom_id, required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')


class MrpBiomedicalBomOperation(models.Model):
    _name = 'mrp.biomedical.bom.operation'
    _description = 'Mrp Biomedical, BoM Operations'

    bom_id = fields.Many2one('mrp.biomedical.bom', ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    template_id = fields.Many2one('mrp.biomedical.template', string='Template', required=True)
    duration = fields.Float(string='Duration', required=True)
    signature_required = fields.Boolean(string='Signature Required?', related='template_id.signature_required', readonly=False, store=True)
    sequence = fields.Integer(string='Sequence')

    @api.constrains('duration')
    def _check_duration(self):
        for record in self:
            if record.duration == 0.0:
                raise ValidationError(f"Duration cannot be set as 00:00 for Operation {record.name}.")
