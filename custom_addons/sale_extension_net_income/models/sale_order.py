from odoo import models, fields, api


class CustomSaleOrder(models.Model):
    _name = 'custom.sale.order'
    _description = 'Custom Sale Order Table'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    name = fields.Char(string='Cost Title')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    service_price = fields.Float(string='Price')
    total_net = fields.Monetary(string='Total:', compute='_compute_totals')

    @api.depends('service_price')
    def _compute_totals(self):
        for record in self:
            record.total_net = record.service_price


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_sale_order_ids = fields.One2many('custom.sale.order', 'sale_order_id', string='Extra Costs')
    custom_total_net_sum = fields.Monetary(string="Custom Total Net", compute="_compute_custom_total_net_sum",
                                           currency_field='currency_id')
    new_total_value = fields.Monetary(string="Total Extra Costs (Tax not included)", compute='_compute_new_total_value',
                                      currency_field='currency_id')

    @api.depends('custom_sale_order_ids.total_net')
    def _compute_custom_total_net_sum(self):
        for order in self:
            order.custom_total_net_sum = sum(order.custom_sale_order_ids.mapped('total_net'))

    @api.depends('custom_total_net_sum', 'tax_totals_json')
    def _compute_new_total_value(self):
        for order in self:
            order.new_total_value = order.amount_untaxed - order.custom_total_net_sum


