from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    construction_work_order_id = fields.Many2one(
        'tn.construction.work.order',
        string='Work Order',
        domain="[('project_id', '=', project_id)]",
    )
    construction_sub_project_id = fields.Many2one(
        'tn.construction.sub.project',
        string='Construction Project',
    )
    construction_timesheet_ids = fields.One2many(
        'tn.construction.task.timesheet',
        'task_id',
        string='Timesheets',
    )
    construction_time_spent = fields.Float(
        string='Time Spent',
        compute='_compute_construction_time_spent',
    )
    construction_progress = fields.Float(
        string='Progress',
        compute='_compute_construction_progress',
    )

    @api.depends('construction_timesheet_ids.hours', 'effective_hours')
    def _compute_construction_time_spent(self):
        for task in self:
            timesheet_hours = sum(task.construction_timesheet_ids.mapped('hours'))
            task.construction_time_spent = timesheet_hours or task.effective_hours

    @api.depends('construction_time_spent', 'allocated_hours', 'state', 'child_ids.state')
    def _compute_construction_progress(self):
        for task in self:
            if task.state == '1_done':
                task.construction_progress = 100.0
            elif task.allocated_hours:
                task.construction_progress = min(
                    100.0,
                    (task.construction_time_spent / task.allocated_hours) * 100.0,
                )
            elif task.child_ids:
                done_children = task.child_ids.filtered(lambda child: child.state == '1_done')
                task.construction_progress = (len(done_children) / len(task.child_ids)) * 100.0
            else:
                task.construction_progress = 0.0

    @api.onchange('construction_work_order_id')
    def _onchange_construction_work_order_id(self):
        for task in self:
            order = task.construction_work_order_id
            if not order:
                continue
            task.project_id = order.task_project_id or order.project_id
            task.construction_sub_project_id = order.sub_project_id
            task.partner_id = order.project_id.partner_id
            task.date_deadline = order.end_date
            if not task.name:
                task.name = order.task_title or order.name
            if not task.description and order.description:
                task.description = order.description
            if order.assignee_ids:
                task.user_ids = order.assignee_ids

    def action_construction_task_start(self):
        self.write({'state': '01_in_progress'})


class TnConstructionTaskTimesheet(models.Model):
    _name = 'tn.construction.task.timesheet'
    _description = 'Construction Task Timesheet'
    _order = 'date desc, id desc'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', string='Employee', default=lambda self: self.env.user, required=True)
    description = fields.Char()
    hours = fields.Float(string='Hours')
