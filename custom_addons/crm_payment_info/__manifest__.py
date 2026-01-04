{
    'name': 'CRM Payment Info',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'Show paid, unpaid and total contract amount in CRM',
    'description': """
        Adds fields for Total Amount, Paid Amount and Due Amount in CRM leads/opportunities.
        Shows payment information in both form and kanban views.
    """,
    'author': 'sajjad',
    'depends': ['crm', 'account', 'sale', 'sale_crm'],
    'data': [
        'views/crm_lead_view.xml',
        'views/crm_lead_form_hide_expected_revenue.xml',
        'views/crm_lead_kanban.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}