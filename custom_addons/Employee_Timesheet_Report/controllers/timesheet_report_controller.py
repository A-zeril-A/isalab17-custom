from odoo import http
from odoo.http import content_disposition, request
import base64

class TimesheetReportController(http.Controller):
    
    @http.route('/timesheet/export/xml', type='http', auth="user")
    def export_timesheet_xml(self, data, filename, **kwargs):
        """دانلود فایل XML"""
        try:
            file_content = base64.b64decode(data)
            return request.make_response(file_content, [
                ('Content-Type', 'application/xml'),
                ('Content-Disposition', content_disposition(filename)),
            ])
        except Exception as e:
            return request.not_found("Error generating file: %s" % str(e))