# -*- coding: utf-8 -*-
{
    'name': "customerInformation_contacts",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Valter Junior",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Contacts',
    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts'],
    
    # always loaded
    'data': [
        'views/views.xml',
        'security/ir.model.access.csv',
        #'views/sale_new_look.xml',
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable' : True,
    'license': 'LGPL-3',
}
