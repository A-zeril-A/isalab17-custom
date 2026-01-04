from odoo import api, SUPERUSER_ID


# To activate the code in the module installation time, You MUST uncomment the line No.81 in __manifest__.py
def assign_admins_to_existing_projects(cr, registry):
    """ ADD All admin members to existing Projects """
    env = api.Environment(cr, SUPERUSER_ID, {})

    admin_group = env.ref('base.group_system')
    admin_users = admin_group.users

    projects = env['project.project'].search([])

    for project in projects:
        existing_followers = project.message_partner_ids
        missing_admins = admin_users.filtered(lambda u: u.partner_id not in existing_followers)

        if missing_admins:
            project.message_subscribe(partner_ids=missing_admins.mapped('partner_id').ids)
