from odoo import api, fields, models, _


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
        for project in self:
            project.construction_sub_project_count = len(project.construction_sub_project_ids)
            project.document_count = attachment.search_count([
                ('res_model', '=', project._name),
                ('res_id', '=', project.id),
            ])
            project.progress_billing_count = purchase_order.search_count([
                ('project_id', '=', project.id),
            ]) if 'project_id' in purchase_order._fields else 0

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
    name = fields.Char(string='Title', required=True)
    code = fields.Char(copy=False)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    related_project_id = fields.Many2one(
        'project.project',
        string='Project',
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

    def _compute_link_counts(self):
        PurchaseOrder = self.env['purchase.order']
        for sub_project in self:
            task_domain = [
                ('project_id', '=', sub_project.project_id.id),
            ]
            purchase_project_domain = (
                [('project_id', '=', sub_project.project_id.id)]
                if 'project_id' in PurchaseOrder._fields
                else []
            )
            sub_project.budget_line_count = len(sub_project.project_id.boq_line_ids)
            sub_project.task_count = self.env['project.task'].search_count(task_domain)
            sub_project.work_order_count = sub_project.task_count
            sub_project.inspection_task_count = self.env['project.task'].search_count(
                task_domain + [('name', 'ilike', 'inspection')]
            )
            sub_project.phase_count = self.env['project.milestone'].search_count(task_domain)
            sub_project.material_requisition_count = PurchaseOrder.search_count([
                ('state', 'in', ('draft', 'sent', 'to approve')),
            ] + purchase_project_domain)
            sub_project.purchase_order_count = PurchaseOrder.search_count(purchase_project_domain)
            sub_project.progress_billing_count = PurchaseOrder.search_count(purchase_project_domain)

    def _project_domain(self):
        self.ensure_one()
        return [('project_id', '=', self.project_id.id)]

    def action_view_budget_analysis(self):
        self.ensure_one()
        return self.project_id.action_view_boq_lines()

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
            'domain': self._project_domain(),
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_inspection_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspection Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': self._project_domain() + [('name', 'ilike', 'inspection')],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_project_phases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Phases (WBS)'),
            'res_model': 'project.milestone',
            'view_mode': 'list,form',
            'domain': self._project_domain(),
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': self._project_domain(),
            'context': {'default_project_id': self.project_id.id},
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
    sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        required=True,
        ondelete='cascade',
    )
    work_type = fields.Char(string='Work Type', required=True)
    work_sub_type = fields.Char(string='Work Sub Type')
    qty = fields.Float(string='Qty.', default=1.0)
    length = fields.Float()
    width = fields.Float()
    height = fields.Float()
    total_qty = fields.Float(string='Total Qty.', compute='_compute_total_qty', store=True)

    @api.depends('qty', 'length', 'width', 'height', 'sub_project_id.use_lwh')
    def _compute_total_qty(self):
        for line in self:
            if line.sub_project_id.use_lwh:
                line.total_qty = line.qty * line.length * line.width * line.height
            else:
                line.total_qty = line.qty


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
    title = fields.Char(required=True)
    length = fields.Float(string='Length(m)')
    width = fields.Float(string='Width(m)')
    area = fields.Float(string='Area(m²)', compute='_compute_area', store=True)

    @api.depends('length', 'width')
    def _compute_area(self):
        for measurement in self:
            measurement.area = measurement.length * measurement.width


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
