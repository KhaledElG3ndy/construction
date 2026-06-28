from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._tn_check_boq_on_confirmed_order()
        return lines

    def write(self, vals):
        res = super().write(vals)
        # Only re-check when something budget-relevant changed.
        if {'product_id', 'product_qty', 'analytic_distribution'} & set(vals):
            self._tn_check_boq_on_confirmed_order()
        return res

    def _tn_qty_in_product_uom(self):
        """This line's quantity expressed in the product's reference UoM, which
        is the UoM the BOQ line is measured in. Lets a PO raised in kg be
        compared against a BOQ approved in tonnes."""
        self.ensure_one()
        if not self.product_id:
            return 0.0
        ref_uom = self.product_id.uom_id
        if not self.product_uom or self.product_uom == ref_uom:
            return self.product_qty
        return self.product_uom._compute_quantity(self.product_qty, ref_uom)

    def _tn_check_boq_on_confirmed_order(self):
        """Hard-stop for lines added/edited on an ALREADY confirmed PO. The line
        is already counted in committed_qty here, so we measure overage against
        what was committed before this line's quantity."""
        Boq = self.env['tn.boq.line']
        for line in self:
            order = line.order_id
            if not order or order.state not in ('purchase', 'done'):
                continue
            if order.boq_override:
                continue
            if not line.product_id or not line.product_qty:
                continue
            added = line._tn_qty_in_product_uom()
            for account in line.distribution_analytic_account_ids:
                boq = Boq._tn_find(line.product_id.id, account.id)
                if not boq:
                    continue
                # committed_qty already includes this line; the "addition" is
                # this line's qty and the pre-existing base excludes it.
                base = boq.committed_qty - added
                boq._tn_assert_within_budget(added, base_committed=base)
