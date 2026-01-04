# -*- coding: utf-8 -*-

#    Stranbys Info Solution. Ltd.
#    ===========================
#    Copyright (C) 2022-TODAY Stranbys Stranbys Info Solution(<https://www.stranbys.com>)
#    Author: Stranbys Info Solution(<https://www.stranbys.com>)

{
    'name': 'Sale Revision-Stranbys',
    'version': "17.0.1.0.0",
    'description': """Revisions and Versions for Sales Orders and Quotations""",
    'author': "Stranbys Info Solutions",
    'depends': ['base', 'sale'],
    'data': [
        'security/stranbys_saleorder_revision_security.xml',
        'security/ir.model.access.csv',
        'views/noupdate.xml',
        'views/sales.xml',
        'wizards/revision_wizard.xml'
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
