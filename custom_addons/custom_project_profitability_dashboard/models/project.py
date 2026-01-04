"""
This file extends the core Odoo Project module by inheriting the Project Updates feature.
It adds a comprehensive profitability dashboard, including HR cost calculation, facilities, taxes,
and margin analysis, directly into the project interface.

Note:
- The 'project.project' model is inherited to inject advanced financial KPIs.
- The Project Updates action and views are customized for enhanced reporting and usability.
- All enhancements are fully integrated with the standard Odoo Project Updates workflow.
"""

from odoo import api, models, fields
from odoo.tools import format_amount
import json

class Project(models.Model):
    _inherit = 'project.project'

    # 1. Stored Profitability Fields for Performance
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency')
    x_net_value = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Untaxed Amount")
    x_total_hr_cost = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="HR Costs")
    x_facilities_cost = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Facilities Costs")
    x_travel_lodging = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Travel & Lodging")
    x_other_costs = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Other Costs")
    x_final_margin = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Final Margin")
    x_total_taxes = fields.Monetary(
        compute='_compute_profitability_metrics', store=True, currency_field='company_currency_id', string="Total Taxes")
    x_hr_cost_warning = fields.Text(
        compute='_compute_profitability_metrics', store=True, string="HR Cost Warning")

    @api.depends(
        'timesheet_ids.unit_amount',
        'timesheet_ids.employee_id.timesheet_cost',
        'sale_order_id.order_line', 
        'sale_order_id.custom_total_net_sum',
        'sale_order_id.business_trip_ids.final_total_cost'
    )    
    def _compute_profitability_metrics(self):
        """
        Computes all profitability metrics and stores them.
        This method is triggered when the underlying analytic lines (timesheets, invoice lines) change.
        """
        for project in self:
            sale_orders = project._get_sale_orders()
            
            # --- HR Cost Calculation (Self-Contained Logic) ---
            timesheet_data = self.env['account.analytic.line'].read_group(
                [('project_id', '=', project.id), ('employee_id', '!=', False)],
                ['unit_amount:sum', 'employee_id'],
                ['employee_id'],
                lazy=False
            )
            total_hr_cost = 0.0
            employees_without_cost = []
            
            if timesheet_data:
                employee_ids = [d['employee_id'][0] for d in timesheet_data]
                employee_costs = {emp.id: emp.timesheet_cost for emp in self.env['hr.employee'].browse(employee_ids)}
                for line in timesheet_data:
                    employee_id = line['employee_id'][0]
                    employee_name = line['employee_id'][1]
                    hours = line['unit_amount']
                    rate = employee_costs.get(employee_id, 0)
                    if not rate:
                        employees_without_cost.append(str(employee_name))
                    total_hr_cost += hours * rate
            
            project.x_total_hr_cost = total_hr_cost
            
            # Set warning message for employees without timesheet cost
            if employees_without_cost:
                unique_names = sorted(list(set(employees_without_cost)))
                project.x_hr_cost_warning = """


The following employees have zero hourly rates, which may affect the accuracy of HR cost calculations:

• %s

Please verify and update their timesheet costs in the HR module to ensure accurate project profitability analysis.
                """.strip() % "\n• ".join(unique_names)
            else:
                project.x_hr_cost_warning = False
            
            # --- Other Metrics Calculation ---
            project.x_facilities_cost = total_hr_cost * 0.15 # Hardcoded value, to be improved next.

            project.x_net_value = sum(order.amount_untaxed for order in sale_orders)
            project.x_total_taxes = sum(order.amount_tax for order in sale_orders)
            project.x_other_costs = sum(order.custom_total_net_sum for order in sale_orders if hasattr(order, 'custom_total_net_sum'))
            
            # Travel & Lodging (safe check for formio module)
            travel_lodging = 0.0
            if 'business.trip' in self.env:
                try:
                    # Define the states for which costs should be included
                    valid_trip_states = [
                        'organization_done',        # Organization Completed
                        'in_progress',              # Travel in Progress
                        'completed_waiting_expense',# Awaiting Travel Expenses
                        'expense_submitted',        # Expenses Under Review
                        'completed'                 # TRAVEL PROCESS COMPLETED
                    ]
                    
                    # Build search domain to find all business trips related to this project
                    trip_domain = [
                        ('trip_status', 'in', valid_trip_states),
                        '|', '|',
                        # Trips linked via sale orders
                        ('sale_order_id', 'in', sale_orders.ids if sale_orders else []),
                        # Standalone trips linked directly to this project
                        ('selected_project_id', '=', project.id),
                        # Trips where project was created for business trip
                        ('business_trip_project_id', '=', project.id),
                    ]
                    
                    related_trips = self.env['business.trip'].search(trip_domain)
                    
                    # Sum the final_total_cost from the retrieved trips
                    travel_lodging = sum(related_trips.mapped('final_total_cost'))

                except Exception:
                    # If any error occurs, set travel_lodging to 0
                    travel_lodging = 0.0
            project.x_travel_lodging = travel_lodging

            project.x_final_margin = project.x_net_value - (project.x_total_hr_cost + project.x_facilities_cost + project.x_travel_lodging + project.x_other_costs)

    def action_open_payment_report(self):
        """
        Open a popup window showing the Summary of HR Costs report for the current project.
        """
        self.ensure_one()
        # Generate or refresh report lines for this project
        self.env['custom.project.profitability.dashboard'].generate_report_lines(self.id)
        return {
            'name': 'Summary of HR Costs',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.project.profitability.dashboard',
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def get_panel_data(self):
        """
        Extend the project panel data to include profitability breakdown.
        This data is now read from stored computed fields for maximum performance.
        """
        self.ensure_one()
        
        # Force recomputation of profitability metrics to ensure up-to-date values
        self._compute_profitability_metrics()
        
        data = super().get_panel_data()

        # Add a custom button for Summary of HR Costs with updated HR cost value
        data['buttons'].append({
            'text': 'Summary of HR Costs',
            'icon': 'money',
            'action': 'action_open_payment_report',
            'action_type': 'object',
            'show': True,
            'order': 99,
            'number': format_amount(self.env, self.x_total_hr_cost or 0.0, self.company_id.currency_id),
            'additional_context': json.dumps({'default_project_id': self.id}),
        })

        # Prepare profitability data for the UI from the new stored fields
        profit_data = [
            {'name': 'Untaxed Amount', 'value': format_amount(self.env, self.x_net_value, self.company_id.currency_id), 'color': ''},
            {'name': 'HR Costs', 'value': format_amount(self.env, -self.x_total_hr_cost, self.company_id.currency_id), 'color': 'red' if self.x_total_hr_cost else ''},
            {'name': 'Facilities Costs', 'value': format_amount(self.env, -self.x_facilities_cost, self.company_id.currency_id), 'color': 'red' if self.x_facilities_cost else ''},
            {'name': 'Travel & Lodging', 'value': format_amount(self.env, -self.x_travel_lodging, self.company_id.currency_id), 'color': 'red' if self.x_travel_lodging else ''},
            {'name': 'Other Costs', 'value': format_amount(self.env, -self.x_other_costs, self.company_id.currency_id), 'color': 'red' if self.x_other_costs else ''},
            {'name': 'Margin', 'value': format_amount(self.env, self.x_final_margin, self.company_id.currency_id), 'color': 'green' if self.x_final_margin > 0 else ('red' if self.x_final_margin < 0 else ''), 'bold': True},
            {'name': 'Taxes', 'value': format_amount(self.env, self.x_total_taxes, self.company_id.currency_id), 'color': 'yellow' if self.x_total_taxes else ''},
        ]
        
        # Add HR cost warning if exists with improved styling
        if self.x_hr_cost_warning:
            # Add some spacing before the warning
            profit_data.append({
                'name': '─' * 50,  # Separator line
                'value': '', 
                'color': 'muted',
                'separator': True
            })
            profit_data.append({
                'name': '⚠️ HR Cost Alert', 
                'value': self.x_hr_cost_warning, 
                'color': 'warning',
                'bold': True,
                'warning': True,
                'style': 'background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0;'
            })
            # Add spacing after the warning
            profit_data.append({
                'name': '─' * 50,  # Separator line
                'value': '', 
                'color': 'muted',
                'separator': True
            })

        if 'profitability_items' in data:
            data['profitability_items']['data'] = profit_data
            # Add HR cost warning to profitability data
            data['profitability_items']['hr_cost_warning'] = self.x_hr_cost_warning or False

        return data



    def _get_stat_buttons(self):
        """
        Override the default stat buttons to rename 'Gross Margin' to 'Detailed HR Costs' and update its value.
        """
        buttons = super()._get_stat_buttons()
        for button in buttons:
            if str(button['text']) == 'Gross Margin':
                button['text'] = 'Detailed HR Costs'
                # Update the button value to show actual HR costs instead of gross margin
                button['number'] = format_amount(self.env, self.x_total_hr_cost or 0.0, self.company_id.currency_id)
        return buttons

    def _get_sale_orders(self):
        """
        Override to include both sale order lines and direct sale orders.
        This ensures projects linked directly to sale orders (not just via sale lines) are included.
        """
        sale_orders = super()._get_sale_orders()
        # Also include direct sale order connections
        if self.sale_order_id:
            sale_orders |= self.sale_order_id
        
        # Additional fallback: search by project name if no direct links found
        if not sale_orders:
            sale_orders = self.env['sale.order'].search([('name', '=', self.name)], limit=1)
        
        return sale_orders

    # TODO: For future improvements, consider making the facilities cost percentage configurable from settings.
    # TODO: Log a warning when a user has no defined timesheet_cost

class CustomProjectProfitabilityDashboard(models.TransientModel):
    _name = 'custom.project.profitability.dashboard'
    _description = 'Custom Project Profitability Dashboard'
    # ...