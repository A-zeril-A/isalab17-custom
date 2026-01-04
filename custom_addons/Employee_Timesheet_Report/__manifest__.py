{
    'name': 'Employee Timesheet Report',
    'version': '17.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Report for Employee Timesheet with start/end time and total duration',
    'author': 'sajjad',
    'depends': ['hr_timesheet', 'web'],

    'data': [
        'views/timesheet_report_views.xml',
        'security/ir.model.access.csv',
    ],

    'controllers': [
        'controllers/timesheet_report_controller.py'
    ],


    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
