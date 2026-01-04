from odoo import models, fields, api

class office(models.Model):
    _name = "purchase.office"
    _description = "Purchase Category"
    _rec_name = 'officeName'

    officeName  = fields.Char(string="Nmae of the office",required=True)
    officeAdd   = fields.Char(string="Office Address",required=True)
    # Modified by A_zeril_A, 2025-10-20: Corrected 'strind' typo to 'string' for Odoo 16 upgrade compatibility.
    image       = fields.Binary(string="Logo")
    
