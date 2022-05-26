# -*- coding: utf-8 -*-
from requests import request
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    ship_engine_api_key = fields.Char("Ship Engine API Key", copy=False,help="API Key provided by ship engine, Using API management functionality we can generate the API key in shipengine and use that key in to the odoo..")
    ship_engine_api_url= fields.Char("Ship Engine API URL", copy=False,help="API URL provided by Shipengine. Ex. https://api.shipengine.com/v1/")
    shipengine_carrier_ids = fields.One2many("shipengine.carrier.details", "company_id", string="Shipping Instance")
    use_shipengine_shipping_provider = fields.Boolean(copy=False, string="Are You Use ShipEngine.?",
                                                   help="If use ShipEngine shipping Integration than value set TRUE.",
                                                   default=False)

    def get_shipengine_carrier(self):
        shipengine_carrier_details_obj= self.env['shipengine.carrier.details']
        api_name = 'carriers'
        headers = {"Accept":"application/json", "api-key":"%s" % (self.ship_engine_api_key),
                   "Content-Type":"application/json"}
        url = "%s%s"%(self.ship_engine_api_url,api_name)
        try:
            response_data = request(method='GET', url=url, headers=headers)
        except Exception as e:
            raise ValidationError(e)
        if response_data.status_code == 200:
            try:
                response_data = response_data.json()
                carrier_response=response_data.get('carriers')
                if carrier_response:
                    if isinstance(carrier_response, dict):
                        carrier_response = [carrier_response]
                    for carrier in carrier_response:
                        carrier_name=carrier.get('carrier_code',False)
                        carrier_id=carrier.get('carrier_id',False)
                        account_no=carrier.get('account_number',False)
                        multiple_package=carrier.get('has_multi_package_supporting_services',False)
                        carrier_exist=shipengine_carrier_details_obj.search([('company_id','=',self.id),('shipengine_carrier_id','=',carrier_id),('provider_account_number','=',account_no)])
                        if not carrier_exist:
                            shipengine_carrier_details_obj.sudo().create({'name':carrier_name,'shipengine_carrier_id':carrier_id,
                            'provider_account_number':account_no,'has_multi_package_supporting_services':multiple_package,
                            'company_id':self.id})
                else:
                    raise ValidationError("Error raised for getting ShipEngine carriers %s"%(response_data))
            except Exception as e:
                raise ValidationError("%s%s"%(e,response_data))
        else:
            raise ValidationError("Error raised for getting ShipEngine carriers")
        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Yeah! Ship Engine Account has been retrieved.",
                'img_url': '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }
