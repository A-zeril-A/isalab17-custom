from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError, UserError
from odoo.tools import formataddr
import logging

_logger = logging.getLogger(__name__)


class CustomProjectTask(models.Model):
    _inherit = 'project.task'
    user_id = fields.Many2one('res.users', string='Assigned to', ondelete='set null')

    planned_hours = fields.Float("Initially Planned Hours",
                                 help='Time planned to achieve this task (including its sub-tasks).',
                                 tracking=True)

    planned_hours_readonly = fields.Boolean(compute="_compute_planned_hours_readonly")

    # Mar 03
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks")

    # end

    # Allocated Hours to Employees
    allocation_ids = fields.One2many(
        'project.task.allocation',
        'task_id',
        string="Employee Allocations",
        help="Distribute the planned hours among the assigned employees."
    )

    allocated_hours_current_employee = fields.Float(
        string="Your Allocated Hours",
        compute="_compute_allocated_hours",
        store=False
    )

    total_project_hours = fields.Float(
        string="Total Project Hours",
        readonly=True,
        compute="_compute_total_project_hours",
        help="Total allocated hours for this project, defined by the Director, Manager or Admin."
    )

    project_state = fields.Selection(
        related='project_id.state',
        string="Project State",
        readonly=True,
        store=False,
    )

    overtime_request_ids = fields.One2many('overtime.request', 'task_id', string="Overtime Requests")

    # Mar 03
    allocated_hours_total = fields.Float(
        string="Total Allocated Hours",
        compute="_compute_allocated_hours_total",
        store=True
    )
    subtask_hours_total = fields.Float(
        string="Total Subtask Hours",
        compute="_compute_subtask_hours_total",
        store=True
    )
    remaining_hours_for_subtasks = fields.Float(
        string="Remaining Hours for Subtasks",
        compute="_compute_remaining_hours_for_subtasks",
        store=True
    )
    # end
    # Mar 09
    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one(
        'res.users', related='project_id.user_id', string='Project Manager (from Project)', readonly=True)
    technical_director_id = fields.Many2one(
        'res.users', related='project_id.technical_director_id', string='Project Director', readonly=True)
    show_allocation = fields.Boolean(compute='_compute_show_allocation')

    # Added by A_zeril_A on Aug 25, 2025
    # This field calculates the remaining project hours AFTER accounting for the current task's planned hours.
    # It shows the budget left for future top-level tasks.
    project_available_hours = fields.Float(
        string="Project Available Hours",
        compute='_compute_project_available_hours',
        help="Shows the remaining hours in the project for other future tasks."
    )


    # Field to show parent task hierarchy
    parent_task_hierarchy = fields.Char(
        string='Parent Task Hierarchy',
        compute='_compute_parent_task_hierarchy',
        help="Shows the hierarchy of parent tasks"
    )


    @api.depends('parent_id', 'parent_id.parent_id', 'parent_id.name')
    def _compute_parent_task_hierarchy(self):
        """
        Computes a string showing the full hierarchy of parent tasks.
        Example: "Main Task > Sub Task 1 > Sub Task 2"
        """
        for task in self:
            if not task.parent_id:
                task.parent_task_hierarchy = False
            else:
                hierarchy = []
                current = task.parent_id
                # Build the hierarchy from bottom to top
                while current:
                    hierarchy.insert(0, current.name)
                    current = current.parent_id
                # Join with arrow separator
                task.parent_task_hierarchy = ' > '.join(hierarchy)



    # End
    def _compute_planned_hours_readonly(self):
        for task in self:
            # task.planned_hours_readonly = task.create_uid != self.env.user
            is_admin = self.env.user.has_group("base.group_system")
            task.planned_hours_readonly = not (
                    is_admin or
                    task.create_uid == self.env.user or
                    task.user_id == self.env.user or
                    task.technical_director_id == self.env.user
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'planned_hours' not in vals or not vals['planned_hours']:
                raise ValidationError(
                    "Please to define new Tasks, First Set the Task Planned Hours(notebook: Timesheet >> Task Planned Hours)")
            elif 'planned_hours' not in vals or not vals['planned_hours']:
                parent_task = self.browse(vals.get('parent_id'))
                if parent_task:
                    vals['planned_hours'] = parent_task.planned_hours

        # If a task is created with assignees, ensure allocation records are also created.
        tasks = super(CustomProjectTask, self).create(vals_list)
        
        for task, vals in zip(tasks, vals_list):
            if not self.env.context.get('syncing_from_allocation') and 'user_ids' in vals:
                # When creating a task, user_ids are provided as commands, not a recordset.
                # We extract the user IDs from the commands to create the allocations.
                user_ids_to_add = []
                for command in vals['user_ids']:
                    # The command (6, 0, [IDs]) replaces the list with new IDs.
                    if command[0] == 6:
                        user_ids_to_add.extend(command[2])
                    # The command (4, ID, 0) adds a single ID.
                    elif command[0] == 4:
                        user_ids_to_add.append(command[1])
                
                if user_ids_to_add:
                    alloc_vals = [{
                        'task_id': task.id,
                        'employee_id': user_id,
                        'allocated_hours': 0.0,
                    } for user_id in user_ids_to_add]
                    self.env['project.task.allocation'].with_context(syncing_from_user=True).create(alloc_vals)

            # Changed by A_zeril_A on Aug 25, 2025
            # The project hour limit check should only apply to TOP-LEVEL tasks.
            # This prevents validation errors when creating sub-tasks, as their hours
            # are constrained by the parent task, not the project directly.
            if not task.parent_id and task.project_id:
                project = task.project_id
                top_level_tasks = project.task_ids.filtered(lambda t: not t.parent_id)
                total_task_hours = sum(top_level_tasks.mapped('planned_hours'))

                if total_task_hours > project.allocated_hours:
                    allocated_hours_int = int(project.allocated_hours)
                    allocated_minutes = int((project.allocated_hours - allocated_hours_int) * 60)
                    allocated_time_str = f"{allocated_hours_int:02d}:{allocated_minutes:02d}"
                    raise ValidationError(
                        f"The total planned hours for tasks in this project exceed the allocated limit of {allocated_time_str} hours."
                    )
            if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
                raise ValidationError(
                    f"Total allocated hours and subtask hours cannot exceed the planned hours for this task!"
                )
        # task._sync_users_with_followers()
        # task._sync_followers_with_users()
        # Mar 05
        return tasks

    @api.depends('allocation_ids.allocated_hours', 'allocation_ids.employee_id')
    def _compute_allocated_hours(self):
        user = self.env.user
        employee = self.env['res.users'].search([('user_ids', '=', user.id)], limit=1)

        for task in self:
            if employee:
                allocation = task.allocation_ids.filtered(lambda a: a.employee_id == employee)
                task.allocated_hours_current_employee = sum(allocation.mapped('allocated_hours'))
            else:
                task.allocated_hours_current_employee = 0.0

    @api.depends('project_id')
    def _compute_total_project_hours(self):
        for task in self:
            task.total_project_hours = task.project_id.allocated_hours if task.project_id else 0.0

    @api.constrains('planned_hours', 'child_ids')
    def _check_subtask_hours(self):
        for task in self:
            if task.child_ids:
                total_subtask_hours = sum(task.child_ids.mapped('planned_hours'))
                if total_subtask_hours > task.planned_hours:
                    raise ValidationError(
                        _(f"❌\nThe total planned hours of subtasks cannot exceed the Task Planned Hours of the main task.")
                    )

    def unlink(self):
        """Allow task deletion, bypassing 'mail.followers' restriction"""
        return super(CustomProjectTask, self.with_context(allow_task_delete=True)).unlink()

    @api.depends("allocation_ids.allocated_hours")
    def _compute_allocated_hours_total(self):
        """ Calculation of total allocated_hours """
        for task in self:
            task.allocated_hours_total = sum(task.allocation_ids.mapped("allocated_hours"))

    @api.depends("child_ids.planned_hours")
    def _compute_subtask_hours_total(self):
        """ Calculate the total planned_hours of all subtasksا """
        for task in self:
            task.subtask_hours_total = sum(task.child_ids.mapped("planned_hours"))

    @api.constrains("subtask_hours_total", "allocated_hours_total")
    def _check_task_hours_limit(self):
        """ Checking the limit of total allocated hours and subtasks """
        for task in self:
            if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
                raise ValidationError(
                    f"❌\nTotal allocated hours and subtask hours cannot exceed the planned hours for this task!\n"
                )

    # alireza Apr 14, 2025
    # better delete this function
    def write(self, vals):
        """
        Overrides the write method to add validation for planned hours.
        - Validates that the total planned hours of top-level tasks do not exceed the project's allocated hours.
        - Validates that the total hours of sub-tasks do not exceed the parent task's planned hours.
        """
        # A_zeril_A, 2025-10-06: Two-way synchronization logic.
        # Prevents loops and handles sync when user_ids are changed from the main field.
        if self.env.context.get('syncing_from_allocation'):
            return super().write(vals)

        # Original validation logic from the module
        old_planned_hours_map = {}
        if 'planned_hours' in vals:
            for task in self:
                # --- Start of New Validation Logic ---
                project = task.project_id
                if project:
                    # 1. Access Control Check
                    commercial_director = self.env['hr.employee'].search([('job_title', '=', 'Commercial Director')], limit=1).user_id
                    allowed_users = [
                        project.technical_director_id,
                        project.user_id,
                        commercial_director
                    ]
                    
                    is_admin = self.env.user.login == 'admin'
                    current_user_is_allowed = self.env.user in allowed_users

                    if not is_admin and not current_user_is_allowed:
                        raise AccessError(_(
                            "You do not have permission to change Planned Hours. "
                            "Allowed users are: Project Director, Project Manager, Commercial Director, or Admin."
                        ))

                    # 2. Pre-condition Checks with specific messages
                    # if not project.date_start:
                    #     raise ValidationError(_(
                    #         "Cannot set Planned Hours because the Project's Start Date is not set. "
                    #         "Please ask the Project Director to set this date first."
                    #     ))
                    # if not project.date:
                    #     raise ValidationError(_(
                    #         "Cannot set Planned Hours because the Project's End Date is not set."
                    #     ))
                    # if project.date_start == project.date:
                    #     raise ValidationError(_(
                    #         "Cannot set Planned Hours because the Project's Start Date and End Date are the same. "
                    #         "Please correct the project dates before proceeding."
                    #     ))
                # --- End of New Validation Logic ---

                old_planned_hours_map[task.id] = task.planned_hours

        res = super().write(vals)

        # A_zeril_A, 2025-10-06: Reworked sync logic.
        # This logic now ensures full synchronization on every write involving 'user_ids',
        # fixing issues with existing unsynced data.
        if 'user_ids' in vals:
            for task in self:
                target_users = task.user_ids
                current_alloc_users = task.allocation_ids.mapped('employee_id')

                # Users to ADD to allocations (present in user_ids but not in allocations)
                users_to_add = target_users - current_alloc_users
                if users_to_add:
                    alloc_vals_to_create = [{
                        'task_id': task.id,
                        'employee_id': user.id,
                        'allocated_hours': 0,
                    } for user in users_to_add]
                    self.env['project.task.allocation'].with_context(syncing_from_user=True).create(alloc_vals_to_create)

                # Allocations to REMOVE (present in allocations but not in user_ids)
                users_to_remove = current_alloc_users - target_users
                if users_to_remove:
                    allocs_to_remove = task.allocation_ids.filtered(lambda a: a.employee_id in users_to_remove)
                    if allocs_to_remove:
                        allocs_to_remove.with_context(syncing_from_user=True).unlink()
        
        # Post chatter message on planned_hours change
        if 'planned_hours' in vals and res:
            for task in self:
                old_hours_float = old_planned_hours_map.get(task.id)
                new_hours_float = task.planned_hours
                if old_hours_float is not None and old_hours_float != new_hours_float:
                    def float_to_time_str(hours_float):
                        hours = int(hours_float)
                        minutes = round((hours_float - hours) * 60)
                        return f"{hours:02d}:{minutes:02d}"

                    old_hours_str = float_to_time_str(old_hours_float)
                    new_hours_str = float_to_time_str(new_hours_float)

                    subject = f"Task Planned Hours Updated"
                    body = f'''
                        <div style="font-family: Arial, sans-serif; border-left: 5px solid #28a745; padding: 12px; margin-bottom: 12px; background-color: #e9f7ef;">
                            <p style="font-size: 16px; font-weight: bold; color: #155724; margin-top: 0;">
                                <i class="fa fa-clock-o"></i> Planned Hours Updated
                            </p>
                            <p>The planned hours for this task were updated by <strong>{self.env.user.name}</strong>.</p>
                            <hr style="border-top: 1px solid #a3d9b1; border-bottom: none;"/>
                            <p style="margin: 0;"><strong>Previous Hours:</strong> {old_hours_str}</p>
                            <p style="margin: 0;"><strong>New Hours:</strong> <span style="font-weight: bold;">{new_hours_str}</span></p>
                        </div>
                    '''
                    task.message_post(
                        body=body,
                        subject=subject,
                        subtype_xmlid='mail.mt_note',  # Internal note, no email to followers
                        author_id=self.env.ref('base.partner_root').id
                    )

        # Project-level validation: only triggers if the 'planned_hours' of a top-level task is being modified.
        # This prevents the check from running incorrectly when the write is triggered by adding a sub-task.
        if 'planned_hours' in vals:
            for task in self.filtered(lambda t: not t.parent_id and t.project_id):
                project = task.project_id
                top_level_tasks = self.env['project.task'].search([
                    ('project_id', '=', project.id),
                    ('parent_id', '=', False)
                ])
                total_task_hours = sum(top_level_tasks.mapped('planned_hours'))

                if total_task_hours > project.allocated_hours:
                    allocated_hours_int = int(project.allocated_hours)
                    allocated_minutes = int((project.allocated_hours - allocated_hours_int) * 60)
                    allocated_time_str = f"{allocated_hours_int:02d}:{allocated_minutes:02d}"
                    raise ValidationError(
                        f"The total planned hours for tasks in this project exceed the allocated limit of {allocated_time_str} hours."
                    )

        # Task-level validation for sub-tasks.
        for task in self:
            # We refresh the task record to ensure the computed field 'subtask_hours_total'
            # is up-to-date after a potential sub-task has been added or modified via the parent task's write.
            task.refresh()
            if task.subtask_hours_total + task.allocated_hours_total > task.planned_hours:
                raise ValidationError(
                    f"Total allocated hours and subtask hours cannot exceed the planned hours for this task!"
                )
        return res

    @api.depends("planned_hours", "allocated_hours_total", "subtask_hours_total")
    def _compute_remaining_hours_for_subtasks(self):
        """ Calculating the amount of time remaining for subtasks """
        for task in self:
            allocated_and_subtask_hours = task.allocated_hours_total + task.subtask_hours_total
            task.remaining_hours_for_subtasks = max(task.planned_hours - allocated_and_subtask_hours, 0)

    # Added by A_zeril_A on Aug 25, 2025
    # This compute method calculates the remaining project budget after the current task's
    # planned hours have been accounted for. It provides a view of the budget left for other tasks.
    @api.depends('planned_hours', 'project_id')
    def _compute_project_available_hours(self):
        for task in self:
            if not task.project_id or task.parent_id:
                # Calculation is only relevant for top-level tasks.
                task.project_available_hours = 0.0
                continue

            project = task.project_id
            # We search for ALL top-level tasks in the project to calculate the total used hours.
            all_top_level_tasks = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('parent_id', '=', False),
                ('id', '!=', task._origin.id)
            ])
            other_tasks_hours = sum(all_top_level_tasks.mapped('planned_hours'))

            # We add the current task's (potentially unsaved) planned_hours to the sum.
            current_total_hours = other_tasks_hours + task.planned_hours

            task.project_available_hours = project.allocated_hours - current_total_hours



    @api.depends('project_id.user_id', 'project_id.technical_director_id')
    def _compute_show_allocation(self):
        for record in self:
            user = self.env.user
            is_admin = user.has_group('base.group_system')

            if (record.project_id.user_id.id == user.id or
                    record.project_id.technical_director_id.id == user.id or
                    is_admin):
                record.show_allocation = True
            else:
                record.show_allocation = False


class CustomProjectProject(models.Model):
    _inherit = 'project.project'

    user_id = fields.Many2one(
        'res.users', string='Project Manager',
        default=lambda self: self.env.user,
        tracking=True
    )

    technical_director_id = fields.Many2one(
        'res.users',
        string="Director",
        help="Responsible for defining the project and assigning the Project Manager.",
        tracking=True
    )

    allocated_hours = fields.Float(
        string="Allocated Hours",
        default=0.0,
        help="Maximum allowed hours for tasks in this project."
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string="State", default='draft', tracking=True)

    completed_at = fields.Datetime(string="Completed At", readonly=True)

    # warning_message = fields.Html(string="Warning Message", readonly=True)

    total_task_hours = fields.Float(
        string="Total Task Hours",
        compute='_compute_total_task_hours',
        help="Sum of planned hours of all top-level tasks in this project."
    )

    def _compute_total_task_hours(self):
        for project in self:
            top_level_tasks = project.task_ids.filtered(lambda t: not t.parent_id)
            project.total_task_hours = sum(top_level_tasks.mapped('planned_hours'))

    def mark_as_completed(self):
        for project in self:

            if project.technical_director_id and self.env.user == project.technical_director_id or self.env.user.has_group(
                    'base.group_system'):
                project.write({
                    'state': 'completed',
                    'completed_at': fields.Datetime.now()
                })
            else:
                raise AccessError("You do not have the permission to mark this project as completed.")

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_completed(self):
        self.write({
            'state': 'completed',
            'completed_at': fields.Datetime.now()
        })

    @api.constrains('technical_director_id')
    def _check_technical_director(self):
        if not self.technical_director_id:
            raise ValidationError("Director is required to create a project.")

    @api.constrains('user_id')
    def _check_project_manager(self):
        for record in self:
            if not record.user_id:
                raise ValidationError(
                    "The Project Manager must be selected by the Director or Administrator.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'project_id' in vals:
                project = self.env['project.project'].browse(vals['project_id'])
                if project.user_id.id != self.env.user.id:
                    raise AccessError("Only the Project Manager can create tasks for this project.")

        projects = super(CustomProjectProject, self).create(vals_list)
        
        # if 'technical_director_id' in vals:
        #     user = self.env['res.users'].browse(vals['technical_director_id'])
        #     group = self.env.ref('custom_project.group_project_director')
            # if user and group and user not in group.users:  # Add the User to the group Automatically.
            #     group.users = [(4, user.id)]

        followers_group = self.env.ref('custom_project.group_followers_all_projects', raise_if_not_found=False)
        
        for project, vals in zip(projects, vals_list):
            if project.state == 'completed':
                project.completed_at = fields.Datetime.now()

            # Mar 03 >> Force adding admin users and followers_group to all projects
            # admin_group = self.env.ref('base.group_system')
            # admin_users = admin_group.users
            #
            # project.message_subscribe(partner_ids=admin_users.mapped('partner_id').ids)

            # Mar 03 >> Force adding followers_group to all projects
            if followers_group:
                followers_users = followers_group.users
                project.message_subscribe(partner_ids=followers_users.mapped('partner_id').ids)

            # Mar 05 >> Adding Director to Followers
            if vals.get('technical_director_id'):
                project.message_subscribe(partner_ids=[project.technical_director_id.partner_id.id])

        return projects
        # end

    # @api.onchange('technical_director_id')
    # def _onchange_technical_director_id(self):
    #     if self.technical_director_id:
    #         self.warning_message = """
    #                         <div style="color: ##101010; font-weight: bold; text-align: center; display: flex;
    #                          justify-content: center; align-items: center; flex-direction: column;">
    #                             <img src="data:image/png;base64,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" alt="information">
    #                             <p>Please be careful.<br>The selected User will be added to
    #                              <span style="color: #460880">Project Director</span> Groups.</p>
    #                         </div>
    #                     """

    def write(self, vals):
        # Add security check: Only the project director or the specific 'admin' user can change the allocated hours.
        old_hours_map = {}
        old_start_date_map = {}

        # Pre-computation and Access Checks for controlled projects
        for project in self:
            # Handle 'start_date' changes for controlled projects
            if 'date_start' in vals:
                # 1. Access Control: Only the Technical Director or the 'admin' user can change the start date.
                if self.env.user.login != 'admin' and self.env.user != project.technical_director_id:
                    raise AccessError(_("Only the Project Director or the 'admin' user can change the project's start date."))
                
                # Store old value for notification
                old_start_date_map[project.id] = project.date_start

            # Handle 'allocated_hours' changes for controlled projects
            if 'allocated_hours' in vals:
                # Store old value for notification later
                old_hours_map[project.id] = project.allocated_hours

                # Find the commercial director(s) by job title
                commercial_director_employee = self.env['hr.employee'].search([('job_title', '=', 'Commercial Director')], limit=1)
                commercial_director_user = commercial_director_employee.user_id if commercial_director_employee else self.env['res.users']

                is_commercial_director = self.env.user == commercial_director_user

                if self.env.user.login != 'admin' and self.env.user != project.technical_director_id and not is_commercial_director:
                    raise AccessError(_("Only the Project Director, Commercial Director, or the system administrator can change the project's allocated hours."))

                # Ensure new allocated hours are not less than the sum of existing task hours.
                new_allocated_hours = vals.get('allocated_hours')
                if new_allocated_hours is not None:
                    top_level_tasks = self.env['project.task'].search([
                        ('project_id', '=', project.id),
                        ('parent_id', '=', False)
                    ])
                    total_task_hours = sum(top_level_tasks.mapped('planned_hours'))

                    if new_allocated_hours < total_task_hours:
                        raise ValidationError(
                            f"Cannot set allocated hours to {new_allocated_hours:.2f}. "
                            f"It is less than the total planned hours of tasks ({total_task_hours:.2f})."
                        )

        res = super(CustomProjectProject, self).write(vals)

        # === Post-write Notifications ===
        # Loop again after the write is successful to send notifications
        for project in self:
            # Notification for 'start_date' change
            if 'date_start' in vals and res:
                new_date = vals['date_start']
                old_date = old_start_date_map.get(project.id)
                new_date_obj = fields.Date.to_date(new_date) if new_date else None

                if old_date != new_date_obj:
                    subject = f"Project Start Date Updated for '{project.name}'"
                    body = f'''
                        <div style="font-family: Arial, sans-serif; border-left: 5px solid #3498db; padding: 12px; margin-bottom: 12px; background-color: #eaf2f8;">
                            <p style="font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 0;">
                                <i class="fa fa-calendar"></i> Project Start Date Updated
                            </p>
                            <p>The start date for project <strong>{project.name}</strong> was updated by <strong>{self.env.user.name}</strong>.</p>
                            <hr style="border-top: 1px solid #aed6f1; border-bottom: none;"/>
                            <p style="margin: 0;"><strong>Previous Date:</strong> {old_date.strftime('%Y-%m-%d') if old_date else 'Not Set'}</p>
                            <p style="margin: 0;"><strong>New Date:</strong> <span style="font-weight: bold;">{new_date_obj.strftime('%Y-%m-%d') if new_date_obj else 'Not Set'}</span></p>
                        </div>
                    '''
                    project.message_post(body=body, subject=subject, subtype_xmlid='mail.mt_note', author_id=self.env.ref('base.partner_root').id)

                    partner_ids_to_notify = []
                    commercial_director = self.env['hr.employee'].search([('job_title', '=', 'Commercial Director')], limit=1).user_id
                    if commercial_director:
                        partner_ids_to_notify.append(commercial_director.partner_id.id)
                    admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
                    if admin_user:
                        partner_ids_to_notify.append(admin_user.partner_id.id)

                    if partner_ids_to_notify:
                        odoo_bot = self.env.ref('base.partner_root')
                        email_from = formataddr((odoo_bot.name, odoo_bot.email or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.address')))
                        for partner_id in list(set(partner_ids_to_notify)):
                            recipient_partner = self.env['res.partner'].browse(partner_id)
                            if recipient_partner.email:
                                self.env['mail.mail'].create({
                                    'subject': subject, 'body_html': body, 'email_from': email_from,
                                    'email_to': recipient_partner.email, 'author_id': odoo_bot.id,
                                    'model': 'project.project', 'res_id': project.id, 'auto_delete': True
                                }).send()

            # Notification for 'allocated_hours' change
            if 'allocated_hours' in vals and res:
                new_hours_float = vals['allocated_hours']
                old_hours_float = old_hours_map.get(project.id)
                
                if old_hours_float is not None and old_hours_float != new_hours_float:
                    # Helper function to format float to HH:MM string
                    def float_to_time_str(hours_float):
                        if hours_float is None: return "N/A"
                        hours, minutes = int(hours_float), round((hours_float - int(hours_float)) * 60)
                        return f"{hours:02d}:{minutes:02d}"

                    old_hours_str, new_hours_str = float_to_time_str(old_hours_float), float_to_time_str(new_hours_float)

                    # 1. Build the rich HTML message for chatter and email
                    subject = f"Attention: Allocated Hours Changed for Project '{project.name}'"
                    body = f'''
                        <div style="font-family: Arial, sans-serif; border-left: 5px solid #ff9800; padding: 12px; margin-bottom: 12px; background-color: #fff3e0;">
                            <p style="font-size: 16px; font-weight: bold; color: #e65100; margin-top: 0;">
                                <i class="fa fa-exclamation-triangle"></i> Allocated Hours Updated
                            </p>
                            <p>The allocated hours for project <strong>{project.name}</strong> were changed by <strong>{self.env.user.name}</strong>.</p>
                            <hr style="border-top: 1px solid #ffcc80; border-bottom: none;"/>
                            <p style="margin: 0;"><strong>Previous Hours:</strong> <span style="font-weight: bold; font-size: 1.1em;">{old_hours_str}</span></p>
                            <p style="margin: 0;"><strong>New Hours:</strong> <span style="font-weight: bold; font-size: 1.1em; color: #c62828;">{new_hours_str}</span></p>
                        </div>
                    '''

                    # 2. Post an internal note in chatter (does not email followers)
                    project.message_post(
                        body=body,
                        subject=subject,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',  # Use 'mt_note' to avoid mass emailing
                        author_id=self.env.ref('base.partner_root').id
                    )

                    # 3. Collect specific partners for targeted email notification
                    partner_ids_to_notify = []
                    # Technical Director
                    if project.technical_director_id:
                        partner_ids_to_notify.append(project.technical_director_id.partner_id.id)

                    # Commercial Director
                    commercial_director_employee = self.env['hr.employee'].search([('job_title', '=', 'Commercial Director')], limit=1)
                    if commercial_director_employee and commercial_director_employee.user_id:
                        partner_ids_to_notify.append(commercial_director_employee.user_id.partner_id.id)

                    # System Admin User
                    admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
                    if admin_user:
                        partner_ids_to_notify.append(admin_user.partner_id.id)

                    # 4. Send targeted emails using a separate notification message
                    if partner_ids_to_notify:
                        # Get OdooBot's details for the 'From' field
                        odoo_bot = self.env.ref('base.partner_root')
                        # Use a fallback system email if OdooBot has no email configured
                        email_from = formataddr((odoo_bot.name, odoo_bot.email or self.env['ir.config_parameter'].sudo().get_param('mail.catchall.address')))

                        unique_partner_ids = list(set(partner_ids_to_notify))
                        for partner_id in unique_partner_ids:
                            recipient_partner = self.env['res.partner'].browse(partner_id)
                            # Only try to send if the recipient has an email
                            if recipient_partner.email:
                                self.env['mail.mail'].create({
                                    'subject': subject,
                                    'body_html': body,
                                    'email_from': email_from,  # Explicitly set the From address
                                    'email_to': recipient_partner.email,
                                    'author_id': odoo_bot.id,
                                    'model': 'project.project',
                                    'res_id': project.id,
                                    'auto_delete': True,  # Clean up sent emails
                                }).send()


        # if 'technical_director_id' in vals:
        #     for record in self:
        #         user = record.env['res.users'].browse(vals['technical_director_id'])
        #         group = record.env.ref('custom_project.group_project_director')
                # if user and group and user not in group.users:  # Add the User to the group Automatically.
                #     group.users = [(4, user.id)]

        if 'user_id' in vals:
            for record in self:
                project_manager = record.env['res.users'].browse(vals['user_id'])
                group_manager = record.env.ref('custom_project.group_project_manager')
                if project_manager and group_manager and project_manager not in group_manager.users:
                    group_manager.users = [(4, project_manager.id)]

        # Mar 05
        if 'technical_director_id' in vals:
            for project in self:
                # if project.technical_director_id:           for last team member
                # alireza Apr 14, 2025
                if project.technical_director_id.partner_id not in project.message_partner_ids:
                    project.message_subscribe(partner_ids=[project.technical_director_id.partner_id.id])

        return res

    @api.constrains('date_start', 'date')
    def _check_start_end_dates_not_equal(self):
        for project in self:
            if project.date_start and project.date and project.date_start == project.date:
                raise ValidationError(_("The project's Start Date and End Date cannot be the same."))

    def unlink(self):
        """When deleting a project, we disable the restriction on deleting followers. """
        if not self.env.context.get('deleting_whole_project'):
            for project in self:
                if project.user_id == self.env.user:
                    return super(CustomProjectProject, self).with_context(deleting_whole_project=True,
                                                                          allow_project_delete=True).sudo().unlink()

            return super(CustomProjectProject, self).with_context(deleting_whole_project=True,
                                                                  allow_project_delete=True).unlink()
        return super(CustomProjectProject, self).unlink()


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    approval_status = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Approval Status',
        default='draft',
    )

    date = fields.Datetime(string="Date and Time", required=True)
    

# by alireza july 23, 2025
    # @api.model
    # def create(self, vals):
    #     task_id = vals.get('task_id')
    #     if task_id:
    #         task = self.env['project.task'].browse(task_id)

    #         project = task.project_id
    #         if project.state == 'completed':
    #             raise ValidationError("The project is Completed. You cannot log time anymore.")

    #         if self.env.user not in task.user_ids:
    #             raise AccessError("You are not assigned to this task.")

    #         # Checks, Employee is assigned to task or not.
    #         allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
    #         if not allocation:
    #             raise AccessError(f"❌\nYou do not have permissions to add timesheet records."
    #                               "\n⚙️"
    #                               "\n  |_The user first must be Assigned to the task, then must be added to Notebook >> My Team)")
    #         # Calculate the total timesheet hours recorded for this user on this task.
    #         timesheet_lines = self.search([
    #             ('task_id', '=', task_id),
    #             ('user_id', '=', self.env.user.id)
    #         ])
    #         total_logged = sum(timesheet_lines.mapped('unit_amount'))
    #         new_hours = vals.get('unit_amount', 0)
    #         if total_logged + new_hours > allocation.allocated_hours:
    #             raise ValidationError("You cannot log more time than allocated for this task.")

    #     return super(AccountAnalyticLine, self).create(vals)

    # def write(self, vals):
    #     task_id = vals.get('task_id')
    #     if task_id:
    #         task = self.env['project.task'].browse(task_id)
    #         if self.env.user not in task.user_ids:
    #             raise AccessError("You are not assigned to this task. So couldn't edit this Task.")

    #     for line in self:
    #         task = line.task_id
    #         if task:
    #             allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
    #             if not allocation:
    #                 raise AccessError("You are not allocated to log time for this task.")
    #             # Calculate the total timesheet hours recorded except for this line (if the value changes)
    #             other_lines = self.search([
    #                 ('id', '!=', line.id),
    #                 ('task_id', '=', task.id),
    #                 ('user_id', '=', self.env.user.id)
    #             ])
    #             total_logged = sum(other_lines.mapped('unit_amount'))
    #             new_amount = vals.get('unit_amount', line.unit_amount)
    #             if total_logged + new_amount > allocation.allocated_hours:
    #                 raise ValidationError("The updated time exceeds your allocated hours for this task.")

    #     return super(AccountAnalyticLine, self).write(vals)


    # by alireza july 23, 2025
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            task_id = vals.get('task_id')
            if task_id:
                task = self.env['project.task'].browse(task_id)

                # Skip validation if task doesn't exist or has no project (e.g., leave records)
                if not task.exists() or not task.project_id:
                    continue

                project = task.project_id
                if not project.date_start or not project.date:
                    raise ValidationError(_(
                        "You cannot log time for this project because the project's Start Date or End Date is not set. "
                        "Please ask the Project Director to set these dates first."
                    ))
                if project.state == 'completed':
                    raise ValidationError("The project is Completed. You cannot log time anymore.")

                if self.env.user not in task.user_ids:
                    raise AccessError("You are not assigned to this task.")

                # Checks, Employee is assigned to task or not.
                allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
                if not allocation:
                    raise AccessError(f"❌\nYou do not have permissions to add timesheet records."
                                    "\n⚙️"
                                    "\n  |_The user first must be Assigned to the task, then must be added to Notebook >> My Team)")
                # Calculate the total timesheet hours recorded for this user on this task.
                timesheet_lines = self.search([
                    ('task_id', '=', task_id),
                    ('user_id', '=', self.env.user.id)
                ])
                total_logged = sum(timesheet_lines.mapped('unit_amount'))
                new_hours = vals.get('unit_amount', 0)
                if total_logged + new_hours > allocation.allocated_hours:
                    raise ValidationError("You cannot log more time than allocated for this task.")

        return super(AccountAnalyticLine, self).create(vals_list)

    def write(self, vals):
        # This initial check only runs if the task is being changed.
        # It needs to exempt the admin user.
        if 'task_id' in vals:
            task = self.env['project.task'].browse(vals.get('task_id'))
            if task.exists() and self.env.user.login != 'admin' and self.env.user not in task.user_ids:
                raise AccessError("You are not assigned to this task, so you cannot change the task of this timesheet.")

        for line in self:
            is_admin = self.env.user.login == 'admin'
            is_owner = line.user_id == self.env.user
            # Security check: Allow edit only for the record owner or the 'admin' user.
            if not (is_admin or is_owner):
                raise AccessError(_("Only the timesheet owner or an administrator can edit this entry."))

            # Admin users bypass all business logic validation below.
            if is_admin:
                continue

            # For non-admin users (who must be the owner), perform validation.
            task = line.task_id
            if task:
                if not task.project_id:
                    continue

                project = task.project_id
                if not project.date_start or not project.date:
                    raise ValidationError(_(
                        "You cannot log time because the project's Start/End Date is not set. "
                        "Please ask the Project Director to set these dates."
                    ))

                allocation = task.allocation_ids.filtered(lambda a: a.employee_id == self.env.user)
                if not allocation:
                    raise AccessError("You are not allocated to log time for this task.")

                # Calculate the total timesheet hours recorded except for this line (if the value changes)
                other_lines = self.search([
                    ('id', '!=', line.id),
                    ('task_id', '=', task.id),
                    ('user_id', '=', self.env.user.id)
                ])
                total_logged = sum(other_lines.mapped('unit_amount'))
                new_amount = vals.get('unit_amount', line.unit_amount)
                if total_logged + new_amount > allocation.allocated_hours:
                    raise ValidationError("The updated time exceeds your allocated hours for this task.")

        return super(AccountAnalyticLine, self).write(vals)

    def unlink(self):
        # Author: F. Alimirzaie, 2025-09-09
        # Security check: Allow delete only for the record owner or the 'admin' user.
        for line in self:
            is_admin = self.env.user.login == 'admin'
            is_owner = line.user_id == self.env.user
            if not (is_admin or is_owner):
                raise AccessError(_("Only the timesheet owner or an administrator can delete this entry."))
        return super(AccountAnalyticLine, self).unlink()

class ProjectTaskAllocation(models.Model):
    _name = 'project.task.allocation'
    _description = 'Allocation of Planned Hours per Employee for a Task'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'res.users',
        string='Employee',
        required=True,
        help="Employee assigned to this task allocation."
    )
    # Modified by A_zeril_A, 2025-10-20: Removed invalid 'widget' parameter from field definition for Odoo 16 upgrade compatibility.
    allocated_hours = fields.Float(
        string="Allocated Hours",
        required=True,
        help="Maximum hours this employee is allowed to log for the task."
    )

    _sql_constraints = [
        # Preventing duplicate assignment of an employee to a task
        ('unique_employee_per_task', 'unique(task_id, employee_id)',
         'Each employee can have only one allocation per task.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # A_zeril_A, 2025-10-06: Two-way synchronization logic.
        # When an allocation is created in the tab, add the user to the main Assignees field.
        allocations = super().create(vals_list)
        if not self.env.context.get('syncing_from_user'):
            for allocation in allocations:
                task = allocation.task_id
                user = allocation.employee_id
                if user and user not in task.user_ids:
                    task.with_context(syncing_from_allocation=True).write({'user_ids': [(4, user.id)]})
        return allocations

    def unlink(self):
        # A_zeril_A, 2025-10-06: Two-way synchronization logic.
        # When an allocation is removed from the tab, remove the user from the main Assignees field.
        if not self.env.context.get('syncing_from_user'):
            for allocation in self:
                task = allocation.task_id
                user_to_remove = allocation.employee_id
                
                # Check if this is the last allocation for this user on this task
                other_allocs = self.search([
                    ('task_id', '=', task.id),
                    ('employee_id', '=', user_to_remove.id),
                    ('id', '!=', allocation.id)
                ])
                
                if not other_allocs and user_to_remove in task.user_ids:
                    task.with_context(syncing_from_allocation=True).write({'user_ids': [(3, user_to_remove.id)]})
        return super().unlink()

    @api.constrains('allocated_hours')
    def _check_allocated_hours(self):
        for record in self:
            total_allocated = sum(record.task_id.allocation_ids.mapped('allocated_hours'))
            if total_allocated > record.task_id.planned_hours:
                raise ValidationError(f"Total allocated hours cannot exceed the planned hours for this task!")


class MailFollowers(models.Model):
    """
    This class inherits mail.followers to restrict followers on projects and tasks.
    It works in conjunction with the CustomMailWizardInvite class.
    """
    _inherit = "mail.followers"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides the create method to handle automatic subscriptions.
        - If the 'allow_external_followers' context is set (by a privileged user),
          it allows the creation of any follower.
        - Otherwise, it silently filters out any non-user followers to prevent
          automated processes (like Sales Order confirmation) from crashing.
        """
        if self.env.context.get('allow_external_followers'):
            return super().create(vals_list)

        filtered_vals_list = []
        for vals in list(vals_list):
            if vals.get('res_model') in ['project.project', 'project.task'] and 'partner_id' in vals:
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                if partner.user_ids:
                    filtered_vals_list.append(vals)
                else:
                    _logger.warning(
                        "Blocked automatic addition of external follower '%s' to %s(id=%s). "
                        "Only registered users are allowed as followers in automated processes.",
                        partner.name, vals.get('res_model'), vals.get('res_id')
                    )
            else:
                filtered_vals_list.append(vals)

        if not filtered_vals_list:
            return self.env['mail.followers']

        return super().create(filtered_vals_list)


# class MailFollowers(models.Model):
#     _inherit = "mail.followers"


#     def unlink(self):
#         """Avoid deleting Admin members and 'Followers of all Projects' members from project followers
#         (except when deleting a task or a project)"""
#         print("🔴 Delete followers: ", self.mapped('partner_id').ids)

#         if self.env.context.get('allow_task_delete') or self.env.context.get('allow_project_delete'):
#             return super(MailFollowers, self).unlink()

#         partners_to_remove = self.mapped('partner_id')
#         current_user = self.env.user

#         _logger.info(
#             "📌 partners_to_remove: %s | 🔍 Removed by: %s (ID: %s)",
#             partners_to_remove.ids,
#             current_user.name,
#             current_user.id
#         )

#         task_id_to_remove_from = self.env.context.get('task_id')

#         for follower in self:
#             if not task_id_to_remove_from and follower.res_model == 'project.task':
#                 task_id_to_remove_from = follower.res_id

#         print(f"✅ Final amount >> task_id_to_remove_from: {task_id_to_remove_from}")

#         if not task_id_to_remove_from:
#             _logger.warning("Task ID not found!")
#         else:
#             task_to_modify = self.env['project.task'].browse(task_id_to_remove_from)
#             print(f"task_to_modify: {task_to_modify}")

#             if task_to_modify.exists():
#                 print(f"📌 Task {task_to_modify.id} Has users: {task_to_modify.user_ids.ids}")
#                 users_to_remove = task_to_modify.user_ids.filtered(
#                     lambda user: user.partner_id in self.mapped('partner_id'))

#                 if users_to_remove:
#                     task_to_modify.write({'user_ids': [(3, user.id) for user in users_to_remove]})
#                     print(f"✅ Users {users_to_remove.ids} from Task {task_to_modify.id} Deleted!")
#             else:
#                 print("📌 ❌ The requested task was not found!")

#         return super(MailFollowers, self).unlink()


#     # Mar 09
#     @api.model
#     def create(self, vals):
#         follower = super(MailFollowers, self).create(vals)

#         # Check if this follower is related to a task.
#         if follower.res_model == 'project.task':
#             task = self.env['project.task'].browse(follower.res_id)
#             partner = follower.partner_id

#             # If this follower has an Odoo user, add him to user_ids
#             if partner.user_ids:
#                 task.write({'user_ids': [(4, partner.user_ids[0].id)]})

#         return follower

#     def write(self, vals):
#         res = super(MailFollowers, self).write(vals)

#         for follower in self:
#             if follower.res_model == 'project.task':
#                 task = self.env['project.task'].browse(follower.res_id)
#                 partner = follower.partner_id

#                 if partner.user_ids:
#                     task.write({'user_ids': [(4, partner.user_ids[0].id)]})

#         return res
#     # End


# Note: project.delete.wizard was removed in Odoo 16
# class ProjectDeleteWizard(models.TransientModel):
#     """ To get Delete Project accesses """
#     _inherit = "project.delete.wizard"


class AccountAnalyticAccountInherit(models.Model):
    """ To get Delete Project accesses """
    _inherit = 'account.analytic.account'
