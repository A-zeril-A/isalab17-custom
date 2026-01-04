# -*- coding: utf-8 -*-
# from odoo import http


# class CustomProjectTeamCost(http.Controller):
#     @http.route('/custom.project.profitability.dashboard/custom.project.profitability.dashboard', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom.project.profitability.dashboard/custom.project.profitability.dashboard/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom.project.profitability.dashboard.listing', {
#             'root': '/custom.project.profitability.dashboard/custom.project.profitability.dashboard',
#             'objects': http.request.env['custom.project.profitability.dashboard.custom.project.profitability.dashboard'].search([]),
#         })

#     @http.route('/custom.project.profitability.dashboard/custom.project.profitability.dashboard/objects/<model("custom.project.profitability.dashboard.custom.project.profitability.dashboard"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom.project.profitability.dashboard.object', {
#             'object': obj
#         })
