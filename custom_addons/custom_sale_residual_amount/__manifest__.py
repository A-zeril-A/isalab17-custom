{
    'name': 'Sale Order Residual Amount',
    'version': '17.0.1.0.0',
    'summary': 'Show remaining amount on Sale Order after invoices',
    'category': 'Sales',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
