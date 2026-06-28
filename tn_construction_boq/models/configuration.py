from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_construction_material = fields.Boolean(string='Is Material')
    is_construction_equipment = fields.Boolean(string='Is Equipment')
    is_construction_labour = fields.Boolean(string='Is Labour')
    is_construction_overhead = fields.Boolean(string='Is Overhead')
    is_construction_expense = fields.Boolean(string='Is Expense')


class TnConstructionWorkSubType(models.Model):
    _name = 'tn.construction.work.sub.type'
    _description = 'Construction Work Sub Type'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Title', required=True)
    active = fields.Boolean(default=True)


class TnConstructionWorkType(models.Model):
    _name = 'tn.construction.work.type'
    _description = 'Construction Work Type'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Title', required=True)
    sub_type_ids = fields.Many2many(
        'tn.construction.work.sub.type',
        'tn_construction_work_type_sub_type_rel',
        'work_type_id',
        'sub_type_id',
        string='Work Sub Type',
    )
    active = fields.Boolean(default=True)


class TnConstructionDocumentType(models.Model):
    _name = 'tn.construction.document.type'
    _description = 'Construction Document Type'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Title', required=True)
    active = fields.Boolean(default=True)


class TnConstructionInsuranceRisk(models.Model):
    _name = 'tn.construction.insurance.risk'
    _description = 'Construction Insurance Risk'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Title', required=True)
    active = fields.Boolean(default=True)


class TnConstructionEmployeeTag(models.Model):
    _name = 'tn.construction.employee.tag'
    _description = 'Construction Employee Tag'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Title', required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)


class TnConstructionRateAnalysisTemplate(models.Model):
    _name = 'tn.construction.rate.analysis.template'
    _description = 'Construction Rate Analysis Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Title', required=True, tracking=True)
    work_type_id = fields.Many2one('tn.construction.work.type', string='Work Type', required=True)
    work_sub_type_id = fields.Many2one('tn.construction.work.sub.type', string='Work Sub Type')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    unit_id = fields.Many2one(
        'uom.uom',
        string='Unit',
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    material_available = fields.Boolean(string='Material', default=True)
    equipment_available = fields.Boolean(string='Equipment', default=True)
    labour_available = fields.Boolean(string='Labour', default=True)
    overhead_available = fields.Boolean(string='Overhead', default=True)
    material_line_ids = fields.One2many(
        'tn.construction.rate.analysis.template.line',
        'template_id',
        string='Material',
        domain=[('line_type', '=', 'material')],
    )
    equipment_line_ids = fields.One2many(
        'tn.construction.rate.analysis.template.line',
        'template_id',
        string='Equipment',
        domain=[('line_type', '=', 'equipment')],
    )
    labour_line_ids = fields.One2many(
        'tn.construction.rate.analysis.template.line',
        'template_id',
        string='Labour',
        domain=[('line_type', '=', 'labour')],
    )
    overhead_line_ids = fields.One2many(
        'tn.construction.rate.analysis.template.line',
        'template_id',
        string='Overhead',
        domain=[('line_type', '=', 'overhead')],
    )
    untaxed_amount = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    tax_amount = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    total_amount = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends(
        'material_line_ids.total_amount', 'equipment_line_ids.total_amount',
        'labour_line_ids.total_amount', 'overhead_line_ids.total_amount',
        'material_line_ids.untaxed_amount', 'equipment_line_ids.untaxed_amount',
        'labour_line_ids.untaxed_amount', 'overhead_line_ids.untaxed_amount',
        'material_line_ids.tax_amount', 'equipment_line_ids.tax_amount',
        'labour_line_ids.tax_amount', 'overhead_line_ids.tax_amount',
    )
    def _compute_totals(self):
        for template in self:
            lines = (
                template.material_line_ids
                | template.equipment_line_ids
                | template.labour_line_ids
                | template.overhead_line_ids
            )
            template.untaxed_amount = sum(lines.mapped('untaxed_amount'))
            template.tax_amount = sum(lines.mapped('tax_amount'))
            template.total_amount = sum(lines.mapped('total_amount'))


class TnConstructionRateAnalysisTemplateLine(models.Model):
    _name = 'tn.construction.rate.analysis.template.line'
    _description = 'Construction Rate Analysis Template Line'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'tn.construction.rate.analysis.template',
        required=True,
        ondelete='cascade',
    )
    line_type = fields.Selection(
        [('material', 'Material'), ('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        required=True,
        default='material',
    )
    product_id = fields.Many2one('product.product', string='Item')
    internal_reference = fields.Char(related='product_id.default_code', string='Internal Reference', readonly=False)
    description = fields.Char()
    qty = fields.Float(string='Qty.', default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='UOM',
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    sale_price = fields.Monetary(string='Sale Price', currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string='Tax')
    untaxed_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    tax_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    total_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='template_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            line.description = product.name
            line.uom_id = product.uom_id
            line.sale_price = product.lst_price

    @api.depends('qty', 'sale_price')
    def _compute_amounts(self):
        for line in self:
            line.untaxed_amount = line.qty * line.sale_price
            line.tax_amount = 0.0
            line.total_amount = line.untaxed_amount + line.tax_amount
