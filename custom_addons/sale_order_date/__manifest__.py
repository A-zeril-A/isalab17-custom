# -*- coding: utf-8 -*-
{
    'name': 'Sale Order Date',

    'summary': """
        Displays the order date in the sale order tree view.
        """,

    'description': """
        This module extends the Sale Order tree view to include the 'Order Date' (date_order) field 
        next to the 'Creation Date' (create_date) for better visibility and tracking.
    """,

    'author': "Iman Gholami",
    'website': "",

    'category': 'Sales',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_date.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
