from odoo import models,fields,api


class PurchaseLimitWizard(models.TransientModel):

    _name           = 'purchase.limit.wizard'
    _description    = 'Purchase Limit Exceeded Wizard'

    message = fields.Text(string="Message", readonly=True, default="The total amount exceeds the purchase limit, Do you want to proceed?")

    def action_confirm(self):
        self.env['purchase.managment'].browse(self.env.context.get('active_id')).write({'exceeds_budget_limit': False})
        return {'type':'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type':'ir.actions.act_window_close'}