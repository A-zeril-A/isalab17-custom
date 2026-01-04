# -*- coding: utf-8 -*-
# from odoo import http


# class CustomerInformation(http.Controller):
#     @http.route('/customer_information/customer_information', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/customer_information/customer_information/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('customer_information.listing', {
#             'root': '/customer_information/customer_information',
#             'objects': http.request.env['customer_information.customer_information'].search([]),
#         })

#     @http.route('/customer_information/customer_information/objects/<model("customer_information.customer_information"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('customer_information.object', {
#             'object': obj
#         })
