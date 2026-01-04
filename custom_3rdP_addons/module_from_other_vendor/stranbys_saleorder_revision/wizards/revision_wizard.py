#    Stranbys Info Solution. Ltd.
#    ===========================
#    Copyright (C) 2022-TODAY Stranbys Stranbys Info Solution(<https://www.stranbys.com>)
#    Author: Stranbys Info Solution(<https://www.stranbys.com>)
from odoo import fields, models, _



class SalesRevision(models.TransientModel):
    _name = 'sale.order.revision.wizard'
    # Added by A_zeril_A, 2025-10-20: Add model description for Odoo 16 upgrade compatibility.
    _description = 'Sale Order Revision Wizard'

    order_id = fields.Many2one('sale.order', string='Sale Order')
    revision_id = fields.Many2one('sale.order.revision', string='Revision Group')
    next_code = fields.Char(string='Next Code')
    reason = fields.Char(string="Reason", required=True)

    # def create_message_in_log(self,order_id,message):
    #     order = self.env['sale.order'].search([('revision_id', '=', self.revision_id.id)])
    #     for rec in order:
    #         rec.order.message_post(body=message , subtype='mt_note')
    def create_revision(self):
        sale_orders = self.env['sale.order'].search([('revision_id', '=', self.revision_id.id)])
        for rec in sale_orders:
            rec.is_completed = False
        vals = {
            'name': self.revision_id.name + ' Rev.' + str(self.next_code),
            'state': 'draft',
            'revision_id': self.revision_id.id,
            'is_completed': True
        }
        copy_id = self.order_id.copy(default=vals)
        copy_id.message_post(body=_("Revision: %s Reason: %s") % (self.next_code, self.reason))

        self.revision_id.write({
            'last_code': self.next_code
        })
        self.order_id.message_post(body=_("Revision: %s Reason: %s") % (self.next_code, self.reason))
        # self.order_id.write({
        #     'is_completed': False
        # })

        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['views'] = form_view
        action['res_id'] = copy_id.id

        return action
    
