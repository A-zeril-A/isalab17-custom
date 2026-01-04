from odoo import models, fields, api
from odoo.tools import float_round

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    amount_total = fields.Monetary(
        string="Total Amount",
        compute="_compute_payment_info",
        help="Sum of all confirmed Sale Orders linked to this opportunity."
    )
    amount_paid = fields.Monetary(
        string="Paid Amount",
        compute="_compute_payment_info",
        help="Sum of paid amounts from posted invoices of linked Sale Orders."
    )
    amount_due = fields.Monetary(
        string="Due Amount",
        compute="_compute_payment_info",
        help="Remaining = Total - Paid."
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_payment_info",
        help="Sum of untaxed amounts from confirmed Sale Orders."
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends(
        'order_ids.invoice_status', 
        'order_ids.amount_total',
        'order_ids.amount_untaxed',
        'order_ids.invoice_ids.state',
        'order_ids.invoice_ids.amount_residual',
        'order_ids.invoice_ids.payment_state'
    )
    def _compute_payment_info(self):
        for lead in self:
            total = 0.0
            paid = 0.0
            untaxed = 0.0

            # All sale orders linked to the opportunity
            sale_orders = lead.order_ids.filtered(lambda so: so.opportunity_id == lead)
            
            if not sale_orders:
                lead.amount_total = 0.0
                lead.amount_paid = 0.0
                lead.amount_due = 0.0
                lead.amount_untaxed = 0.0
                continue

            # Calculate totals
            for so in sale_orders:
                total += so.amount_total
                untaxed += so.amount_untaxed

            # Calculate paid amount from invoices
            invoices = self.env['account.move'].search([
                ('invoice_origin', 'in', sale_orders.mapped('name')),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
            ])

            for inv in invoices:
                sign = -1.0 if inv.move_type == 'out_refund' else 1.0
                paid_amount = inv.amount_total - inv.amount_residual
                paid += sign * paid_amount

            # Round values to prevent floating point computational errors
            lead.amount_total = float_round(total, precision_digits=2)
            lead.amount_paid = float_round(paid, precision_digits=2)
            lead.amount_due = float_round(total - paid, precision_digits=2)
            lead.amount_untaxed = float_round(untaxed, precision_digits=2)

    # Adding this function to ensure updates when invoices change
    def _inverse_payment_info(self):
        """This function ensures that calculations are updated when invoices change"""
        pass