# -*- coding: utf-8 -*-
{
    'name': "purchase_management",

    'summary': """
        The Purchase Management module in Odoo 15 streamlines procurement
        by enabling control, approval, and efficient tracking of purchase orders,
        with automated delegation to designated purchasers""",

    'description': """
        The Purchase Management module for Odoo 15 streamlines procurement
        by allowing responsible individuals to control and approve purchase orders, 
        which are then sent to designated purchasers for execution.
        It ensures efficient tracking, role-specific permissions, and timely notifications to enhance the purchasing process
    """,

    'author': "H.Shirazi",
    'website': "zeta-lab.it",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['mail', 'product', 'sale'],

    # always loaded
    'data': [
        'data/activity.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'wizard/refuse_purchase_view.xml',
        'views/menu.xml',
        'data/sequence.xml',
        'views/purchase_management.xml',
        'views/purchase_categ.xml',
        'views/product.xml',
        'views/purchase_office.xml',
        'views/setting_view.xml',
        'views/purchase_limit_wizard_views.xml',
        'data/email_template_data.xml',
    ],
    # assets
    'assets': {
        'web.assets_backend': [
            'purchase_management/static/src/css/custom_styles.css',
        ],
    },
    # only loaded in demonstration mode
    'demo': [],
    'license': 'LGPL-3',
    'auto_install': False,
    'application': True,
    'installable': True,

}
