# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MrpBiomedicalProduction(models.Model):
    _name = 'mrp.biomedical.production'
    _description = 'MRP Biomedical Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_start asc,id'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], string='Priority', default='0',
        help="Components will be reserved first for the MO with the highest priorities.")

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="[('type', 'in', ['product', 'consu'])]",
        compute='_compute_product_id', store=True, copy=True, precompute=True,
        readonly=False, required=True, check_company=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce', digits='Product Unit of Measure',
        readonly=False, required=True, tracking=True, default=1.0)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=False, required=False, compute='_compute_uom_id', store=True, copy=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")

    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_deadline = fields.Datetime(
        'Deadline', copy=False, help="Informative date allowing to define when the manufacturing order should be processed at the latest to fulfill delivery on time.")
    date_start = fields.Datetime(
        'Start', copy=False,
        help="Date you plan to start production or date you actually started production.",
        index=True, required=True)
    date_finished = fields.Datetime(
        'Date End', copy=False, help="Date you expect to finish production or actual date you finished production.")
    duration_expected = fields.Float("Expected Duration", help="Total expected duration (in minutes)")
    duration = fields.Float("Real Duration", help="Total real duration (in minutes)")

    bom_id = fields.Many2one(
        'mrp.biomedical.bom', 'Bill of Material',
        check_company=True,
        help="Bills of Materials, also called recipes, are used to autocomplete components and work order instructions.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State', copy=False, index=True, readonly=True, default='draft',
        store=True, tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")

    component_ids = fields.One2many('mrp.production.component', 'order_id')
    operation_ids = fields.One2many('mrp.production.operation', 'order_id')

    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.depends('bom_id', 'product_id')
    def _compute_uom_id(self):
        for production in self:
            if production.state != 'draft':
                continue
            if production.bom_id and production._origin.bom_id != production.bom_id:
                production.product_uom_id = production.bom_id.product_uom_id
            elif production.product_id:
                production.product_uom_id = production.product_id.uom_id
            else:
                production.product_uom_id = False

    @api.depends('bom_id')
    def _compute_product_id(self):
        for production in self:
            bom = production.bom_id
            if bom and bom.product_id != production.product_id:
                production.product_id = bom.product_id

    @api.depends('bom_id')
    def _compute_product_qty(self):
        for production in self:
            if production.state != 'draft':
                continue
            if production.bom_id:
                production.product_qty = production.bom_id.product_qty
            elif not production.bom_id:
                production.product_qty = 1.0

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if self.bom_id:
            # Update component quantities based on the BoM and new product_qty
            for component in self.component_ids:
                for bom_component in self.bom_id.component_ids:
                    if component.product_id == bom_component.product_id:
                        component.product_qty = bom_component.product_qty * (self.product_qty / self.bom_id.product_qty)
        else:
            # No BoM selected, update component quantities based on the new product_qty
            for component in self.component_ids:
                component.product_qty *= self.product_qty / self._origin.product_qty

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            # Clear existing components
            self.component_ids = [(5, 0, 0)]
            self.operation_ids = [(5, 0, 0)]
            # Fetch components from the selected BoM
            components = []

            bom_operations = self.bom_id.operation_ids
            operations = []

            for operation in bom_operations:
                operations.append((0, 0, {
                    'operation_ids': [(6, 0, operation.operation_ids.ids)],
                    'name': operation.name,
                    'duration': operation.duration,
                    'sequence': operation.sequence,
                    'template_id': operation.template_id.id,
                    'department_ids': [(6, 0, operation.department_ids.ids)]
                }))

            for component in self.bom_id.component_ids:
                components.append((0, 0, {
                    'product_id': component.product_id.id,
                    'product_qty': component.product_qty,
                    'product_uom_id': component.product_uom_id.id,
                }))
            self.component_ids = components
            self.operation_ids = operations
            self.product_qty = self.bom_id.product_qty
        else:
            # Clear components if no BoM is selected
            self.component_ids = [(5, 0, 0)]
            self.operation_ids = [(5, 0, 0)]
            self.product_qty = 1.0

    # @api.depends('workorder_ids.duration_expected')
    # def _compute_duration_expected(self):
    #     for production in self:
    #         production.duration_expected = sum(production.workorder_ids.mapped('duration_expected'))

    # @api.depends('workorder_ids.duration')
    # def _compute_duration(self):
    #     for production in self:
    #         production.duration = sum(production.workorder_ids.mapped('duration'))

    @api.depends('product_uom_id', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for production in self:
            if production.product_id.uom_id != production.product_uom_id:
                production.product_uom_qty = production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id)
            else:
                production.product_uom_qty = production.product_qty

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.biomedical.production') or _('New')
        return super(MrpBiomedicalProduction, self).create(vals)


class MrpBiomedicalComponent(models.Model):
    _name = 'mrp.production.component'
    _description = 'MRP Production Components'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    order_id = fields.Many2one('mrp.biomedical.production', ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True, related='order_id.company_id')
    order_product_id = fields.Many2one('product.product', related='order_id.product_id')
    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True)
    product_qty = fields.Float(
        'To Consume', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_product_uom_id, required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')


class MrpProductionOperation(models.Model):
    _name = 'mrp.production.operation'
    _description = 'MRP Production Operations'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    order_id = fields.Many2one('mrp.biomedical.production', ondelete='cascade')
    order_bom_id = fields.Many2one(
        'mrp.biomedical.bom', 'Bill of Material',
        check_company=True,
        help="Bills of Materials, also called recipes, are used to autocomplete components and work order instructions.", related='order_id.bom_id', store=True)
    company_id = fields.Many2one('res.company', required=True, related='order_id.company_id')
    order_product_id = fields.Many2one('product.product', related='order_id.product_id')
    operation_ids = fields.Many2many('mrp.biomedical.bom.operation', relation='mrp_production_operation_dependency_rel',
                                     column1='operation_id', column2='dependency_id', string='Operation Dependencies',
                                     check_company=True,
                                     help="""Select this BoM operations on which this operation depends. The operations selected will be checked in order i.e. if the selected operations are completed, only then this operation will be able to be processed.""")
    signature_required = fields.Boolean(string='Signature Required?', related='template_id.signature_required',
                                        readonly=False, store=True)
    template_id = fields.Many2one('mrp.biomedical.template', string='Template', required=True,
                                  domain=[('state', '=', 'confirm')], check_company=True)
    department_ids = fields.Many2many('hr.department', string='Departments', required=True, check_company=True)
    name = fields.Char(string='Name', required=True)
    duration = fields.Float(string='Duration', required=True)
    sequence = fields.Integer(string='Sequence')
