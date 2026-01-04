# -*- coding: utf-8 -*-
{
    'name': "Sale Extension Net Income",

    'summary': """
        Sale Extention Net Income for ISALAB""",

    'description': """
        Long description of module's purpose
    """,

    'author': "H.Shirazi",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '17.0.1.0.0',
    'installable': False,  # Temporarily disabled - needs tax_totals_json field fixes for Odoo 16

    # any module necessary for this one to work correctly
    'depends': ['sale','crm','mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sales_views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [],
    'license': 'LGPL-3',
    'auto_install': False,
    'application': False,
    'installable': True,
}
