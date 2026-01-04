# -*- coding: utf-8 -*-
{
    'name': "custom.project.profitability.dashboard",

    'summary': """
        Advanced Project Profitability Dashboard with HR Cost Integration
    """,

    'description': """
Custom Project Profitability Dashboard
======================================

This module extends the official Odoo Project module by inheriting and enhancing the Project Updates feature.
It provides a comprehensive profitability dashboard for each project, integrating HR team cost calculation,
facilities costs, taxes, and other financial KPIs directly into the project interface.

Key Features
------------
- Full Integration with Project Updates:** Inherits and customizes the Project Updates functionality from the official Odoo Project module, ensuring seamless user experience.
- HR Team Cost Calculation:** Automatically calculates and reports HR costs per project, based on timesheet data and employee cost rates.
- Profitability & Financial KPIs:** Integrates essential financial indicators (costs, margin, taxes, facilities) into the project dashboard for real-time analysis.
- Custom Security Groups:** Restricts access to sensitive financial data via dedicated security groups, ensuring data privacy and compliance.
- Enhanced User Interface:** Customizes project kanban and update views for improved usability and clarity, including renaming and extending key actions.
- Real-Time Reporting:** All calculations and dashboards are updated in real time, providing project managers with up-to-date insights.

How It Works
------------
- The module inherits the Project Updates feature and injects advanced financial calculations into the project dashboard.
- HR costs are calculated per user based on timesheet entries and employee cost rates.
- Facilities costs, taxes, and other expenses are automatically included in the profitability analysis.
- All enhancements are fully integrated with the standard Odoo Project workflow, requiring no additional configuration.

Intended Audience
-----------------
This module is ideal for organizations seeking real-time insight into project profitability and cost structure, especially those with complex HR and financial requirements.

""",

    'author': "A_zeril_A",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '17.0.1.0.0',
    'installable': False,  # Temporarily disabled - needs field dependency fixes for Odoo 16

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'sale', 'sale_timesheet', 'hr_timesheet', 'analytic', 'account', 'custom_business_trip_management'],
    
    
    'data': [
        'security/groups.xml',              
        'security/ir.model.access.csv',
        'security/project_update_access.xml', 
        'views/custom_project_kanban_button_rename_inherit.xml', 
        'views/custom_project_update_view_rename_inherit.xml',                                                                 
        'views/custom_project_profitability_dashboard_views.xml',
    ],

    'assets': {
        'web.assets_qweb': [
            'custom_project_profitability_dashboard/static/src/xml/sold_section_override.xml',
        ],
    },
    # always loaded
    
    
    'installable': True,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
