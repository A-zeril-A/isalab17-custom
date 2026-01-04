# -*- coding: utf-8 -*-

from odoo import models, fields, api

class purchaseCateg(models.Model):
    _name= "purchase.categ"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Purchase Category"
    _rec_name = 'name'

    name    = fields.Char(string="Category Name",required=True)
    # Modified by A_zeril_A, 2025-10-20: Corrected invalid 'String' parameter to 'string' for Odoo 16 upgrade compatibility.
    color   = fields.Integer(string="Color")