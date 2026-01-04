# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    arca = fields.Char(string="Arca")

    @api.constrains('arca')
    def _check_arca(self):
        for record in self:
            if record.arca and not re.match(r'^[0-9_]*$', record.arca):
                raise ValidationError("Only 'Numbers' and 'Underscore ( _ )' are allowed in the 'Arca' field.")
