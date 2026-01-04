# -*- coding: utf-8 -*-
{
    'name': "CRM Private Chat",

    'summary': """
        Adds a private section in CRM module for Specific Users to have secret chats.
    """,

    'description': """
        This Odoo module extends the crm.lead model to enable private commercial team messages within leads.
         Users can mention others, attach files, and send email notifications when mentioned in a message.
    """,

    'author': "Iman gholami",
    'website': "https://github.com/ImanGholamii/Odoo-CRM-Custom-Private-Message-Section",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Crm',
    'version': '17.0.1.0.0',
    'license': "LGPL-3",

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'mail'],

    # always loaded
    'data': [
        "security/private_custom_note_security.xml",
        "security/ir.model.access.csv",
        "views/custom_crm_views.xml",

    ],

    # only loaded in demonstration mode
    'demo': [
    ],
    "icon": '/crm_private_message/static/description/icon.png',
    "installable": True,
    "application": False,
    "auto_install": False,
}
