from odoo import models, fields, api

class orderProduct(models.Model):
    _name="order.product"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Product"
    _rec_name = 'productName'

    productName     = fields.Char(string="Product", tracking=True)
    # Modified by A_zeril_A, 2025-10-20: Corrected invalid 'String' parameter to 'string' for Odoo 16 upgrade compatibility.
    company_id      = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    currency_id     = fields.Many2one('res.currency',related='company_id.currency_id')
    productPrice    = fields.Float(string="price",tracking=True)
    productLink     = fields.Char(string="Product Link",tracking=True)    
    product_cat     = fields.Many2many('purchase.categ')