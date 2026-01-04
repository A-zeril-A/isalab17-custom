# -*- coding: utf-8 -*-
{
    'name': "Custom Limited CRM Log Note and Views",

    'summary': """
        Restrict log notes in CRM to show only opportunity name and customer name, 
        and provide customized field visibility for general users.
    """,

    'description': """
        This module customizes the CRM log notes by limiting the displayed information 
        to only the opportunity name and customer name, preventing unnecessary details 
        from appearing in the chatter. It also adds restrictions to some fields, 
        making them visible only to specific groups, such as 'CRM Full Access'.
    """,

    'author': "Iman Gholami",
    'website': "https://github.com/ImanGholamii/Odoo_CRM_Limited_views",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'CRM',
    'version': '17.0.1.0.0',
    'installable': False,  # Temporarily disabled - needs xpath fixes for Odoo 16

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'views/crm_lead_views.xml',
        'views/crm_lead_kanban_inherit_views.xml',
        'views/crm_lead_inherit_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'icon': 'custom_limited_crm_log_note_and_views/static/description/icon.png',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
