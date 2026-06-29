from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class TnConstructionPhase(models.Model):
    _name = 'tn.construction.phase'
    _description = 'Construction Project Phase WBS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence_code desc, id desc'

    sequence_code = fields.Char(string='Sequence', required=True, default='New')
    name = fields.Char(string='Title', required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        string='Sub Project',
        domain="[('project_id', '=', project_id)]",
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    start_date = fields.Date()
    end_date = fields.Date()
    work_type = fields.Char()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('in_progress', 'In Progress'),
            ('complete', 'Complete'),
        ],
        default='draft',
        tracking=True,
    )
    material_line_ids = fields.One2many(
        'tn.construction.phase.line', 'phase_id', string='Materials',
        domain=[('line_type', '=', 'material')],
    )
    equipment_line_ids = fields.One2many(
        'tn.construction.phase.line', 'phase_id', string='Equipments',
        domain=[('line_type', '=', 'equipment')],
    )
    labour_line_ids = fields.One2many(
        'tn.construction.phase.line', 'phase_id', string='Labours',
        domain=[('line_type', '=', 'labour')],
    )
    overhead_line_ids = fields.One2many(
        'tn.construction.phase.line', 'phase_id', string='Overheads',
        domain=[('line_type', '=', 'overhead')],
    )
    work_order_count = fields.Integer(compute='_compute_counts')
    material_request_count = fields.Integer(compute='_compute_counts')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for phase in self:
            if phase.project_id:
                phase.company_id = phase.project_id.company_id

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id(self):
        for phase in self:
            if phase.sub_project_id:
                phase.project_id = phase.sub_project_id.project_id
                phase.company_id = phase.sub_project_id.company_id
                phase.start_date = phase.sub_project_id.schedule_start_date
                phase.end_date = phase.sub_project_id.schedule_end_date

    def _compute_counts(self):
        WorkOrder = self.env['tn.construction.work.order']
        MaterialRequest = self.env['tn.construction.material.request']
        for phase in self:
            phase.work_order_count = WorkOrder.search_count([('phase_id', '=', phase.id)])
            phase.material_request_count = MaterialRequest.search_count([('phase_id', '=', phase.id)])

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'complete'})

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'tn.construction.work.order',
            'view_mode': 'list,form',
            'domain': [('phase_id', '=', self.id)],
            'context': {
                'default_phase_id': self.id,
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.sub_project_id.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': (
                    self.sub_project_id.project_warehouse_id.id
                    or self.project_id.project_warehouse_id.id
                ),
            },
        }

    def action_view_material_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'tn.construction.material.request',
            'view_mode': 'list,form',
            'domain': [('phase_id', '=', self.id)],
            'context': {
                'default_phase_id': self.id,
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.sub_project_id.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': (
                    self.sub_project_id.project_warehouse_id.id
                    or self.project_id.project_warehouse_id.id
                ),
            },
        }


class TnConstructionPhaseLine(models.Model):
    _name = 'tn.construction.phase.line'
    _description = 'Construction Project Phase Line'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    phase_id = fields.Many2one('tn.construction.phase', required=True, ondelete='cascade')
    line_type = fields.Selection(
        [('material', 'Material'), ('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        required=True,
        default='material',
    )
    work_sub_type = fields.Char(string='Work Sub Type')
    product_id = fields.Many2one('product.product', string='Product')
    equipment_type = fields.Char(string='Type')
    description = fields.Char()
    budget_qty = fields.Float(string='Budget Qty.')
    qty = fields.Float(string='Qty.')
    hours = fields.Float()
    forecast_qty = fields.Float(string='Forecast Qty.')
    forecast_hours = fields.Float(string='Forecast Hours')
    remain_qty = fields.Float(string='Remain Qty.', compute='_compute_remaining', store=True)
    remain_hours = fields.Float(string='Remain Hours', compute='_compute_remaining', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost_unit = fields.Monetary(string='Cost / Unit', currency_field='currency_id')
    cost_hour = fields.Monetary(string='Cost / Hour', currency_field='currency_id')
    taxes = fields.Char()
    estimation_cost = fields.Monetary(compute='_compute_costs', store=True, currency_field='currency_id')
    total_cost = fields.Monetary(compute='_compute_costs', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='phase_id.company_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if product:
                line.description = product.name
                line.uom_id = product.uom_id
                line.cost_unit = product.standard_price
                line.cost_hour = product.standard_price

    @api.depends('qty', 'forecast_qty', 'hours', 'forecast_hours')
    def _compute_remaining(self):
        for line in self:
            line.remain_qty = line.qty - line.forecast_qty
            line.remain_hours = line.hours - line.forecast_hours

    @api.depends('qty', 'hours', 'cost_unit', 'cost_hour')
    def _compute_costs(self):
        for line in self:
            if line.line_type == 'labour':
                line.estimation_cost = line.hours * line.cost_hour
            else:
                line.estimation_cost = line.qty * line.cost_unit
            line.total_cost = line.estimation_cost


class TnConstructionWorkOrder(models.Model):
    _name = 'tn.construction.work.order'
    _description = 'Construction Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence_code desc, id desc'

    sequence_code = fields.Char(string='Sequence', required=True, default='New')
    name = fields.Char(string='Title', required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    sub_project_id = fields.Many2one('tn.construction.sub.project', domain="[('project_id', '=', project_id)]")
    phase_id = fields.Many2one('tn.construction.phase', string='Project Phase(WBS)', domain="[('project_id', '=', project_id)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    warehouse_id = fields.Many2one('res.company', string='Warehouse', default=lambda self: self.env.company)
    project_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Project Warehouse',
        domain="[('company_id', 'in', [company_id, False])]",
        help='Default warehouse used for material movements, receipts, issues, and returns related to this project.',
    )
    start_date = fields.Date()
    end_date = fields.Date()
    work_type = fields.Char()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('material_requested', 'Material Requested'),
            ('material_arrived', 'Material Arrived'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='draft',
        tracking=True,
    )
    task_project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    task_title = fields.Char()
    assignee_ids = fields.Many2many('res.users', string='Assignees')
    description = fields.Text()
    timesheet_hours = fields.Float(string='Timesheet Hours', compute='_compute_counts')
    material_request_count = fields.Integer(compute='_compute_counts')
    subcontract_count = fields.Integer(compute='_compute_counts')
    material_line_ids = fields.One2many('tn.construction.work.order.line', 'work_order_id', string='Required Materials', domain=[('line_type', '=', 'material')])
    equipment_line_ids = fields.One2many('tn.construction.work.order.line', 'work_order_id', string='Required Equipments', domain=[('line_type', '=', 'equipment')])
    labour_line_ids = fields.One2many('tn.construction.work.order.line', 'work_order_id', string='Required Labours', domain=[('line_type', '=', 'labour')])
    overhead_line_ids = fields.One2many('tn.construction.work.order.line', 'work_order_id', string='Required Overheads', domain=[('line_type', '=', 'overhead')])

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for order in self:
            if order.project_id:
                order.company_id = order.project_id.company_id
                order.warehouse_id = order.project_id.warehouse_id or order.project_id.company_id
                order.project_warehouse_id = order.project_id.project_warehouse_id

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id(self):
        for order in self:
            if order.sub_project_id:
                order.project_id = order.sub_project_id.project_id
                order.company_id = order.sub_project_id.company_id
                order.warehouse_id = order.sub_project_id.warehouse_id or order.sub_project_id.company_id
                order.project_warehouse_id = (
                    order.sub_project_id.project_warehouse_id
                    or order.project_id.project_warehouse_id
                )

    @api.constrains('project_warehouse_id', 'company_id')
    def _check_project_warehouse_company(self):
        for order in self:
            warehouse_company = order.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != order.company_id:
                raise ValidationError(
                    _('The Project Warehouse must belong to the same company as the project.')
                )

    @api.onchange('company_id')
    def _onchange_company_id_project_warehouse(self):
        for order in self:
            warehouse_company = order.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != order.company_id:
                order.project_warehouse_id = False

    def _compute_counts(self):
        MaterialRequest = self.env['tn.construction.material.request']
        for order in self:
            order.material_request_count = MaterialRequest.search_count([('work_order_id', '=', order.id)])
            order.subcontract_count = len(order.equipment_line_ids) + len(order.labour_line_ids) + len(order.overhead_line_ids)
            order.timesheet_hours = sum(order.labour_line_ids.mapped('hours'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project = self.env['project.project'].browse(vals.get('project_id'))
            sub_project = self.env['tn.construction.sub.project'].browse(vals.get('sub_project_id'))
            if sub_project:
                project = sub_project.project_id
                vals.setdefault('project_id', project.id)
                vals.setdefault('company_id', sub_project.company_id.id)
                vals.setdefault('warehouse_id', (sub_project.warehouse_id or sub_project.company_id).id)
                vals.setdefault(
                    'project_warehouse_id',
                    (sub_project.project_warehouse_id or project.project_warehouse_id).id,
                )
            elif project:
                vals.setdefault('company_id', project.company_id.id)
                vals.setdefault('warehouse_id', (project.warehouse_id or project.company_id).id)
                vals.setdefault('project_warehouse_id', project.project_warehouse_id.id)
        return super().create(vals_list)

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_create_material_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Material Requisition'),
            'res_model': 'tn.construction.material.request',
            'view_mode': 'form',
            'context': {
                'default_work_order_id': self.id,
                'default_phase_id': self.phase_id.id,
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.sub_project_id.id,
                'default_work_type': self.work_type,
                'default_project_warehouse_id': self.project_warehouse_id.id,
            },
        }

    def action_view_material_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'tn.construction.material.request',
            'view_mode': 'list,form',
            'domain': [('work_order_id', '=', self.id)],
            'context': {'default_work_order_id': self.id},
        }

    def action_create_subcontract(self):
        self.ensure_one()
        return self.action_create_equipment_subcontracts()

    def action_view_subcontracts(self):
        self.ensure_one()
        return self.action_view_equipment_subcontracts()

    def _get_subcontract_action(self, contract_kind):
        self.ensure_one()
        action_xmlids = {
            'equipment': 'tn_construction_boq.action_tn_construction_equipment_subcontract',
            'labour': 'tn_construction_boq.action_tn_construction_labour_subcontract',
            'overhead': 'tn_construction_boq.action_tn_construction_overhead_subcontract',
        }
        action = self.env['ir.actions.act_window']._for_xml_id(action_xmlids[contract_kind])
        action['domain'] = [('work_order_id', '=', self.id), ('contract_kind', '=', contract_kind)]
        action_context = action.get('context') or {}
        context = safe_eval(action_context) if isinstance(action_context, str) else dict(action_context)
        context.update({
            'default_work_order_id': self.id,
            'default_project_id': self.project_id.id,
            'default_sub_project_id': self.sub_project_id.id,
            'default_phase_id': self.phase_id.id,
            'default_task_id': self.task_id.id,
            'default_company_id': self.company_id.id,
            'default_work_type': self.work_type,
            'default_contract_kind': contract_kind,
        })
        action['context'] = context
        return action

    def _create_subcontracts_from_lines(self, contract_kind):
        self.ensure_one()
        lines = self.env['tn.construction.work.order.line'].search([
            ('work_order_id', '=', self.id),
            ('line_type', '=', contract_kind),
        ])
        Subcontract = self.env['tn.construction.subcontract']
        for line in lines:
            existing = Subcontract.search([
                ('work_order_line_id', '=', line.id),
                ('contract_kind', '=', contract_kind),
            ], limit=1)
            if existing:
                continue
            Subcontract.create({
                'contract_kind': contract_kind,
                'title': line.description or line.product_id.display_name or self.name,
                'company_id': self.company_id.id,
                'project_id': self.project_id.id,
                'sub_project_id': self.sub_project_id.id,
                'phase_id': self.phase_id.id,
                'work_order_id': self.id,
                'work_order_line_id': line.id,
                'task_id': self.task_id.id,
                'vendor_id': line.vendor_id.id,
                'product_id': line.product_id.id,
                'work_type': self.work_type,
                'work_sub_type': line.work_sub_type,
                'equipment_type': line.equipment_type,
                'qty': line.qty,
                'hours': line.hours,
                'uom_id': line.uom_id.id,
                'cost_unit': line.cost_unit or line.price,
                'cost_hour': line.cost_hour,
            })

    def action_create_equipment_subcontracts(self):
        self._create_subcontracts_from_lines('equipment')
        return self.action_view_equipment_subcontracts()

    def action_view_equipment_subcontracts(self):
        return self._get_subcontract_action('equipment')

    def action_create_labour_subcontracts(self):
        self._create_subcontracts_from_lines('labour')
        return self.action_view_labour_subcontracts()

    def action_view_labour_subcontracts(self):
        return self._get_subcontract_action('labour')

    def action_create_overhead_subcontracts(self):
        self._create_subcontracts_from_lines('overhead')
        return self.action_view_overhead_subcontracts()

    def action_view_overhead_subcontracts(self):
        return self._get_subcontract_action('overhead')


class TnConstructionSubcontract(models.Model):
    _name = 'tn.construction.subcontract'
    _description = 'Construction Subcontract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sequence_code'
    _order = 'sequence_code desc, id desc'

    sequence_code = fields.Char(string='Sequence', required=True, default='New', copy=False)
    contract_kind = fields.Selection(
        [('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        required=True,
        default='equipment',
        tracking=True,
    )
    title = fields.Char(required=True, tracking=True)
    procurement_type = fields.Selection(
        [('bill', 'Bill'), ('po', 'Purchase Order')],
        string='Type',
        default='bill',
        required=True,
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    sub_project_id = fields.Many2one('tn.construction.sub.project', domain="[('project_id', '=', project_id)]")
    phase_id = fields.Many2one('tn.construction.phase', string='Project Phase(WBS)', domain="[('project_id', '=', project_id)]")
    work_order_id = fields.Many2one('tn.construction.work.order', string='Work Order', domain="[('project_id', '=', project_id)]")
    work_order_line_id = fields.Many2one('tn.construction.work.order.line', string='Work Order Line', copy=False)
    task_id = fields.Many2one('project.task', string='Task')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    product_id = fields.Many2one('product.product', string='Product')
    work_type = fields.Char()
    work_sub_type = fields.Char(string='Work Sub Type')
    equipment_type = fields.Char(string='Type')
    qty = fields.Float(string='Qty.')
    hours = fields.Float()
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost_unit = fields.Monetary(string='Cost / Unit', currency_field='currency_id')
    cost_hour = fields.Monetary(string='Cost / Hour', currency_field='currency_id')
    estimation_cost = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    total_cost = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    billed_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    remaining_qty = fields.Float(compute='_compute_amounts', store=True)
    remaining_hours = fields.Float(compute='_compute_amounts', store=True)
    remaining_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    completed_bill_percent = fields.Float(string='Completed Bill', compute='_compute_amounts', store=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')],
        default='in_progress',
        tracking=True,
    )
    bill_line_ids = fields.One2many('tn.construction.subcontract.bill.line', 'subcontract_id', string='Subcontract Bills/PO')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequence_codes = {
            'equipment': 'tn.construction.equipment.subcontract',
            'labour': 'tn.construction.labour.subcontract',
            'overhead': 'tn.construction.overhead.subcontract',
        }
        for vals in vals_list:
            if vals.get('sequence_code', 'New') == 'New':
                contract_kind = vals.get('contract_kind') or 'equipment'
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code(sequence_codes[contract_kind]) or 'New'
        return super().create(vals_list)

    @api.onchange('work_order_id')
    def _onchange_work_order_id(self):
        for contract in self:
            order = contract.work_order_id
            if not order:
                continue
            contract.project_id = order.project_id
            contract.sub_project_id = order.sub_project_id
            contract.phase_id = order.phase_id
            contract.task_id = order.task_id
            contract.company_id = order.company_id
            contract.work_type = order.work_type

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for contract in self:
            product = contract.product_id
            if not product:
                continue
            if not contract.title:
                contract.title = product.display_name
            contract.uom_id = product.uom_id
            contract.cost_unit = product.standard_price
            contract.cost_hour = product.standard_price

    @api.depends(
        'contract_kind', 'qty', 'hours', 'cost_unit', 'cost_hour',
        'bill_line_ids.qty', 'bill_line_ids.hours', 'bill_line_ids.total_amount',
    )
    def _compute_amounts(self):
        for contract in self:
            total = contract.hours * contract.cost_hour if contract.contract_kind == 'labour' else contract.qty * contract.cost_unit
            billed_qty = sum(contract.bill_line_ids.mapped('qty'))
            billed_hours = sum(contract.bill_line_ids.mapped('hours'))
            billed_amount = sum(contract.bill_line_ids.mapped('total_amount'))
            contract.estimation_cost = total
            contract.total_cost = total
            contract.billed_amount = billed_amount
            contract.remaining_qty = contract.qty - billed_qty
            contract.remaining_hours = contract.hours - billed_hours
            contract.remaining_amount = total - billed_amount
            contract.completed_bill_percent = (billed_amount / total * 100.0) if total else 0.0

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class TnConstructionSubcontractBillLine(models.Model):
    _name = 'tn.construction.subcontract.bill.line'
    _description = 'Construction Subcontract Bill Line'
    _order = 'date, id'

    subcontract_id = fields.Many2one('tn.construction.subcontract', required=True, ondelete='cascade')
    contract_kind = fields.Selection(related='subcontract_id.contract_kind', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    qty = fields.Float(string='Qty.')
    hours = fields.Float()
    percentage = fields.Float()
    amount = fields.Monetary(currency_field='currency_id')
    retention_percent = fields.Float(string='Retention(%)')
    retention_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    total_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    remark = fields.Char()
    bill_id = fields.Many2one('account.move', string='Bill')
    payment_state = fields.Selection(
        [('draft', 'Draft'), ('department', 'Department'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Payment Status',
        default='department',
    )
    quality_check = fields.Char(string='Quality Check')
    quality_check_id = fields.Many2one('tn.construction.quality.check', string='Quality Check', copy=False)
    currency_id = fields.Many2one('res.currency', related='subcontract_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ensure_quality_checks()
        return lines

    def write(self, vals):
        result = super().write(vals)
        self._ensure_quality_checks()
        return result

    def _ensure_quality_checks(self):
        QualityCheck = self.env['tn.construction.quality.check']
        for line in self:
            if line.quality_check_id or not line.subcontract_id:
                continue
            line.quality_check_id = QualityCheck.create({
                'check_kind': line.subcontract_id.contract_kind,
                'subcontract_id': line.subcontract_id.id,
                'subcontract_bill_line_id': line.id,
                'company_id': line.subcontract_id.company_id.id,
                'date': line.date,
                'qty': line.qty,
                'hours': line.hours,
                'percentage': line.percentage,
                'amount': line.amount,
                'retention_percent': line.retention_percent,
                'retention_amount': line.retention_amount,
                'total_amount': line.total_amount,
                'remark': line.remark,
            })

    @api.onchange('qty', 'hours', 'percentage')
    def _onchange_progress(self):
        for line in self:
            contract = line.subcontract_id
            if not contract:
                continue
            if contract.contract_kind == 'labour':
                line.amount = line.hours * contract.cost_hour
                if contract.hours and line.hours:
                    line.percentage = line.hours / contract.hours * 100.0
            else:
                line.amount = line.qty * contract.cost_unit
                if contract.qty and line.qty:
                    line.percentage = line.qty / contract.qty * 100.0

    @api.depends('amount', 'retention_percent')
    def _compute_amounts(self):
        for line in self:
            line.retention_amount = line.amount * line.retention_percent / 100.0
            line.total_amount = line.amount - line.retention_amount

    def action_approve(self):
        self.write({'payment_state': 'approved'})

    def action_reject(self):
        self.write({'payment_state': 'rejected'})


class TnConstructionQualityCheck(models.Model):
    _name = 'tn.construction.quality.check'
    _description = 'Construction Quality Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    check_kind = fields.Selection(
        [('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead'), ('material', 'Material')],
        required=True,
        default='equipment',
        tracking=True,
    )
    subcontract_id = fields.Many2one('tn.construction.subcontract', string='Subcontract', ondelete='cascade')
    subcontract_bill_line_id = fields.Many2one('tn.construction.subcontract.bill.line', string='Subcontract Bill/PO Line', ondelete='cascade')
    material_request_line_id = fields.Many2one('tn.construction.material.request.line', string='Material Line', ondelete='cascade')
    material_request_id = fields.Many2one(related='material_request_line_id.request_id', store=True, string='Material Request')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date = fields.Date(default=fields.Date.context_today)
    qty = fields.Float(string='Qty.')
    hours = fields.Float()
    percentage = fields.Float()
    amount = fields.Monetary(currency_field='currency_id')
    retention_percent = fields.Float(string='Retention(%)')
    retention_amount = fields.Monetary(currency_field='currency_id')
    total_amount = fields.Monetary(currency_field='currency_id')
    remark = fields.Char()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='department_approval',
        string='Quality Check Status',
        tracking=True,
    )
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends(
        'subcontract_id.sequence_code',
        'subcontract_id.work_order_id.sequence_code',
        'material_request_id.sequence_code',
        'material_request_line_id.product_id',
        'material_request_line_id.material_id',
    )
    def _compute_name(self):
        for check in self:
            if check.subcontract_id:
                work_order = check.subcontract_id.work_order_id.sequence_code
                subcontract = check.subcontract_id.sequence_code
                check.name = '%s-%s' % (work_order, subcontract) if work_order else subcontract
            elif check.material_request_line_id:
                product = check.material_request_line_id.product_id or check.material_request_line_id.material_id
                parts = [check.material_request_id.sequence_code, product.display_name]
                check.name = ' - '.join(part for part in parts if part)
            else:
                check.name = _('Quality Check')

    def action_submit_department(self):
        self.write({'state': 'department_approval'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class TnConstructionWorkOrderLine(models.Model):
    _name = 'tn.construction.work.order.line'
    _description = 'Construction Work Order Requirement'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    work_order_id = fields.Many2one('tn.construction.work.order', required=True, ondelete='cascade')
    line_type = fields.Selection(
        [('material', 'Material'), ('equipment', 'Equipment'), ('labour', 'Labour'), ('overhead', 'Overhead')],
        required=True,
        default='material',
    )
    work_sub_type = fields.Char(string='Work Sub Type')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    product_id = fields.Many2one('product.product', string='Product')
    equipment_type = fields.Char(string='Type')
    description = fields.Char()
    qty = fields.Float(string='Qty.')
    used_qty = fields.Float(string='Used Qty.')
    remain_qty = fields.Float(string='Remain Qty.', compute='_compute_remaining', store=True)
    hours = fields.Float()
    remaining_hours = fields.Float(compute='_compute_remaining', store=True)
    uom_id = fields.Many2one('uom.uom', string='UOM')
    price = fields.Monetary(currency_field='currency_id')
    cost_hour = fields.Monetary(string='Cost / Hour', currency_field='currency_id')
    cost_unit = fields.Monetary(string='Cost / Unit', currency_field='currency_id')
    taxes = fields.Char()
    total_price = fields.Monetary(compute='_compute_total', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='work_order_id.company_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if product:
                line.description = product.name
                line.uom_id = product.uom_id
                line.price = product.standard_price
                line.cost_unit = product.standard_price
                line.cost_hour = product.standard_price

    @api.depends('qty', 'used_qty', 'hours')
    def _compute_remaining(self):
        for line in self:
            line.remain_qty = line.qty - line.used_qty
            line.remaining_hours = line.hours

    @api.depends('qty', 'hours', 'price', 'cost_unit', 'cost_hour')
    def _compute_total(self):
        for line in self:
            if line.line_type == 'labour':
                line.total_price = line.hours * line.cost_hour
            elif line.line_type in ('equipment', 'overhead'):
                line.total_price = line.qty * line.cost_unit
            else:
                line.total_price = line.qty * line.price


class TnConstructionMaterialRequest(models.Model):
    _name = 'tn.construction.material.request'
    _description = 'Construction Material Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence_code desc, id desc'

    sequence_code = fields.Char(string='Sequence', required=True, default='New')
    name = fields.Char(string='Title', required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    sub_project_id = fields.Many2one('tn.construction.sub.project', domain="[('project_id', '=', project_id)]")
    warehouse_id = fields.Many2one('res.company', string='Warehouse', default=lambda self: self.env.company)
    project_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Project Warehouse',
        domain="[('company_id', 'in', [company_id, False])]",
        help='Default warehouse used for material movements, receipts, issues, and returns related to this project.',
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date = fields.Datetime(default=fields.Datetime.now)
    created_by_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    department_manager_id = fields.Many2one('res.users', string='Department Manager')
    work_type = fields.Char()
    work_order_id = fields.Many2one('tn.construction.work.order', string='Work Order')
    phase_id = fields.Many2one('tn.construction.phase', string='Project Phase(WBS)')
    state = fields.Selection(
        [
            ('waiting_department_approval', 'Waiting Department Approval'),
            ('in_progress', 'In Progress'),
            ('ready_delivery', 'Ready for Delivery'),
            ('internal_transfer', 'Internal Transfer'),
            ('done', 'Done'),
        ],
        default='in_progress',
        tracking=True,
    )
    material_line_ids = fields.One2many('tn.construction.material.request.line', 'request_id', string='Material Requisition', domain=[('line_type', '=', 'requisition')])
    purchase_line_ids = fields.One2many('tn.construction.material.request.line', 'request_id', string='Material Purchase', domain=[('line_type', '=', 'purchase')])
    transfer_line_ids = fields.One2many('tn.construction.material.request.line', 'request_id', string='Internal Transfer', domain=[('line_type', '=', 'transfer')])
    description = fields.Text()

    @api.onchange('work_order_id')
    def _onchange_work_order_id(self):
        for request in self:
            order = request.work_order_id
            if order:
                request.project_id = order.project_id
                request.sub_project_id = order.sub_project_id
                request.phase_id = order.phase_id
                request.company_id = order.company_id
                request.warehouse_id = order.warehouse_id
                request.project_warehouse_id = (
                    order.project_warehouse_id
                    or order.project_id.project_warehouse_id
                )
                request.work_type = order.work_type

    @api.onchange('project_id')
    def _onchange_project_id_project_warehouse(self):
        for request in self:
            if request.project_id:
                request.company_id = request.project_id.company_id
                request.warehouse_id = request.project_id.warehouse_id or request.project_id.company_id
                request.project_warehouse_id = request.project_id.project_warehouse_id

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id_project_warehouse(self):
        for request in self:
            if request.sub_project_id:
                request.project_id = request.sub_project_id.project_id
                request.company_id = request.sub_project_id.company_id
                request.warehouse_id = request.sub_project_id.warehouse_id or request.sub_project_id.company_id
                request.project_warehouse_id = (
                    request.sub_project_id.project_warehouse_id
                    or request.project_id.project_warehouse_id
                )

    @api.constrains('project_warehouse_id', 'company_id')
    def _check_project_warehouse_company(self):
        for request in self:
            warehouse_company = request.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != request.company_id:
                raise ValidationError(
                    _('The Project Warehouse must belong to the same company as the project.')
                )

    @api.onchange('company_id')
    def _onchange_company_id_project_warehouse(self):
        for request in self:
            warehouse_company = request.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != request.company_id:
                request.project_warehouse_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['tn.construction.work.order'].browse(vals.get('work_order_id'))
            project = self.env['project.project'].browse(vals.get('project_id'))
            sub_project = self.env['tn.construction.sub.project'].browse(vals.get('sub_project_id'))
            if order:
                project = order.project_id
                vals.setdefault('project_id', project.id)
                vals.setdefault('sub_project_id', order.sub_project_id.id)
                vals.setdefault('phase_id', order.phase_id.id)
                vals.setdefault('company_id', order.company_id.id)
                vals.setdefault('warehouse_id', order.warehouse_id.id)
                vals.setdefault(
                    'project_warehouse_id',
                    (order.project_warehouse_id or project.project_warehouse_id).id,
                )
                vals.setdefault('work_type', order.work_type)
            elif sub_project:
                project = sub_project.project_id
                vals.setdefault('project_id', project.id)
                vals.setdefault('company_id', sub_project.company_id.id)
                vals.setdefault('warehouse_id', (sub_project.warehouse_id or sub_project.company_id).id)
                vals.setdefault(
                    'project_warehouse_id',
                    (sub_project.project_warehouse_id or project.project_warehouse_id).id,
                )
            elif project:
                vals.setdefault('company_id', project.company_id.id)
                vals.setdefault('warehouse_id', (project.warehouse_id or project.company_id).id)
                vals.setdefault('project_warehouse_id', project.project_warehouse_id.id)
        return super().create(vals_list)

    def action_create_po(self):
        self.ensure_one()
        context = {'default_origin': self.sequence_code}
        if self.project_warehouse_id.in_type_id:
            context['default_picking_type_id'] = self.project_warehouse_id.in_type_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'context': context,
        }


class TnConstructionMaterialRequestLine(models.Model):
    _name = 'tn.construction.material.request.line'
    _description = 'Construction Material Requisition Line'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one('tn.construction.material.request', required=True, ondelete='cascade')
    line_type = fields.Selection(
        [('requisition', 'Material Requisition'), ('purchase', 'Material Purchase'), ('transfer', 'Internal Transfer')],
        required=True,
        default='requisition',
    )
    work_sub_type = fields.Char(string='Work Sub Type')
    product_id = fields.Many2one('product.product', string='Product')
    material_id = fields.Many2one('product.product', string='Material')
    description = fields.Char()
    qty = fields.Float(string='Qty.')
    forecast_qty = fields.Float(string='Forecast Qty.')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    pickup_delivery = fields.Char(string='Pickup / Delivery')
    operation = fields.Char()
    price = fields.Monetary(currency_field='currency_id')
    total_price = fields.Monetary(compute='_compute_total', store=True, currency_field='currency_id')
    delivery_warehouse_id = fields.Many2one('res.company', string='Delivery Warehouse')
    picking_warehouse_id = fields.Many2one('res.company', string='Picking Warehouse')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    quality_check_id = fields.Many2one('tn.construction.quality.check', string='Quality Check', copy=False)
    currency_id = fields.Many2one('res.currency', related='request_id.company_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._ensure_material_quality_checks()
        return lines

    def write(self, vals):
        result = super().write(vals)
        self._ensure_material_quality_checks()
        return result

    def _ensure_material_quality_checks(self):
        QualityCheck = self.env['tn.construction.quality.check']
        for line in self:
            if line.quality_check_id or not line.request_id:
                continue
            line.quality_check_id = QualityCheck.create({
                'check_kind': 'material',
                'material_request_line_id': line.id,
                'company_id': line.request_id.company_id.id,
                'date': line.request_id.date.date() if line.request_id.date else fields.Date.context_today(line),
                'qty': line.qty,
                'amount': line.total_price,
                'total_amount': line.total_price,
                'remark': line.description,
            })

    @api.onchange('product_id', 'material_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id or line.material_id
            if product:
                line.description = product.name
                line.uom_id = product.uom_id
                line.price = product.standard_price

    @api.depends('qty', 'price')
    def _compute_total(self):
        for line in self:
            line.total_price = line.qty * line.price
