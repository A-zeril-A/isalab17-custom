# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    custom_message_ids = fields.One2many(
        'crm.lead.custom.private.message', 'lead_id', string='Opportunity Commercial Private Chat'
    )

    @api.model_create_multi
    def create(self, vals_list):
        leads = super(CrmLead, self).create(vals_list)
        for lead in leads:
            lead._log_expected_revenue_change(False, lead.expected_revenue)
        return leads

    def write(self, vals):
        for lead in self:
            old_value = lead.expected_revenue
            res = super(CrmLead, lead).write(vals)
            new_value = vals.get('expected_revenue', old_value)

            if 'expected_revenue' in vals and old_value != new_value:
                lead._log_expected_revenue_change(old_value, new_value)

        return res

    def _log_expected_revenue_change(self, old_value, new_value):
        """ Tracking of expected_revenue """
        if old_value != new_value:
            user_name = self.env.user.name
            message = f"{user_name} changed Expected Revenue from {old_value} to ➣➣➣ {new_value}"

            self.env['crm.lead.custom.private.message'].create({
                'lead_id': self.id,
                'message': message,
                'user_id': self.env.user.id,
                'is_system_generated_message': True
            })


class CrmLeadCustomMessage(models.Model):
    _name = 'crm.lead.custom.private.message'
    # Added by A_zeril_A, 2025-10-20: Add model description for Odoo 16 upgrade compatibility.
    _description = 'CRM Lead Custom Private Message'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    lead_id = fields.Many2one('crm.lead', string='Lead', required=False, ondelete='cascade')
    message = fields.Text('Message', tracking=True)
    create_date = fields.Datetime('Created On', default=lambda self: fields.Datetime.now())
    user_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user, required=True)
    mentioned_user_ids = fields.Many2many('res.users', string='Mentioned Users')

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'crm_custom_message_attachment_rel', 'message_id', 'attachment_id',
        string="Attachments",
        help="Attachments related to this message"
    )

    is_system_generated_message = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "changed Expected Revenue from" in vals.get('message', ''):
                vals['is_system_generated_message'] = True

        records = super(CrmLeadCustomMessage, self).create(vals_list)

        for record in records:
            for attachment in record.attachment_ids:
                attachment.write({'public': True})

            record._send_mention_notifications()
        return records

    def _send_mention_notifications(self):
        """Sends notification emails to mentioned users"""

        for record in self:
            lead_url = f"{record.get_base_url()}/web#id={record.lead_id.id}&model=crm.lead&view_type=form"

            for user in record.mentioned_user_ids:
                mail_values = {
                    'email_to': user.email,
                    'subject': f"You were mentioned in an Odoo message",

                    'body_html': f"""
                                    <div style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 15px; 
                                                border-radius: 8px; border: 1px solid #ddd;">
                                        <h2 style="color: #0275d8; text-align: center;">📢 New Mention Notification</h2>
                
                                        <p style="font-size: 14px; color: #333;"><strong>{record.user_id.name}</strong> mentioned you in a message:</p>
                
                                        <div style="background-color: #fff; padding: 10px; border-left: 4px solid #0275d8; 
                                                    font-style: italic; color: #555;">
                                            "{record.message}"
                                        </div>
                
                                        <p style="text-align: center;">
                                            <a href="{lead_url}" style="display: inline-block; padding: 10px 20px; background-color: #0275d8; 
                                            color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📩 View Message</a>
                                        </p>
                
                                        <hr style="background-color: red; height: 3px; border: none;">
                
                                        <p style="color: #999; font-size: 12px; text-align: center;">
                                            © Odoo System | Auto-generated Notification
                                        </p>
                                    </div>
                                """

                }
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()

            # Add the Commercial Manager Login info, for receiving the email notifications of expected revenue changes.
            if record.is_system_generated_message:
                commercial_manager = self.env['res.users'].search([('login', '=', 's.boustan@isalab.eu')], limit=1)
                mail_values = {
                    'email_to': commercial_manager.email,

                    'subject': f"Auto generated Odoo message",

                    'body_html': f"""
                                    <div style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                                        <h2 style="color: #d9534f; text-align: center;">⚠ Important Notification ⚠</h2>
                                        <p style="font-size: 14px; color: #333;">This message is from <strong>Odoo System</strong></p>
                                        <p style="font-size: 16px; font-weight: bold; color: #0275d8;">CRM module: Expected Revenue has been Changed.</p>
                
                                        <p style="text-align: center;">
                                            <a href="{lead_url}" style="display: inline-block; padding: 10px 20px; background-color: #0275d8; color: white; 
                                            text-decoration: none; border-radius: 5px; font-weight: bold;">📂 View Changes</a>
                                        </p>
                
                                        <hr style="background-color: red; height: 3px; border: none;">
                
                                        <p style="color: #555; font-size: 12px; text-align: center;">
                                            This message is <strong>strictly confidential</strong> and intended for you only. If you made these changes, you can ignore this message.
                                        </p>
                
                                        <p style="color: #999; font-size: 12px; text-align: center;">
                                            © Odoo System | Auto-generated Notification
                                        </p>
                                    </div>
                                """

                }
                mail = self.env['mail.mail'].create(mail_values)
                # mail.send()

    def unlink(self):
        for record in self:
            if record.is_system_generated_message or "changed Expected Revenue from" in record.message:
                raise UserError(f"❌\nYou cannot delete this system-generated message. 💻⚙️")
        return super(CrmLeadCustomMessage, self).unlink()

    def write(self, vals):
        for record in self:
            if record.is_system_generated_message or "changed Expected Revenue from" in record.message:
                raise UserError(f"❌\nYou cannot edit this System-generated message. 💻⚙️")
        return super(CrmLeadCustomMessage, self).write(vals)
