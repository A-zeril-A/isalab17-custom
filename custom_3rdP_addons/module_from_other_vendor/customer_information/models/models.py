from odoo import fields, models

class CrmLeadExtension(models.Model):
    _inherit = 'crm.lead'
    
    updateDateField = fields.Date(string="Last Update")
    companySectores = fields.Text(string="Customer's departments relevant for our services")
    contSecReach = fields.Text(string="Contacts reached in the customer's company, by department")
    secTarget = fields.Text(string="Last commercial actions, by department")
    currentProject = fields.Text(string="Projects for which we have a contract/are bidding")
    currentContracts = fields.Text(string="Future opportunities identified")
    currentSup = fields.Text(string="Current Suppliers")
    generalNda = fields.Text(string="Generic NDA in progress")
    contactOfTheCompany = fields.Text(string="Contacts to reach in the customer's company, by department")
    customerLinkedin = fields.Text(string="Company's Linkedin")
    notes = fields.Html(string="Notes")
