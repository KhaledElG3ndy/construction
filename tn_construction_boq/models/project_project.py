from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    construction_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='Construction Status',
        default='draft',
        tracking=True,
    )
    warehouse_id = fields.Many2one(
        'res.company',
        string='Warehouse',
        default=lambda self: self.env.company,
    )
    project_code = fields.Char(string='Project Code', copy=False)
    contract_reference = fields.Char(string='Contract Reference')
    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id',
    )
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    project_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Project Warehouse',
        domain="[('company_id', 'in', [company_id, False])]",
        help='Default warehouse used for material movements, receipts, issues, and returns related to this project.',
    )
    address_street = fields.Char(string='Street')
    address_street2 = fields.Char(string='Street 2')
    address_city = fields.Char(string='City')
    address_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id', '=?', address_country_id)]",
    )
    address_zip = fields.Char(string='ZIP')
    address_country_id = fields.Many2one('res.country', string='Country')
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    progress_percent = fields.Float(
        string='Progress',
        compute='_compute_progress_percent',
        store=True,
    )
    boq_line_ids = fields.One2many(
        'tn.boq.line',
        'project_id',
        string='BOQ Lines',
    )
    boq_line_count = fields.Integer(
        string='BOQ Lines',
        compute='_compute_boq_line_count',
    )
    construction_sub_project_ids = fields.One2many(
        'tn.construction.sub.project',
        'project_id',
        string='Sub Projects',
    )
    stakeholder_ids = fields.One2many(
        'tn.construction.stakeholder',
        'project_id',
        string='Stakeholders',
    )
    site_image_ids = fields.One2many(
        'tn.construction.site.image',
        'project_id',
        string='Images',
    )
    measurement_ids = fields.One2many(
        'tn.construction.measurement',
        'project_id',
        string='Project Measurements',
    )
    permit_ids = fields.One2many(
        'tn.construction.permit',
        'project_id',
        string='Permits & Approvals',
    )
    construction_sub_project_count = fields.Integer(
        string='Sub Projects',
        compute='_compute_construction_counts',
    )
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_construction_counts',
    )
    progress_billing_count = fields.Integer(
        string='Progress Billing',
        compute='_compute_construction_counts',
    )
    construction_boq_summary_count = fields.Integer(
        string='BOQ Summary',
        compute='_compute_construction_counts',
    )
    construction_budget_summary_count = fields.Integer(
        string='Budget Summary',
        compute='_compute_construction_counts',
    )
    construction_work_order_count = fields.Integer(
        string='Work Orders',
        compute='_compute_construction_counts',
    )
    construction_material_requisition_count = fields.Integer(
        string='Material Requisitions',
        compute='_compute_construction_counts',
    )
    construction_task_count = fields.Integer(
        string='Tasks',
        compute='_compute_construction_counts',
    )
    construction_inspection_task_count = fields.Integer(
        string='Inspection Tasks',
        compute='_compute_construction_counts',
    )
    construction_purchase_order_count = fields.Integer(
        string='Purchase Orders',
        compute='_compute_construction_counts',
    )
    construction_stock_transfer_count = fields.Integer(
        string='Stock Transfers',
        compute='_compute_construction_counts',
    )
    construction_measurement_count = fields.Integer(
        string='Measurements',
        compute='_compute_construction_counts',
    )

    @api.depends('boq_line_ids')
    def _compute_boq_line_count(self):
        for project in self:
            project.boq_line_count = len(project.boq_line_ids)

    @api.depends('construction_sub_project_ids.progress')
    def _compute_progress_percent(self):
        for project in self:
            sub_projects = project.construction_sub_project_ids
            if sub_projects:
                project.progress_percent = sum(sub_projects.mapped('progress')) / len(sub_projects)
            else:
                done = project.closed_task_count or 0
                total = project.task_count or 0
                project.progress_percent = (done / total * 100.0) if total else 0.0

    def _compute_construction_counts(self):
        attachment = self.env['ir.attachment'].sudo()
        purchase_order = self.env['purchase.order']
        Boq = self.env['tn.construction.sub.project.boq']
        BudgetLine = self.env['tn.construction.budget.line']
        WorkOrder = self.env['tn.construction.work.order']
        MaterialRequest = self.env['tn.construction.material.request']
        Task = self.env['project.task']
        InternalTransfer = self.env['tn.construction.internal.transfer']
        Measurement = self.env['tn.construction.measurement']
        for project in self:
            sub_project_ids = project.construction_sub_project_ids.ids
            project_domain = [('project_id', '=', project.id)]
            sub_project_domain = [('sub_project_id', 'in', sub_project_ids)]
            project.construction_sub_project_count = len(project.construction_sub_project_ids)
            project.document_count = attachment.search_count([
                ('res_model', '=', project._name),
                ('res_id', '=', project.id),
            ])
            project.construction_boq_summary_count = Boq.search_count(sub_project_domain)
            project.construction_budget_summary_count = BudgetLine.search_count(project_domain)
            project.construction_work_order_count = WorkOrder.search_count(project_domain)
            project.construction_material_requisition_count = MaterialRequest.search_count(project_domain)
            project.construction_task_count = Task.search_count(project_domain)
            project.construction_inspection_task_count = Task.search_count(
                project_domain + [('name', 'ilike', 'inspection')]
            )
            project.construction_stock_transfer_count = InternalTransfer.search_count(project_domain)
            project.construction_measurement_count = Measurement.search_count(project_domain)
            project.construction_purchase_order_count = (
                purchase_order.search_count(project_domain)
                if 'project_id' in purchase_order._fields
                else 0
            )
            project.progress_billing_count = project.construction_purchase_order_count

    @api.constrains('project_warehouse_id', 'company_id')
    def _check_project_warehouse_company(self):
        for project in self:
            warehouse_company = project.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != project.company_id:
                raise ValidationError(
                    _('The Project Warehouse must belong to the same company as the project.')
                )

    @api.onchange('company_id')
    def _onchange_company_id_project_warehouse(self):
        for project in self:
            warehouse_company = project.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != project.company_id:
                project.project_warehouse_id = False

    def action_construction_set_in_progress(self):
        self.write({'construction_state': 'in_progress'})

    def action_construction_complete(self):
        self.write({'construction_state': 'completed'})

    def action_create_construction_sub_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Sub Project'),
            'res_model': 'tn.construction.sub.project',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_project_id': self.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': self.project_warehouse_id.id,
            },
        }

    def action_view_boq_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'BOQ Budget Control',
            'res_model': 'tn.boq.line',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_boq_summary(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('BOQ Summary'),
            'res_model': 'tn.construction.sub.project.boq',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', 'in', self.construction_sub_project_ids.ids)],
            'context': {'default_project_id': self.id},
        }

    def action_view_budget_summary(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Summary'),
            'res_model': 'tn.construction.budget.line',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_construction_sub_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub Projects'),
            'res_model': 'tn.construction.sub.project',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': self.project_warehouse_id.id,
            },
        }

    def action_view_project_map(self):
        self.ensure_one()
        url = 'https://www.google.com/maps'
        if self.latitude and self.longitude:
            url = 'https://www.google.com/maps/search/?api=1&query=%s,%s' % (
                self.latitude,
                self.longitude,
            )
        return {'type': 'ir.actions.act_url', 'target': 'new', 'url': url}

    def action_view_project_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def action_view_progress_billing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Progress Billing'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)] if 'project_id' in self.env['purchase.order']._fields else [],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'tn.construction.work.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_material_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'tn.construction.material.request',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_construction_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_construction_inspection_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspection Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('project_id', '=', self.id), ('name', 'ilike', 'inspection')],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)] if 'project_id' in self.env['purchase.order']._fields else [],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_stock_transfers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Transfers'),
            'res_model': 'tn.construction.internal.transfer',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_measurements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Measurements'),
            'res_model': 'tn.construction.measurement',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_gantt(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Schedule'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,calendar,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }


class TnConstructionSubProject(models.Model):
    _name = 'tn.construction.sub.project'
    _description = 'Construction Sub Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Sub Project Name', required=True)
    code = fields.Char(copy=False)
    project_id = fields.Many2one(
        'project.project',
        string='Parent Project',
        required=True,
        ondelete='cascade',
    )
    related_project_id = fields.Many2one(
        'project.project',
        string='Legacy Project',
        default=lambda self: self.env.context.get('default_project_id'),
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        'res.company',
        string='Warehouse',
        default=lambda self: self.env.company,
    )
    project_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Project Warehouse',
        domain="[('company_id', 'in', [company_id, False])]",
        help='Default warehouse used for material movements, receipts, issues, and returns related to this project.',
    )
    budget_id = fields.Many2one(
        'tn.construction.budget',
        string='Budget',
        domain="[('project_id', '=', project_id)]",
    )
    stage = fields.Selection(
        [
            ('draft', 'Draft'),
            ('planning', 'Planning'),
            ('procurement', 'Procurement'),
            ('construction', 'Construction'),
            ('handover', 'Handover'),
            ('done', 'Done'),
        ],
        default='planning',
        tracking=True,
    )
    schedule_start_date = fields.Date(string='Schedule Start Date')
    schedule_end_date = fields.Date(string='Schedule End Date')
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    responsible_engineer_id = fields.Many2one(
        'res.partner',
        string='Responsible Engineer',
    )
    site_zone = fields.Char(string='Zone / Block / Floor')
    progress = fields.Float(string='Progress (%)')
    address_street = fields.Char(string='Street')
    address_street2 = fields.Char(string='Street 2')
    address_city = fields.Char(string='City')
    address_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id', '=?', address_country_id)]",
    )
    address_zip = fields.Char(string='ZIP')
    address_country_id = fields.Many2one('res.country', string='Country')
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    use_lwh = fields.Boolean(
        string='Is use of (LENGTH × WIDTH × HEIGHT) ?',
        default=True,
    )
    engineer_ids = fields.One2many(
        'tn.construction.sub.project.engineer',
        'sub_project_id',
        string='Engineers',
    )
    document_ids = fields.One2many(
        'tn.construction.sub.project.document',
        'sub_project_id',
        string='Documents',
    )
    insurance_ids = fields.One2many(
        'tn.construction.sub.project.insurance',
        'sub_project_id',
        string='Insurance',
    )
    extra_expense_ids = fields.One2many(
        'tn.construction.sub.project.extra.expense',
        'sub_project_id',
        string='Extra Expenses',
    )
    boq_item_ids = fields.One2many(
        'tn.construction.sub.project.boq',
        'sub_project_id',
        string='BOQ',
    )
    measurement_ids = fields.One2many(
        'tn.construction.measurement',
        'sub_project_id',
        string='Measurements',
    )
    boq_count = fields.Integer(compute='_compute_link_counts')
    measurement_count = fields.Integer(compute='_compute_link_counts')
    progress_billing_count = fields.Integer(compute='_compute_link_counts')
    budget_line_count = fields.Integer(compute='_compute_link_counts')
    work_order_count = fields.Integer(compute='_compute_link_counts')
    task_count = fields.Integer(compute='_compute_link_counts')
    inspection_task_count = fields.Integer(compute='_compute_link_counts')
    phase_count = fields.Integer(compute='_compute_link_counts')
    material_requisition_count = fields.Integer(compute='_compute_link_counts')
    purchase_order_count = fields.Integer(compute='_compute_link_counts')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for sub_project in self:
            project = sub_project.project_id
            if not project:
                continue
            sub_project.related_project_id = project
            sub_project.company_id = project.company_id
            sub_project.warehouse_id = project.warehouse_id or project.company_id
            sub_project.project_warehouse_id = project.project_warehouse_id
            sub_project.address_street = project.address_street
            sub_project.address_street2 = project.address_street2
            sub_project.address_city = project.address_city
            sub_project.address_state_id = project.address_state_id
            sub_project.address_zip = project.address_zip
            sub_project.address_country_id = project.address_country_id
            sub_project.longitude = project.longitude
            sub_project.latitude = project.latitude
            sub_project.schedule_start_date = project.date_start
            sub_project.schedule_end_date = project.date

    @api.constrains('project_warehouse_id', 'company_id')
    def _check_project_warehouse_company(self):
        for sub_project in self:
            warehouse_company = sub_project.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != sub_project.company_id:
                raise ValidationError(
                    _('The Project Warehouse must belong to the same company as the project.')
                )

    @api.onchange('company_id')
    def _onchange_company_id_project_warehouse(self):
        for sub_project in self:
            warehouse_company = sub_project.project_warehouse_id.company_id
            if warehouse_company and warehouse_company != sub_project.company_id:
                sub_project.project_warehouse_id = False

    def _compute_link_counts(self):
        PurchaseOrder = self.env['purchase.order']
        BudgetLine = self.env['tn.construction.budget.line']
        WorkOrder = self.env['tn.construction.work.order']
        MaterialRequest = self.env['tn.construction.material.request']
        Phase = self.env['tn.construction.phase']
        Task = self.env['project.task']
        Measurement = self.env['tn.construction.measurement']
        for sub_project in self:
            task_domain = [('construction_sub_project_id', '=', sub_project.id)]
            purchase_project_domain = (
                [('project_id', '=', sub_project.project_id.id)]
                if 'project_id' in PurchaseOrder._fields
                else []
            )
            sub_project.boq_count = len(sub_project.boq_item_ids)
            sub_project.budget_line_count = BudgetLine.search_count([('sub_project_id', '=', sub_project.id)])
            sub_project.work_order_count = WorkOrder.search_count([('sub_project_id', '=', sub_project.id)])
            sub_project.material_requisition_count = MaterialRequest.search_count([('sub_project_id', '=', sub_project.id)])
            sub_project.task_count = Task.search_count(task_domain)
            sub_project.inspection_task_count = Task.search_count(
                task_domain + [('name', 'ilike', 'inspection')]
            )
            sub_project.phase_count = Phase.search_count([('sub_project_id', '=', sub_project.id)])
            sub_project.measurement_count = Measurement.search_count([('sub_project_id', '=', sub_project.id)])
            sub_project.purchase_order_count = PurchaseOrder.search_count(purchase_project_domain)
            sub_project.progress_billing_count = PurchaseOrder.search_count(purchase_project_domain)

    def _project_domain(self):
        self.ensure_one()
        return [('project_id', '=', self.project_id.id)]

    def action_view_budget_analysis(self):
        self.ensure_one()
        return self.action_view_budget_lines()

    def action_view_progress_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Progress Bills'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.project_id.id)] if 'project_id' in self.env['purchase.order']._fields else [],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('construction_sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_construction_sub_project_id': self.id,
            },
        }

    def action_view_inspection_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspection Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('construction_sub_project_id', '=', self.id), ('name', 'ilike', 'inspection')],
            'context': {
                'default_project_id': self.project_id.id,
                'default_construction_sub_project_id': self.id,
            },
        }

    def action_view_project_phases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Phases (WBS)'),
            'res_model': 'tn.construction.phase',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
            },
        }

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'tn.construction.work.order',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': self.project_warehouse_id.id,
            },
        }

    def action_view_material_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'tn.construction.material.request',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
                'default_company_id': self.company_id.id,
                'default_project_warehouse_id': self.project_warehouse_id.id,
            },
        }

    def action_view_boq_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('BOQ'),
            'res_model': 'tn.construction.sub.project.boq',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
            },
        }

    def action_view_measurements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Measurements'),
            'res_model': 'tn.construction.measurement',
            'view_mode': 'list,form',
            'domain': [('sub_project_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
            },
        }

    def action_view_work_order_po(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Order PO'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
        }

    def action_view_mreq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ('draft', 'sent', 'to approve'))],
        }

    def action_view_mreq_po(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('MREQ PO'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ('purchase', 'done'))],
        }

    def action_view_budget_lines(self):
        self.ensure_one()
        domain = [('sub_project_id', '=', self.id)]
        if self.budget_id:
            domain = [('budget_id', '=', self.budget_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Lines'),
            'res_model': 'tn.construction.budget.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_project_id': self.project_id.id,
                'default_sub_project_id': self.id,
                'default_budget_id': self.budget_id.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project = self.env['project.project'].browse(vals.get('project_id'))
            if project:
                vals.setdefault('related_project_id', project.id)
                vals.setdefault('company_id', project.company_id.id)
                vals.setdefault('warehouse_id', (project.warehouse_id or project.company_id).id)
                vals.setdefault('project_warehouse_id', project.project_warehouse_id.id)
                vals.setdefault('address_street', project.address_street)
                vals.setdefault('address_street2', project.address_street2)
                vals.setdefault('address_city', project.address_city)
                vals.setdefault('address_state_id', project.address_state_id.id)
                vals.setdefault('address_zip', project.address_zip)
                vals.setdefault('address_country_id', project.address_country_id.id)
                vals.setdefault('longitude', project.longitude)
                vals.setdefault('latitude', project.latitude)
                vals.setdefault('schedule_start_date', project.date_start)
                vals.setdefault('schedule_end_date', project.date)
        return super().create(vals_list)


class TnConstructionSubProjectEngineer(models.Model):
    _name = 'tn.construction.sub.project.engineer'
    _description = 'Construction Sub Project Engineer'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Engineer', required=True)
    role = fields.Char(default='Engineer')
    phone = fields.Char(related='partner_id.phone', readonly=False)
    email = fields.Char(related='partner_id.email', readonly=False)
    share = fields.Float(string='Share (%)')
    image_128 = fields.Image(related='partner_id.image_128')


class TnConstructionSubProjectDocument(models.Model):
    _name = 'tn.construction.sub.project.document'
    _description = 'Construction Sub Project Document'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Document', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Documents')


class TnConstructionSubProjectInsurance(models.Model):
    _name = 'tn.construction.sub.project.insurance'
    _description = 'Construction Sub Project Insurance'
    _order = 'issue_date desc, id desc'

    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
    )
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    issue_date = fields.Date(string='Issue Date')
    insurance = fields.Char()
    insurance_ref = fields.Char(string='Insurance Reference')
    risk_coverage = fields.Char(string='Risk Coverage')
    attachment_ids = fields.Many2many('ir.attachment', string='Documents')
    total_charge = fields.Monetary()
    bill_id = fields.Many2one('account.move', domain="[('move_type', 'in', ('in_invoice', 'in_refund'))]")
    status = fields.Selection(
        [('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled')],
        default='draft',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='sub_project_id.company_id.currency_id',
        readonly=True,
    )


class TnConstructionSubProjectExtraExpense(models.Model):
    _name = 'tn.construction.sub.project.extra.expense'
    _description = 'Construction Sub Project Extra Expense'
    _order = 'date desc, id desc'

    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
    )
    date = fields.Date(default=fields.Date.context_today)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    expense_id = fields.Many2one('product.product', string='Expense')
    note = fields.Char()
    qty = fields.Float(string='Qty.', default=1.0)
    cost = fields.Monetary()
    bill_id = fields.Many2one('account.move', domain="[('move_type', 'in', ('in_invoice', 'in_refund'))]")
    status = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('posted', 'Posted'), ('cancelled', 'Cancelled')],
        default='draft',
    )
    payment_status = fields.Selection(
        [('not_paid', 'Not Paid'), ('partial', 'Partially Paid'), ('paid', 'Paid')],
        default='not_paid',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='sub_project_id.company_id.currency_id',
        readonly=True,
    )


class TnConstructionSubProjectBoq(models.Model):
    _name = 'tn.construction.sub.project.boq'
    _description = 'Construction Sub Project BOQ'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    item_code = fields.Char(string='BOQ Item Code', copy=False)
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
        string='Sub Project',
    )
    project_id = fields.Many2one(
        'project.project',
        related='sub_project_id.project_id',
        store=True,
        readonly=True,
        string='Parent Project',
    )
    work_type = fields.Char(string='Work Type', required=True)
    work_sub_type = fields.Char(string='Work Sub Type')
    description = fields.Text(string='Description')
    qty = fields.Float(string='Qty.', default=1.0)
    length = fields.Float()
    width = fields.Float()
    height = fields.Float()
    total_qty = fields.Float(string='Total Qty.', compute='_compute_totals', store=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    unit_rate = fields.Monetary(string='Unit Rate', currency_field='currency_id')
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    executed_qty = fields.Float(string='Executed Qty')
    remaining_qty = fields.Float(
        string='Remaining Qty',
        compute='_compute_totals',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='sub_project_id.company_id.currency_id',
        readonly=True,
    )

    @api.depends('qty', 'length', 'width', 'height', 'unit_rate', 'executed_qty')
    def _compute_totals(self):
        for line in self:
            total_qty = line.qty
            for dimension in (line.length, line.width, line.height):
                if dimension:
                    total_qty *= dimension
            line.total_qty = total_qty
            line.total_amount = line.total_qty * line.unit_rate
            line.remaining_qty = line.total_qty - line.executed_qty

    @api.constrains('total_qty', 'unit_rate', 'executed_qty')
    def _check_boq_quantities_and_rates(self):
        for line in self:
            if line.total_qty < 0:
                raise ValidationError(_('Total Qty cannot be negative.'))
            if line.unit_rate < 0:
                raise ValidationError(_('Unit Rate cannot be negative.'))
            if line.executed_qty < 0:
                raise ValidationError(_('Executed Qty cannot be negative.'))
            if line.executed_qty > line.total_qty:
                raise ValidationError(_('Executed Qty cannot be greater than Total Qty.'))


class TnConstructionStakeholder(models.Model):
    _name = 'tn.construction.stakeholder'
    _description = 'Construction Stakeholder'
    _order = 'id'

    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Stakeholder', required=True)
    role = fields.Char(default='Stakeholder')
    email = fields.Char(related='partner_id.email', readonly=False)
    phone = fields.Char(related='partner_id.phone', readonly=False)
    share = fields.Float(string='Share (%)')
    image_128 = fields.Image(related='partner_id.image_128')


class TnConstructionSiteImage(models.Model):
    _name = 'tn.construction.site.image'
    _description = 'Construction Site Image'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    name = fields.Char(required=True, default='Site Image')
    image = fields.Image(required=True)
    description = fields.Text()


class TnConstructionMeasurement(models.Model):
    _name = 'tn.construction.measurement'
    _description = 'Construction Project Measurement'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        string='Sub Project',
        domain="[('project_id', '=', project_id)]",
    )
    title = fields.Char(required=True)
    length = fields.Float(string='Length(m)')
    width = fields.Float(string='Width(m)')
    area = fields.Float(string='Area(m²)', compute='_compute_area', store=True)

    @api.depends('length', 'width')
    def _compute_area(self):
        for measurement in self:
            measurement.area = measurement.length * measurement.width

    @api.onchange('sub_project_id')
    def _onchange_sub_project_id(self):
        for measurement in self:
            if measurement.sub_project_id:
                measurement.project_id = measurement.sub_project_id.project_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sub_project = self.env['tn.construction.sub.project'].browse(vals.get('sub_project_id'))
            if sub_project:
                vals.setdefault('project_id', sub_project.project_id.id)
        return super().create(vals_list)


class TnConstructionPermit(models.Model):
    _name = 'tn.construction.permit'
    _description = 'Construction Permit & Approval'
    _order = 'date desc, id desc'

    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today)
    document_type = fields.Char(string='Document Type', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Documents')
    submitted_by_id = fields.Many2one('res.partner', string='Submitted By')
    feedback = fields.Text()
    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        required=True,
    )

    def init(self):
        self.env.cr.execute(
            """
            UPDATE tn_construction_permit
               SET status = 'pending'
             WHERE status IS NULL
                OR status IN ('draft', 'submitted')
            """
        )
