from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    residual_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_residual_amount",
        store=True,
        currency_field='currency_id'
    )
    percent = fields.Float(
        string="ّinvoiced %",
        compute="_compute_residual_amount",
        store=True,
    )
    @api.depends('amount_total', 'invoice_ids.amount_total', 'invoice_ids.payment_state')
    def _compute_residual_amount(self):
        for order in self:
            paid = sum(inv.amount_total for inv in order.invoice_ids if inv.payment_state == 'paid')
            order.residual_amount = order.amount_total - paid
            if order.amount_total > 0 :
                invoiced_total = sum(inv.amount_total for inv in order.invoice_ids if inv.state not in ('cancel',))
                order.percent = (invoiced_total / order.amount_total) * 100
            else :
                order.percent =  0.0
