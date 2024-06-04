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
        'End', copy=False, help="Date you expect to finish production or actual date you finished production.")
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
        ('cancel', 'Cancelled')], string='State', copy=False, index=True, readonly=True,
        store=True, tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
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
