from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class CustomMailWizardInvite(models.TransientModel):
    """
    Inherits the mail wizard to add custom logic for manually adding followers
    to projects and tasks.
    """
    _inherit = 'mail.wizard.invite'

    def add_followers(self):
        """
        Overrides the method to enforce follower restrictions for manual additions.
        - Privileged users (admin, Commercial Directors) can add any contact.
        - Non-privileged users can only add registered system users and will receive
          an error if they attempt to add an external contact.
        """
        if self.res_model in ['project.project', 'project.task']:
            # A_zeril_A, 2025-10-06: Robust privilege check.
            # We now primarily rely on the new security group. The job title check is a fallback.
            is_admin = self.env.user.id == self.env.ref('base.user_admin').id
            is_in_cd_group = self.env.user.has_group('custom_project.group_commercial_director')
            is_cd_by_job = self.env.user.employee_id and self.env.user.employee_id.job_title == 'Commercial Director'

            is_privileged = is_admin or is_in_cd_group or is_cd_by_job

            if not is_privileged:
                external_partners = self.partner_ids.filtered(lambda p: not p.user_ids)
                if external_partners:
                    raise ValidationError(_(
                        "Operation not allowed: Only registered system users can be added as followers.\n\n"
                        "The following contacts are not registered users: %s",
                        ", ".join(external_partners.mapped('name'))
                    ))
            
            # For privileged users, call super with a context flag to bypass the mail.followers check.
            # For non-privileged users adding valid (internal) followers, this also proceeds.
            ctx = self.env.context.copy()
            if is_privileged:
                ctx['allow_external_followers'] = True
            
            return super(CustomMailWizardInvite, self.with_context(ctx)).add_followers()

        return super().add_followers()  
