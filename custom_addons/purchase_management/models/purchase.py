# -*- coding: utf-8 -*-

# Modified by A_zeril_A, 2025-10-20: Corrected invalid 'String' parameter to 'string' in multiple fields for Odoo 16 upgrade compatibility.

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class purchaseManagement(models.Model):

    _name       = "purchase.management"
    _inherit    = ['mail.thread','mail.activity.mixin']
    _description = "Purchase Management"

    name                = fields.Char(string="Purchase Name", tracking=True)
    purchaser_res_id    = fields.Many2one('res.users', string="Purchaser Responsible", ondelete='cascade',required=True,
                                          default=lambda self: self.env['ir.config_parameter'].sudo().get_param('purchase_management.purchase_responsible_id'), readonly=True)
    budget_approver_id  = fields.Many2one('res.users', string="Budget Approver Responsible", ondelete='cascade',required=True,
                                          default=lambda self: self.env['ir.config_parameter'].sudo().get_param('purchase_management.budget_approver_id'), readonly=True)
    responsible_id      = fields.Many2one('hr.employee', string="Purchase Approver", default=lambda self : self._default_responsible(), readonly=True ,ondelete='set null')
    ordering_num        = fields.Char(string="Ordering Number")
    active              = fields.Boolean(string="Active", default=True)
    source_document     = fields.Char(string="Source Document" ,help='Number of related document')
    category_ids        = fields.Many2many('purchase.categ', string="Category")
    deadline_date       = fields.Date(string="Deadline date", required=True)
    order_date          = fields.Date(string="Order date", default=fields.Datetime.now)
    zlab_contact_id     = fields.Many2one('res.partner', string="Office", domain="[('id','in',child_ids)]", required=True)
    
    #product One2many
    product_line_ids    = fields.One2many('purchase.product.lines','purchase_id',string='Product Line')
    #product end
    company_id          = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    arca_number         = fields.Integer(string='N.Arca')
    note                = fields.Html(string="Terms and conditions")
    purchase_product_id = fields.Many2one('purchase.product.lines')
    currency_id         = fields.Many2one('res.currency',related='company_id.currency_id')
    state               = fields.Selection([
                            ('draft','Draft'),
                            ('send2res','Responsible'),
                            ('purchaser_start','Purchaser'),
                            ('budget_approve','Budget Approve'),
                            ('approve','Approve'),
                            ('done','Done'),
                            ('buy','Proceed To Buy'),
                            ('cancel','Cancelled')
                        ], string="Status", default="draft", required=True)
    total_amount        = fields.Monetary(string="Total Amount", compute="_compute_total_amount", store=True)
    exceed_budget_limit = fields.Boolean(string="Exceeds Purchase Limit", compute="_compute_exceeds_budget_limit", store=True, default=False)
    is_field_readonly   = fields.Boolean(string="Is the field ReadOnly?", compute="_compute_is_field_readonly", store=False)


    @api.model
    def _default_company_id(self):
        return self.env['res.partner'].search([('name','=like','ISALAB')], limit=1)
    
    zlab_company_id     = fields.Many2one('res.partner', string="Company", default=_default_company_id,readonly=True)
    child_ids           = fields.One2many('res.partner', inverse_name='parent_id',string="ZLAB Italia Contacts", compute='_compute_child_ids')

    @api.depends('zlab_company_id')
    def _compute_child_ids(self):
        for record in self:
            if record.zlab_company_id:
                record.child_ids = record.zlab_company_id.child_ids
            else:
                record.child_ids = False

    @api.model
    def _default_responsible(self):
        employee = self.env.user.employee_id
        if employee:
            return employee.parent_id
        else:
            return False
        
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'ordering_num' not in vals or not vals['ordering_num']:
                vals['ordering_num'] = self.env['ir.sequence'].next_by_code('purchase.management')
        records = super(purchaseManagement, self).create(vals_list)
        for record in records:
            record._compute_exceeds_budget_limit()  # Use the new record here
        return records

    def write(self, vals):
        result = super(purchaseManagement, self).write(vals)
        return result

    def _compute_is_field_readonly(self):
        for record in self:
            user                = self.env.user
            is_in_group_admin   = user.has_group('purchase_management.group_purchase_admin')
            is_in_group_aprover = user.has_group('purchase_management.group_purchase_approval')
            record.is_field_readonly = (
                record.state in ['send2res','purchaser_start'] and
                not (is_in_group_admin or is_in_group_aprover)
            )
    def _show_purchase_limit_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.limit.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('purchase_management.view_purchase_limit_wizard').id,
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def action_to_budget_approver(self):
        self.state  = 'budget_approve'
        for order in self:
            budget_responsible = order.budget_approver_id
            if budget_responsible and budget_responsible.id not in order.message_partner_ids.ids:
                order.message_partner_ids = [(4,budget_responsible.id)]
                activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
                summary = "Follow up on Purchase"
                note = "The purchase exceeds the budget limit, consider the budget approver. Please review and follow up on the purchase order."
                res_model_id = self.env.ref('purchase_management.model_purchase_management').id
                activity_values = {
                    'activity_type_id': activity_type_id,
                    'summary': summary,
                    'note': note,
                    'res_id': order.id,
                    'res_model_id': res_model_id,
                    'date_deadline': fields.Date.today(),
                    'user_id': budget_responsible.id,
                }
                self.env['mail.activity'].create(activity_values)

    def action_to_buy(self):
        self.state = 'buy'
        for order in self:
            purchaser_res = order.purchaser_res_id
            if purchaser_res and purchaser_res.id not in order.message_partner_ids.ids:
                order.message_partner_ids = [(4,purchaser_res.id)]
            activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
            summary = "Proceed to buy"
            note    = "The purchase has been accepted by budget approver"
            res_model_id = self.env.ref('purchase_management.model_purchase_management').id
            activity_values = {
                'activity_type_id' : activity_type_id,
                'summary': summary,
                'note' : note,
                'res_id' : order.id,
                'res_model_id': res_model_id,
                'date_deadline': fields.Date.today(),
                'user_id' : purchaser_res.id,
            }
            self.env['mail.activity'].create(activity_values)

    def action_to_purchaser(self):
        self.state = 'purchaser_start'
        for order in self:
            purchaser_res = order.purchaser_res_id
            if purchaser_res and purchaser_res.id not in order.message_partner_ids.ids:
                order.message_partner_ids = [(4,purchaser_res.id)]
                activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
                summary = "Follow up on purchase"
                note = "Start the purchase process"
                res_model_id = self.env.ref('purchase_management.model_purchase_management').id
                activity_values = {
                    'activity_type_id' : activity_type_id,
                    'summary' : summary,
                    'note' : note,
                    'res_id' : order.id,
                    'res_model_id' : res_model_id,
                    'date_deadline': fields.Date.today(),
                    'user_id' : purchaser_res.id,
                }
                self.env['mail.activity'].create(activity_values)

    def action_to_res(self):
        self.state = 'send2res'
        for order in self:
            responsible_user = order.responsible_id.user_id
            if responsible_user.id or order.responsible_id.user_id not in order.message_partner_ids.ids:
                order.message_partner_ids = [(4, responsible_user.id)]
            activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
            summary = "Follow up on Purchase"
            note = "Please review and follow up on the purchase order."
            res_model_id = self.env.ref('purchase_management.model_purchase_management').id
            activity_values = {
                'activity_type_id': activity_type_id,
                'summary': summary,
                'note': note,
                'res_id': order.id,
                'res_model_id': res_model_id,
                'date_deadline': fields.Date.today(),
                'user_id': responsible_user.id,
            }
            self.env['mail.activity'].create(activity_values)

    def action_approving(self):
        self.state = 'approve'
        for order in self:
            purchaser_responsible = self.purchaser_res_id
            if purchaser_responsible.id not in order.message_partner_ids.ids:
                order.message_partner_ids = [(4, purchaser_responsible.id)]
            activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
            summary = "Proceed the Purchase"
            note = "Please review the purchase and proceed with the order."
            res_model_id = self.env.ref('purchase_management.model_purchase_management').id
            activity_values = {
                'activity_type_id': activity_type_id,
                'summary': summary,
                'note': note,
                'res_id': order.id,
                'res_model_id': res_model_id,
                'date_deadline': fields.Date.today(),
                'user_id': purchaser_responsible.id,
            }
            self.env['mail.activity'].create(activity_values)

    @api.depends("total_amount")
    def _compute_exceeds_budget_limit(self):
        budget_limit = float(self.env['ir.config_parameter'].sudo().get_param('purchase_management.budget_limit', default=100))
        for record in self:
            record.exceed_budget_limit = record.total_amount > budget_limit

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def send_email(self, template):
        template.send_mail(self.id, force_send=True)

    @api.depends('product_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(line.price_subtotal for line in rec.product_line_ids)

class purchaseProductLines(models.Model):

    _name           = "purchase.product.lines"
    _description    = "Product Lines"
    qty             = fields.Integer(string = 'Quantity', default='1')
    purchase_id     = fields.Many2one('purchase.management',string="Purchase")
    currency_id     = fields.Many2one('res.currency',related='purchase_id.currency_id')
    price_subtotal  = fields.Monetary(string="Subtotal",compute='_compute_price_subtotal')
    price_total     = fields.Monetary(string="Totals",compute='_compute_price_total')
    product_id      = fields.Many2one('order.product',required=True)
    price_unit      = fields.Float(related='product_id.productPrice',readonly=False)
    is_readonly     = fields.Boolean(string="is readonly in product?")
    def _compute_is_readonly(self):
        for record in self:
            record.is_readonly = purchase_id.is_field_readonly

    @api.depends('price_unit','qty')
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.price_unit * rec.qty

    @api.depends('price_subtotal')
    def _compute_above_20(self):
        for rec in self:
            totals += rec.price_subtotal
        if totals > 20.0:
            return True

