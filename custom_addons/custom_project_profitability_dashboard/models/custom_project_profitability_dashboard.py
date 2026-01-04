from odoo import models, fields, api

class CustomProjectProfitabilityDashboard(models.TransientModel):
    """
    Transient model for generating and displaying the Project Profitability Dashboard.
    Integrates HR cost, facilities, taxes, and margin analysis for each project.
    """
    _name = 'custom.project.profitability.dashboard'
    _description = 'Custom Project Profitability Dashboard'

    user_id = fields.Many2one('res.users', string='User')
    total_hours = fields.Float(string='Total Hours')
    hourly_rate = fields.Float(string='Hourly Rate')
    total_payment = fields.Float(string='Total Payment', compute='_compute_total_payment')
    project_id = fields.Many2one('project.project', string='Project')

    @api.depends('total_hours', 'hourly_rate')
    def _compute_total_payment(self):
        """
        Compute the total payment by multiplying total hours with hourly rate.
        """
        for rec in self:
            hours = rec.total_hours if rec.total_hours else 0.0
            rate = rec.hourly_rate if rec.hourly_rate else 0.0
            rec.total_payment = hours * rate

    @api.model
    def generate_report_lines(self, project_id):
        """
        Generate dashboard lines for the profitability report based on timesheet data.
        Calculates total hours and retrieves the hourly rate from the employee's timesheet cost.
        """
        domain = []
        if project_id:
            domain.append(('project_id', '=', project_id))

        # Group timesheet entries by user and sum their worked hours (unit_amount).
        data = self.env['account.analytic.line'].read_group(
            domain,
            ['user_id', 'unit_amount:sum'],
            ['user_id']
        )

        # Remove previous report lines for this project to avoid duplicates.
        existing_lines = self.search([('project_id', '=', project_id)])
        existing_lines.unlink()

        # Retrieve hourly rates from the employee's 'timesheet_cost' field.
        rates = {
            user.id: user.employee_id.timesheet_cost or 0
            for user in self.env['res.users'].browse([d['user_id'][0] for d in data if d['user_id']])
        }

        # Create report lines with the calculated total hours and hourly rates.
        for line in data:
            user_id = line['user_id'][0]
            hours = line['unit_amount']
            rate = rates.get(user_id, 0)
            self.create({
                'user_id': user_id,
                'total_hours': hours,
                'hourly_rate': rate,
                'project_id': project_id,
            })

        # TODO: Handle cases where user has no employee or timesheet_cost defined.
        # Optionally, log a warning or notify the admin.

        # TODO: For large datasets, consider using batch create for performance.
