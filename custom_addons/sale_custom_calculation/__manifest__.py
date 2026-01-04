{
    'name': 'Sale Order Custom Calculation',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom calculation for sale order lines',
    'description': """
        This module changes sale order line calculation:
        - User enters Quantity and Subtotal
        - Unit Price is calculated automatically
        - Better user experience for sales operations
    """,
    'author': 'sajjad',
    'depends': ['sale', 'sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],

    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}