# -*- coding: utf-8 -*-
{
    'name': "custom_crm_lead_extension",

    'summary': """
        Adds custom fields and functionality to CRM Leads
        """,

    'description': """
        This module extends the CRM Lead model by adding custom fields such as 'Main Contact'.
    """,

    'author': "Iman Gholami",
    'website': "https://github.com/ImanGholamii/Odoo-CRM_extension_01.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/CRM',
    'version': '17.0.1.0.0',
    'license': "LGPL-3",
    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        'security/security_groups.xml',
        'views/crm_lead_view.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'icon': 'custom_crm_lead_extension/static/description/icon.png',
    "installable": True,
    "application": False,
    "auto_install": False
}
