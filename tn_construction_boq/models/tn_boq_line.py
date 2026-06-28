from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class TnConstructionBudget(models.Model):
    _name = 'tn.construction.budget'
    _description = 'Construction Sub Project Budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, default='New Budget', tracking=True)
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        string='Sub Project',
        domain="[('project_id', '=', project_id)]",
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    start_date = fields.Date()
    end_date = fields.Date()
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='draft',
        tracking=True,
    )
    progress = fields.Float(string='Progress (%)', compute='_compute_budget_totals')
    line_ids = fields.One2many(
        'tn.construction.budget.line',
        'budget_id',
        string='Budget Lines',
    )
    confirmation_ids = fields.One2many(
        'tn.construction.budget.confirmation',
        'budget_id',
        string='Budget Line Confirmation',
    )
    line_count = fields.Integer(compute='_compute_budget_totals')
    total_budget_amount = fields.Monetary(
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id',
    )
    budget_utilization = fields.Monetary(
        compute='_compute_budget_totals',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.depends(
        'line_ids.total_budget_amount',
        'line_ids.material_spent',
        'line_ids.equipment_spent',
    )
    def _compute_budget_totals(self):
        for budget in self:
            budget.line_count = len(budget.line_ids)
            budget.total_budget_amount = sum(budget.line_ids.mapped('total_budget_amount'))
            budget.budget_utilization = sum(
                budget.line_ids.mapped('material_spent')
            ) + sum(budget.line_ids.mapped('equipment_spent'))
            budget.progress = (
                budget.budget_utilization / budget.total_budget_amount * 100.0
                if budget.total_budget_amount
                else 0.0
            )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for budget in self:
            project = budget.project_id
            if not project:
                continue
            budget.company_id = project.company_id
            budget.start_date = project.date_start
            budget.end_date = project.date

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id(self):
        for budget in self:
            sub_project = budget.sub_project_id
            if not sub_project:
                continue
            budget.project_id = sub_project.project_id
            budget.company_id = sub_project.company_id
            budget.start_date = sub_project.schedule_start_date
            budget.end_date = sub_project.schedule_end_date

    def action_submit_for_approval(self):
        self.write({'state': 'waiting_approval'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_view_budget_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Lines'),
            'res_model': 'tn.construction.budget.line',
            'view_mode': 'list,form',
            'domain': [('budget_id', '=', self.id)],
            'context': {
                'default_budget_id': self.id,
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.sub_project_id.id,
            },
        }


class TnConstructionBudgetLine(models.Model):
    _name = 'tn.construction.budget.line'
    _description = 'Construction Budget Line'
    _order = 'budget_id, sequence, id'

    sequence = fields.Integer(default=10)
    budget_id = fields.Many2one(
        'tn.construction.budget',
        required=True,
        ondelete='cascade',
    )
    project_id = fields.Many2one(
        'project.project',
        related='budget_id.project_id',
        store=True,
        readonly=True,
    )
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        related='budget_id.sub_project_id',
        store=True,
        readonly=True,
    )
    work_type = fields.Char(required=True)
    work_sub_type = fields.Char(string='Work Sub Type')
    boq_qty = fields.Float(string='BOQ Qty')
    additional_qty = fields.Float(string='Add. Qty')
    rate_analysis = fields.Char(string='Rate Analysis')
    price_qty = fields.Monetary(string='Price / Qty', currency_field='currency_id')
    untaxed_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    tax_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_budget_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    material_spent = fields.Monetary(currency_field='currency_id')
    equipment_spent = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.currency_id',
        readonly=True,
    )

    @api.depends('boq_qty', 'additional_qty', 'price_qty')
    def _compute_amounts(self):
        for line in self:
            qty = line.boq_qty + line.additional_qty
            line.untaxed_amount = qty * line.price_qty
            line.tax_amount = 0.0
            line.total_budget_amount = line.untaxed_amount + line.tax_amount


class TnConstructionBudgetConfirmation(models.Model):
    _name = 'tn.construction.budget.confirmation'
    _description = 'Construction Budget Line Confirmation'
    _order = 'date desc, id desc'

    budget_id = fields.Many2one(
        'tn.construction.budget',
        required=True,
        ondelete='cascade',
    )
    action_type = fields.Selection(
        [
            ('insert', 'Insert BOQ Line'),
            ('update', 'Update BOQ Line'),
            ('delete', 'Delete BOQ Line'),
        ],
        default='insert',
        required=True,
    )
    date = fields.Date(default=fields.Date.context_today)
    requested_by_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
    )
    status = fields.Selection(
        [
            ('requested', 'Requested'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='requested',
    )


class TnConstructionRateAnalysis(models.Model):
    _name = 'tn.construction.rate.analysis'
    _description = 'Construction Rate Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        string='Sub Project',
        domain="[('project_id', '=', project_id)]",
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    date = fields.Date(default=fields.Date.context_today)
    work_type = fields.Char(required=True)
    work_sub_type = fields.Char(string='Work Sub Type')
    template = fields.Char()
    boq_type = fields.Selection(
        [
            ('qty_per_unit', 'Qty per Unit'),
            ('total_required_qty', 'Total Required Qty'),
        ],
        string='Type',
        default='qty_per_unit',
        required=True,
    )
    unit_id = fields.Many2one('uom.uom', string='Unit')
    material_available = fields.Boolean(string='Material', default=True)
    equipment_available = fields.Boolean(string='Equipment', default=True)
    labour_available = fields.Boolean(string='Labour', default=True)
    overhead_available = fields.Boolean(string='Overhead', default=True)
    resource_line_ids = fields.One2many(
        'tn.construction.rate.analysis.line',
        'rate_analysis_id',
        string='Rate Lines',
    )
    employee_hour_ids = fields.One2many(
        'tn.construction.rate.analysis.hour',
        'rate_analysis_id',
        string='Employee Hours',
    )
    material_line_ids = fields.One2many(
        'tn.construction.rate.analysis.line',
        'rate_analysis_id',
        string='Material',
        domain=[('line_type', '=', 'material')],
    )
    equipment_line_ids = fields.One2many(
        'tn.construction.rate.analysis.line',
        'rate_analysis_id',
        string='Equipment',
        domain=[('line_type', '=', 'equipment')],
    )
    labour_line_ids = fields.One2many(
        'tn.construction.rate.analysis.line',
        'rate_analysis_id',
        string='Labour',
        domain=[('line_type', '=', 'labour')],
    )
    overhead_line_ids = fields.One2many(
        'tn.construction.rate.analysis.line',
        'rate_analysis_id',
        string='Overhead',
        domain=[('line_type', '=', 'overhead')],
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    cost_untaxed_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    cost_tax_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    cost_total_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    sale_untaxed_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    sale_tax_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    sale_total_amount = fields.Monetary(
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.depends(
        'material_available',
        'equipment_available',
        'labour_available',
        'overhead_available',
        'resource_line_ids.line_type',
        'resource_line_ids.cost_untaxed_amount',
        'resource_line_ids.cost_tax_amount',
        'resource_line_ids.cost_total_amount',
        'resource_line_ids.untaxed_amount',
        'resource_line_ids.tax_amount',
        'resource_line_ids.total_amount',
    )
    def _compute_totals(self):
        for analysis in self:
            enabled_types = set()
            if analysis.material_available:
                enabled_types.add('material')
            if analysis.equipment_available:
                enabled_types.add('equipment')
            if analysis.labour_available:
                enabled_types.add('labour')
            if analysis.overhead_available:
                enabled_types.add('overhead')
            lines = analysis.resource_line_ids.filtered(
                lambda line: line.line_type in enabled_types
            )
            analysis.cost_untaxed_amount = sum(lines.mapped('cost_untaxed_amount'))
            analysis.cost_tax_amount = sum(lines.mapped('cost_tax_amount'))
            analysis.cost_total_amount = sum(lines.mapped('cost_total_amount'))
            analysis.sale_untaxed_amount = sum(lines.mapped('untaxed_amount'))
            analysis.sale_tax_amount = sum(lines.mapped('tax_amount'))
            analysis.sale_total_amount = sum(lines.mapped('total_amount'))
            analysis.total_amount = analysis.sale_total_amount

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for analysis in self:
            project = analysis.project_id
            if project:
                analysis.company_id = project.company_id

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id(self):
        for analysis in self:
            sub_project = analysis.sub_project_id
            if sub_project:
                analysis.project_id = sub_project.project_id
                analysis.company_id = sub_project.company_id


class TnConstructionRateAnalysisLine(models.Model):
    _name = 'tn.construction.rate.analysis.line'
    _description = 'Construction Rate Analysis Line'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    rate_analysis_id = fields.Many2one(
        'tn.construction.rate.analysis',
        required=True,
        ondelete='cascade',
    )
    line_type = fields.Selection(
        [
            ('material', 'Material'),
            ('equipment', 'Equipment'),
            ('labour', 'Labour'),
            ('overhead', 'Overhead'),
        ],
        required=True,
        default='material',
    )
    product_id = fields.Many2one('product.product', string='Item')
    internal_reference = fields.Char(
        related='product_id.default_code',
        string='Internal Ref.',
        readonly=False,
    )
    description = fields.Char()
    qty = fields.Float(string='Qty.', default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='UOM',
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    cost_price = fields.Monetary(currency_field='currency_id')
    sale_price = fields.Monetary(currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string='Tax')
    cost_untaxed_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    cost_tax_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    cost_total_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    untaxed_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    tax_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='rate_analysis_id.currency_id',
        readonly=True,
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            line.description = product.name
            line.uom_id = product.uom_id
            line.cost_price = product.standard_price
            line.sale_price = product.lst_price

    @api.depends('qty', 'cost_price', 'sale_price')
    def _compute_amounts(self):
        for line in self:
            line.cost_untaxed_amount = line.qty * line.cost_price
            line.cost_tax_amount = 0.0
            line.cost_total_amount = line.cost_untaxed_amount + line.cost_tax_amount
            line.untaxed_amount = line.qty * line.sale_price
            line.tax_amount = 0.0
            line.total_amount = line.untaxed_amount + line.tax_amount


class TnConstructionRateAnalysisHour(models.Model):
    _name = 'tn.construction.rate.analysis.hour'
    _description = 'Construction Rate Analysis Employee Hour'
    _order = 'date desc, id desc'

    rate_analysis_id = fields.Many2one(
        'tn.construction.rate.analysis',
        required=True,
        ondelete='cascade',
    )
    date = fields.Date(default=fields.Date.context_today)
    employee_id = fields.Many2one('res.users', string='Employee')
    phase_id = fields.Many2one(
        'project.milestone',
        string='Phase',
        domain="[('project_id', '=', parent.project_id)]",
    )
    work_order_id = fields.Many2one(
        'project.task',
        string='Work Order',
        domain="[('project_id', '=', parent.project_id)]",
    )
    hour_worked = fields.Float(string='Hour Worked')


class TnBoqLine(models.Model):
    _name = 'tn.boq.line'
    _description = 'BOQ Budget Line'
    _order = 'project_id, product_id'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    # The project's analytic account is the cost backbone every commitment ties
    # back to. Stored related so we can filter/search BOQ lines by account.
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        related='project_id.account_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='BOQ Item',
        required=True,
        index=True,
    )
    description = fields.Char(string='Description')
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        store=True,
        readonly=True,
    )

    approved_qty = fields.Float(
        string='Approved Qty',
        required=True,
        digits='Product Unit of Measure',
        help='The BOQ-approved quantity for this item on this project.',
    )
    approved_rate = fields.Float(
        string='Approved Rate (SAR)',
        digits='Product Price',
        help='Approved unit rate in SAR.',
    )
    approved_value = fields.Monetary(
        string='Approved Value',
        compute='_compute_approved_value',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='project_id.currency_id',
        readonly=True,
    )

    committed_qty = fields.Float(
        string='Committed Qty',
        compute='_compute_committed_qty',
        digits='Product Unit of Measure',
        help='Sum of confirmed purchase order line quantities for this product '
             'on POs whose analytic distribution targets this project.',
    )
    remaining_qty = fields.Float(
        string='Remaining Qty',
        compute='_compute_remaining_qty',
        search='_search_remaining_qty',
        digits='Product Unit of Measure',
        store=False,
    )
    percent_committed = fields.Float(
        string='% Committed',
        compute='_compute_remaining_qty',
        store=False,
    )

    _sql_constraints = [
        (
            'uniq_project_product',
            'unique(project_id, product_id)',
            'A BOQ line already exists for this product on this project.',
        ),
    ]

    @api.depends('approved_qty', 'approved_rate')
    def _compute_approved_value(self):
        for line in self:
            line.approved_value = line.approved_qty * line.approved_rate

    @api.depends('product_id', 'analytic_account_id')
    def _compute_committed_qty(self):
        for line in self:
            line.committed_qty = line._tn_committed_qty()

    @api.depends('approved_qty', 'committed_qty')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.approved_qty - line.committed_qty
            line.percent_committed = (
                (line.committed_qty / line.approved_qty * 100.0)
                if line.approved_qty else 0.0
            )

    def _search_remaining_qty(self, operator, value):
        """remaining_qty is non-stored (it depends on live PO commitments), so
        it can't be filtered in SQL. We compute it for all BOQ lines and return
        a domain of matching ids, which keeps the "Over Budget" filter working.
        """
        cmp_map = {
            '<': lambda c: c < 0,
            '<=': lambda c: c <= 0,
            '>': lambda c: c > 0,
            '>=': lambda c: c >= 0,
            '=': lambda c: c == 0,
            '!=': lambda c: c != 0,
        }
        if operator not in cmp_map:
            raise UserError(_(
                "Unsupported operator '%s' for Remaining Qty filter.", operator))
        keep = cmp_map[operator]
        matching = self.search([]).filtered(
            lambda line: keep(float_compare(
                line.remaining_qty, value, precision_digits=3))
        )
        return [('id', 'in', matching.ids)]

    def _tn_committed_qty(self):
        """Confirmed quantity committed for this product on this project's
        analytic account. Confirmed = PO state in ('purchase', 'done')."""
        self.ensure_one()
        if not self.product_id or not self.analytic_account_id:
            return 0.0
        pols = self.env['purchase.order.line'].search([
            ('product_id', '=', self.product_id.id),
            ('order_id.state', 'in', ('purchase', 'done')),
            ('distribution_analytic_account_ids', '=', self.analytic_account_id.id),
        ])
        # Convert each line into the BOQ UoM (product reference UoM) before
        # summing, so a PO in kg counts correctly against a BOQ in tonnes.
        return sum(pol._tn_qty_in_product_uom() for pol in pols)

    def _tn_assert_within_budget(self, added_qty, base_committed=None):
        """Raise UserError if base_committed + added_qty exceeds approved_qty.

        base_committed defaults to the line's current committed_qty (used when
        the contributing PO is not yet confirmed). When the contributing line is
        already counted in committed_qty, pass base_committed explicitly so the
        message and overage are computed against what was already committed.
        """
        self.ensure_one()
        already = self.committed_qty if base_committed is None else base_committed
        projected = already + added_qty
        rounding = self.uom_id.rounding or 0.01
        if float_compare(projected, self.approved_qty, precision_rounding=rounding) > 0:
            overage = projected - self.approved_qty
            uom = self.uom_id.name or ''
            raise UserError(_(
                "BOQ budget exceeded for %(product)s: approved %(approved).3f "
                "%(uom)s, already committed %(committed).3f, this order adds "
                "%(added).3f, which exceeds the approved BOQ quantity by "
                "%(overage).3f %(uom)s. Raise a Variation Order to proceed.",
                product=self.product_id.display_name,
                approved=self.approved_qty,
                uom=uom,
                committed=already,
                added=added_qty,
                overage=overage,
            ))

    @api.model
    def _tn_find(self, product_id, analytic_account_id):
        """Return the BOQ line governing this product+analytic account, if any."""
        if not product_id or not analytic_account_id:
            return self.browse()
        return self.search([
            ('product_id', '=', product_id),
            ('analytic_account_id', '=', analytic_account_id),
        ], limit=1)
