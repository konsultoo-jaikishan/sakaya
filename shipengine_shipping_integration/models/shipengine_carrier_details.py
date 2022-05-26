from odoo import models, fields, api

class ShipEngineCarrierDetails(models.Model):
    _name = "shipengine.carrier.details"
    _description = "Shipengin Carrier Details"
    
    name = fields.Char(string='Carrier Code',help="Carrier code indicates configured carrier in shipengine.")
    shipengine_carrier_id = fields.Char(string='Ship Engine Carrier ID',help="Carrier ID indicates configured carrier in shipengine.")
    provider_account_number = fields.Char(string='Account Number',help="It's indicates configured carrier account in shipengine.")
    has_multi_package_supporting_services = fields.Boolean(string="Is multi package supported?",default=False,help="If multiple packges available or provide by this provider then True.")
    company_id=fields.Many2one('res.company',string="Company")