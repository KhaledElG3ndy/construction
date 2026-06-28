from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    boq_override = fields.Boolean(
        string='Approved Variation (BOQ Override)',
        default=False,
        copy=False,
        help='When set, this PO represents an approved Variation Order and the '
             'BOQ budget hard-stop is bypassed for its lines. This is the '
             'controlled override path.',
    )

    def button_confirm(self):
        # Server-side hard-stop: block confirmation of any PO that would commit
        # more than the approved BOQ quantity. Checked BEFORE super() so the
        # PO is still draft and not yet counted in committed_qty.
        for order in self:
            order._tn_check_boq_on_confirm()
        return super().button_confirm()

    def _tn_check_boq_on_confirm(self):
        self.ensure_one()
        if self.boq_override:
            return
        Boq = self.env['tn.boq.line']
        # Aggregate this order's contribution per (analytic account, product).
        additions = {}
        for line in self.order_line:
            if not line.product_id or not line.product_qty:
                continue
            qty = line._tn_qty_in_product_uom()
            for account in line.distribution_analytic_account_ids:
                key = (account.id, line.product_id.id)
                additions[key] = additions.get(key, 0.0) + qty
        for (account_id, product_id), added_qty in additions.items():
            boq = Boq._tn_find(product_id, account_id)
            if not boq:
                # No BOQ line governs this product+project: allow it.
                continue
            # This PO is not yet confirmed, so committed_qty excludes it.
            boq._tn_assert_within_budget(added_qty)
