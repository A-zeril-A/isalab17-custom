# -*- coding: utf-8 -*-
{
    'name': "Sale Order ARCA Field",

    'summary': "Adds a Float field 'ARCA' to Sale Order form",

    'description': """
        This module extends the Sale Order model by adding a Float field named 'ARCA'.
        The field is positioned below the 'perment_term_id' field in the sale order form.
       """,

    'author': "Iman Gholami",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Sales',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_ex_arca.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
