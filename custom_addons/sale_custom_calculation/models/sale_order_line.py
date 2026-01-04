# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # اضافه کردن فیلد جدید برای subtotal دستی
    manual_price_subtotal = fields.Float(
        string='Subtotal',
        digits='Product Price',
        compute='_compute_manual_subtotal',
        inverse='_inverse_manual_subtotal',
        store=True
    )

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_manual_subtotal(self):
        """
        محاسبه خودکار subtotal بر اساس quantity و price unit
        """
        for line in self:
            line.manual_price_subtotal = line.product_uom_qty * line.price_unit

    def _inverse_manual_subtotal(self):
        """
        وقتی کاربر subtotal را وارد کرد، price unit را محاسبه کن
        """
        for line in self:
            if line.product_uom_qty and line.manual_price_subtotal:
                if line.product_uom_qty <= 0:
                    raise UserError("مقدار تعداد باید بزرگتر از صفر باشد!")
                line.price_unit = line.manual_price_subtotal / line.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_id_custom(self):
        """
        وقتی محصول تغییر کرد، قیمت پیشفرض را تنظیم کن
        """
        if self.product_id:
            self.price_unit = self.product_id.list_price

    @api.onchange('product_uom_qty', 'price_unit')
    def _onchange_qty_price(self):
        """
        وقتی quantity یا price unit تغییر کرد، subtotal را آپدیت کن
        """
        if self.product_uom_qty and self.price_unit:
            self.manual_price_subtotal = self.product_uom_qty * self.price_unit

    @api.onchange('manual_price_subtotal')
    def _onchange_manual_subtotal(self):
        """
        وقتی کاربر مستقیماً subtotal را تغییر داد
        """
        if self.product_uom_qty and self.manual_price_subtotal:
            if self.product_uom_qty <= 0:
                raise UserError("مقدار تعداد باید بزرگتر از صفر باشد!")
            self.price_unit = self.manual_price_subtotal / self.product_uom_qty

    def write(self, vals):
        """
        مدیریت محاسبات هنگام ذخیره
        """
        if 'manual_price_subtotal' in vals and 'product_uom_qty' in vals:
            if vals.get('product_uom_qty') and vals.get('manual_price_subtotal'):
                if vals['product_uom_qty'] <= 0:
                    raise UserError("مقدار تعداد باید بزرگتر از صفر باشد!")
                vals['price_unit'] = vals['manual_price_subtotal'] / vals['product_uom_qty']
        
        elif 'manual_price_subtotal' in vals:
            # فقط subtotal تغییر کرده
            for line in self:
                if line.product_uom_qty and vals.get('manual_price_subtotal'):
                    if line.product_uom_qty <= 0:
                        raise UserError("مقدار تعداد باید بزرگتر از صفر باشد!")
                    vals['price_unit'] = vals['manual_price_subtotal'] / line.product_uom_qty
        
        return super(SaleOrderLine, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        مدیریت محاسبات هنگام ایجاد رکورد جدید
        """
        for vals in vals_list:
            if vals.get('manual_price_subtotal') and vals.get('product_uom_qty'):
                if vals['product_uom_qty'] <= 0:
                    raise UserError("مقدار تعداد باید بزرگتر از صفر باشد!")
                vals['price_unit'] = vals['manual_price_subtotal'] / vals['product_uom_qty']
        
        return super(SaleOrderLine, self).create(vals_list)