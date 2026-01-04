from odoo import models, api, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def message_post(self, **kwargs):
        if 'body' not in kwargs:
            message = f"New opportunity: {self.name}"
            if self.partner_id:
                message += f"\nCustomer: {self.partner_id.name}"
            kwargs['body'] = message

        return super().message_post(**kwargs)

    def message_track(self, tracked_fields, initial_values):
        """delete expected_revenue from log chatter"""
        if 'partner_id' in tracked_fields:
            tracked_fields = {'partner_id'}
        else:
            tracked_fields = set()
        return super().message_track(tracked_fields, initial_values)

    # Hide expected_revenue from kanban cards
    can_see_financials = fields.Boolean(
        compute="_compute_can_see_financials",
        store=False
    )

    @api.depends('user_id')
    def _compute_can_see_financials(self):
        for record in self:
            record.can_see_financials = self.env.user.has_group(
                'custom_limited_crm_log_note_and_views.group_crm_full_access')
