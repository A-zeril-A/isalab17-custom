# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError


class CustomLead(models.Model):
    _inherit = 'crm.lead'

    # Modified by A_zeril_A, 2025-10-20: Corrected invalid 'stored' parameter to 'store' for Odoo 16 upgrade compatibility.
    main_contact = fields.Boolean(string='Main Contact', store=True, help="Define The Main Contact")


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('custom_crm_lead_extension.custom_group_crm_tag_manager'):
            raise AccessError("You do not have permission to create a tag.")
        return super(CrmTag, self).create(vals_list)
