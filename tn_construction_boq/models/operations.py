from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TnConstructionInternalTransfer(models.Model):
    _name = 'tn.construction.internal.transfer'
    _description = 'Construction Internal Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Sequence', required=True, default='New', copy=False)
    title = fields.Char(required=True, default='Internal Transfer')
    project_id = fields.Many2one('project.project', string='Site', required=True)
    sub_project_id = fields.Many2one('tn.construction.sub.project', string='Sub Project', domain="[('project_id', '=', project_id)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    work_type = fields.Char()
    phase_id = fields.Many2one('tn.construction.phase', string='Phase(WBS)', domain="[('project_id', '=', project_id)]")
    work_order_id = fields.Many2one('tn.construction.work.order', string='Work Order', domain="[('project_id', '=', project_id)]")
    material_request_id = fields.Many2one('tn.construction.material.request', string='Material Req', domain="[('project_id', '=', project_id)]")
    state = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled')],
        default='draft',
        tracking=True,
    )
    line_ids = fields.One2many('tn.construction.internal.transfer.line', 'transfer_id', string='Internal Transfer')
    stock_picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
    vehicle_no = fields.Char(default='NE-DMO-101')
    vehicle_name = fields.Char(default='Flatbed Truck')
    vehicle_model = fields.Char(string='Model')
    driver_name = fields.Char(default='Demo Driver')
    driver_phone = fields.Char(string='Phone')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tn.construction.internal.transfer') or 'New'
        return super().create(vals_list)

    @api.onchange('work_order_id')
    def _onchange_work_order_id(self):
        for transfer in self:
            order = transfer.work_order_id
            if not order:
                continue
            transfer.project_id = order.project_id
            transfer.sub_project_id = order.sub_project_id
            transfer.phase_id = order.phase_id
            transfer.company_id = order.company_id
            transfer.work_type = order.work_type

    @api.onchange('material_request_id')
    def _onchange_material_request_id(self):
        for transfer in self:
            request = transfer.material_request_id
            if not request:
                continue
            transfer.project_id = request.project_id
            transfer.sub_project_id = request.sub_project_id
            transfer.phase_id = request.phase_id
            transfer.work_order_id = request.work_order_id
            transfer.company_id = request.company_id
            transfer.work_type = request.work_type

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_internal_transfer(self):
        self.ensure_one()
        if self.stock_picking_id:
            return self._action_open_picking()
        if not self.line_ids:
            raise UserError(_('Add at least one transfer line.'))

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1) or self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        stock_location = (
            warehouse.lot_stock_id
            or self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
            or self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
        )
        if not picking_type:
            if not stock_location:
                raise UserError(_('Configure an internal stock location first.'))
            picking_type = self.env['stock.picking.type'].create({
                'name': _('Internal Transfers'),
                'code': 'internal',
                'sequence_code': 'INT',
                'warehouse_id': warehouse.id,
                'company_id': self.company_id.id,
                'default_location_src_id': stock_location.id,
                'default_location_dest_id': stock_location.id,
            })

        source_location = picking_type.default_location_src_id or stock_location
        destination_location = picking_type.default_location_dest_id or stock_location
        if not source_location or not destination_location:
            raise UserError(_('Configure source and destination stock locations first.'))

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': destination_location.id,
            'origin': self.name,
            'scheduled_date': fields.Datetime.to_datetime(self.date),
            'company_id': self.company_id.id,
        })
        for line in self.line_ids.filtered('product_id'):
            uom = line.uom_id or line.product_id.uom_id
            self.env['stock.move'].create({
                'name': line.description or line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': uom.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': destination_location.id,
                'company_id': self.company_id.id,
            })
        self.stock_picking_id = picking
        self.state = 'in_progress'
        return self._action_open_picking()

    def _action_open_picking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfer'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_picking_id.id,
        }


class TnConstructionInternalTransferLine(models.Model):
    _name = 'tn.construction.internal.transfer.line'
    _description = 'Construction Internal Transfer Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    transfer_id = fields.Many2one('tn.construction.internal.transfer', required=True, ondelete='cascade')
    work_sub_type = fields.Char(string='Work Sub Type')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char()
    qty = fields.Float(string='Qty.', default=1.0)
    forecast_qty = fields.Float(string='Forecast Qty.')
    uom_id = fields.Many2one('uom.uom', string='UOM')
    pickup_warehouse_id = fields.Many2one('res.company', string='Pickup Warehouse')
    delivery_warehouse_id = fields.Many2one('res.company', string='Delivery Warehouse')
    delivery_order = fields.Char(string='DO')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.name
                line.uom_id = line.product_id.uom_id


class TnConstructionScrapOrder(models.Model):
    _name = 'tn.construction.scrap.order'
    _description = 'Construction Scrap Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Sequence', required=True, default='New', copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    work_order_id = fields.Many2one('tn.construction.work.order', string='Work Order')
    date = fields.Date(default=fields.Date.context_today, required=True)
    note = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    line_ids = fields.One2many('tn.construction.scrap.order.line', 'scrap_id', string='Scrap Order')
    total_amount = fields.Monetary(string='Total', compute='_compute_total_amount', store=True, currency_field='currency_id')
    invoice_id = fields.Many2one('account.move', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tn.construction.scrap.order') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.total_value')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.line_ids.mapped('total_value'))

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self._action_open_invoice()
        if not self.line_ids:
            raise UserError(_('Add at least one scrap line.'))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'company_id': self.company_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name or line.scrap_type,
                    'quantity': line.qty,
                    'price_unit': line.value,
                })
                for line in self.line_ids
            ],
        })
        self.invoice_id = invoice
        return self._action_open_invoice()

    def _action_open_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }


class TnConstructionScrapOrderLine(models.Model):
    _name = 'tn.construction.scrap.order.line'
    _description = 'Construction Scrap Order Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    scrap_id = fields.Many2one('tn.construction.scrap.order', required=True, ondelete='cascade')
    scrap_type = fields.Selection([('material', 'Material'), ('equipment', 'Equipment')], string='Scrap of', default='material', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Qty.', default=1.0)
    company_id = fields.Many2one('res.company', related='scrap_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='scrap_id.currency_id', readonly=True)
    value = fields.Monetary(currency_field='currency_id')
    total_value = fields.Monetary(compute='_compute_total_value', store=True, currency_field='currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and not line.value:
                line.value = line.product_id.lst_price or line.product_id.standard_price

    @api.depends('qty', 'value')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.qty * line.value
