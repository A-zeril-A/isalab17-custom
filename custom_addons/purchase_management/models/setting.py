
from odoo import models, fields, api
class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_responsible_id = fields.Many2one(
        'res.users', 
        string="Default Responsible"
    )
    budget_approver_id = fields.Many2one(
        'res.users', 
        string="Default Budget Approver"
    )
    budget_limit = fields.Monetary(
        string="Purchase Limit", 
        currency_field='company_currency_id', 
        default=100
    )
    company_currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_id', 
        string="Company Currency", 
        readonly=True
    )

    def set_values(self):
        super(PurchaseConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'purchase_management.purchase_responsible_id', 
            self.purchase_responsible_id.id if self.purchase_responsible_id else False
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'purchase_management.budget_approver_id', 
            self.budget_approver_id.id if self.budget_approver_id else False
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'purchase_management.budget_limit', 
            self.budget_limit
        )

    @api.model
    def get_values(self):
        res = super(PurchaseConfigSettings, self).get_values()
        purchase_responsible_id = self.env['ir.config_parameter'].sudo().get_param('purchase_management.purchase_responsible_id', default=False)
        budget_approver_id = self.env['ir.config_parameter'].sudo().get_param('purchase_management.budget_approver_id', default=False)
        budget_limit = self.env['ir.config_parameter'].sudo().get_param('purchase_management.budget_limit', default=100)
        
        res.update(
            purchase_responsible_id=int(purchase_responsible_id) if purchase_responsible_id else False,
            budget_approver_id=int(budget_approver_id) if budget_approver_id else False,
            budget_limit=float(budget_limit)
        )
        
        return res

