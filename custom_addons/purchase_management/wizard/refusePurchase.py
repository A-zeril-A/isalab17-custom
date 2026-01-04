from odoo import api,fields,models

# Modified by A_zeril_A, 2025-10-20: Corrected invalid 'String' parameter to 'string' in multiple fields for Odoo 16 upgrade compatibility.

class refusePurchaseWizard(models.TransientModel):
    _name           = "refuse.purchase.wizard"
    _description    = "Refuse Purchase Wizard"



    purchase_id     = fields.Many2one('purchase.management', string="Purchase")
    reason          = fields.Text(string="Reason")



    def action_refuse(self):
        return
    