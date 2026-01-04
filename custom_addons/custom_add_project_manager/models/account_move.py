from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'


    project_manager_id = fields.Many2one(
        'res.users',
        string='Project Manager',
        tracking=True,
        help="Select the project manager responsible for this order"
    )
    
    sale_order_date = fields.Date(
        string='Order Date',
        compute='_compute_sale_order_fields',
        store=True,
        help="Date of the related sale order"
    )
    
    order_date_sequence = fields.Integer(
        string='Order Date Sequence',
        compute='_compute_order_date_sequence',
        store=True,
        help="Sequential number based on order date (1 for oldest)"
    )
    
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        compute='_compute_opportunity_info',
        store=True,
        help="Related opportunity from CRM"
    )
    
    opportunity_name = fields.Char(
        string='Opportunity Name',
        related='opportunity_id.name',
        store=True,
        help="Name of the related opportunity"
    )
    
    total_project_quantity = fields.Float(
        string='Total Project Hours',
        compute='_compute_total_project_quantity',
        store=True,
        digits=(12, 2),
        help="Total quantity of all products in the related project"
    )
    
    sale_order_amount_untaxed = fields.Monetary(
        string='Sale Amount Untaxed',
        compute='_compute_sale_order_amounts',
        store=True,
        help="Untaxed amount of the related sale order"
    )
    
    sale_order_amount_tax = fields.Monetary(
        string='Sale Amount Tax',
        compute='_compute_sale_order_amounts',
        store=True,
        help="Tax amount of the related sale order"
    )
    
    sale_order_amount_total = fields.Monetary(
        string='Sale Amount Total',
        compute='_compute_sale_order_amounts',
        store=True,
        help="Total amount of the related sale order"
    )
    
    total_invoiced_amount = fields.Monetary(
        string='Total Invoiced Amount',
        compute='_compute_sale_order_invoice_info',
        store=True,
        help="Total amount invoiced for this sale order"
    )
    
    total_paid_amount = fields.Monetary(
        string='Total Paid Amount',
        compute='_compute_sale_order_invoice_info',
        store=True,
        help="Total amount paid for all invoices of this sale order"
    )
    
    total_due_amount = fields.Monetary(
        string='Total Due Amount',
        compute='_compute_sale_order_invoice_info',
        store=True,
        help="Total amount due for all invoices of this sale order"
    )
    
    sale_order_payment_status = fields.Selection(
        selection=[
            ('not_invoiced', 'Not Invoiced'),
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Fully Paid')
        ],
        string='Sale Order Payment Status',
        compute='_compute_sale_order_invoice_info',
        store=True,
        help="Payment status of all invoices for the sale order"
    )

    client_order_number = fields.Char(
        string='Client Order Number',
        tracking=True,
        help="Client's reference number for this order"
    )

    status_project = fields.Selection(
        selection=[
            ('ongoing', 'Ongoing'),
            ('blocked', 'Blocked'),
            ('done', 'Done')
        ],
        string='Project Status',
        tracking=True,
        help="Current status of the project"
    )

    manual_invoice_date = fields.Date(
        string='Invoice Date',
        tracking=True,
        help="Manual invoice date entry"
    )

    invoice_origin = fields.Char(
        string='Protocol Number', 
        tracking=True
    )

    @api.depends('invoice_origin')
    def _compute_sale_order_fields(self):
        for invoice in self:
            order_date = False
            if invoice.invoice_origin:
                sale_order = self.env['sale.order'].search(
                    [('name', '=', invoice.invoice_origin)], 
                    limit=1
                )
                if sale_order and sale_order.date_order:
                    order_date = fields.Date.to_date(sale_order.date_order)
            invoice.sale_order_date = order_date

    @api.depends('sale_order_date')
    def _compute_order_date_sequence(self):
        # همه فاکتورهای دارای تاریخ سفارش را بگیر
        invoices_with_order_date = self.search([
            ('sale_order_date', '!=', False),
            ('id', 'in', self.ids)
        ])
        
        if invoices_with_order_date:
            # بر اساس تاریخ سفارش مرتب کن (قدیمی ترین اول)
            sorted_invoices = invoices_with_order_date.sorted(
                key=lambda x: x.sale_order_date
            )
            
            # شماره ترتیب اختصاص بده
            sequence = 1
            for invoice in sorted_invoices:
                invoice.order_date_sequence = sequence
                sequence += 1
        
        # برای فاکتورهایی که تاریخ سفارش ندارند، مقدار صفر بگذار
        for invoice in self:
            if not invoice.sale_order_date:
                invoice.order_date_sequence = 0

    @api.depends('invoice_origin')
    def _compute_opportunity_info(self):
        for invoice in self:
            opportunity_id = False
            
            if invoice.invoice_origin:
                sale_order = self.env['sale.order'].search(
                    [('name', '=', invoice.invoice_origin)], 
                    limit=1
                )
                
                if sale_order:
                    # بررسی فیلدهای مختلف برای پیدا کردن opportunity
                    for field_name in ['opportunity_id', 'lead_id', 'source_id']:
                        if hasattr(sale_order, field_name) and getattr(sale_order, field_name):
                            opportunity_id = getattr(sale_order, field_name).id
                            break
            
            invoice.opportunity_id = opportunity_id

    @api.depends('invoice_origin')
    def _compute_total_project_quantity(self):
        for invoice in self:
            total_quantity = 0.0
            
            if invoice.invoice_origin:
                # پیدا کردن سفارش فروش مرتبط
                sale_order = self.env['sale.order'].search(
                    [('name', '=', invoice.invoice_origin)], 
                    limit=1
                )
                
                if sale_order:
                    # محاسبه مجموع quantity تمامی محصولات در سفارش فروش
                    for order_line in sale_order.order_line:
                        total_quantity += order_line.product_uom_qty
            
            invoice.total_project_quantity = total_quantity

    @api.depends('invoice_origin')
    def _compute_sale_order_amounts(self):
        for invoice in self:
            amount_untaxed = 0.0
            amount_tax = 0.0
            amount_total = 0.0
            
            if invoice.invoice_origin:
                # پیدا کردن سفارش فروش مرتبط
                sale_order = self.env['sale.order'].search(
                    [('name', '=', invoice.invoice_origin)], 
                    limit=1
                )
                
                if sale_order:
                    amount_untaxed = sale_order.amount_untaxed
                    amount_tax = sale_order.amount_tax
                    amount_total = sale_order.amount_total
            
            invoice.sale_order_amount_untaxed = amount_untaxed
            invoice.sale_order_amount_tax = amount_tax
            invoice.sale_order_amount_total = amount_total

    @api.depends('invoice_origin')
    def _compute_sale_order_invoice_info(self):
        for invoice in self:
            total_invoiced = 0.0
            total_paid = 0.0
            total_due = 0.0
            payment_status = 'not_invoiced'
            
            if invoice.invoice_origin:
                # پیدا کردن سفارش فروش مرتبط
                sale_order = self.env['sale.order'].search(
                    [('name', '=', invoice.invoice_origin)], 
                    limit=1
                )
                
                if sale_order:
                    # پیدا کردن همه invoiceهای مربوط به این sale order
                    sale_order_invoices = self.search([
                        ('invoice_origin', '=', sale_order.name),
                        ('state', 'in', ['posted', 'draft'])
                    ])
                    
                    # محاسبه مجموع مبالغ
                    for inv in sale_order_invoices:
                        total_invoiced += inv.amount_total
                        total_paid += (inv.amount_total - inv.amount_residual)
                        total_due += inv.amount_residual
                    
                    # تعیین وضعیت پرداخت
                    if total_invoiced == 0:
                        payment_status = 'not_invoiced'
                    elif total_due == 0:
                        payment_status = 'paid'
                    elif total_due < total_invoiced:
                        payment_status = 'partial'
                    else:
                        payment_status = 'not_paid'
            
            invoice.total_invoiced_amount = total_invoiced
            invoice.total_paid_amount = total_paid
            invoice.total_due_amount = total_due
            invoice.sale_order_payment_status = payment_status

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.invoice_origin:
                sale_order = self.env['sale.order'].search(
                    [('name', '=', move.invoice_origin)], 
                    limit=1
                )
                if sale_order:
                    update_vals = {}
                    if sale_order.date_order:
                        update_vals['sale_order_date'] = fields.Date.to_date(sale_order.date_order)
                    
                    # پیدا کردن opportunity
                    opportunity_id = False
                    for field_name in ['opportunity_id', 'lead_id', 'source_id']:
                        if hasattr(sale_order, field_name) and getattr(sale_order, field_name):
                            opportunity_id = getattr(sale_order, field_name).id
                            break
                    
                    if opportunity_id:
                        update_vals['opportunity_id'] = opportunity_id
                    
                    # محاسبه مجموع quantity
                    total_quantity = 0.0
                    for order_line in sale_order.order_line:
                        total_quantity += order_line.product_uom_qty
                    update_vals['total_project_quantity'] = total_quantity
                    
                    # اضافه کردن مقادیر مالی
                    update_vals.update({
                        'sale_order_amount_untaxed': sale_order.amount_untaxed,
                        'sale_order_amount_tax': sale_order.amount_tax,
                        'sale_order_amount_total': sale_order.amount_total,
                    })
                    
                    if update_vals:
                        move.write(update_vals)
        
        # پس از ایجاد، sequence را محاسبه کن
        moves._compute_order_date_sequence()
        # اطلاعات invoiceهای sale order را به روز کن
        moves._compute_sale_order_invoice_info()
        return moves