import json
from requests import request
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"
    shipengine_label_url = fields.Char(string="Ship Engine Label URL", help="Label URL.", readonly=True, copy=False)
    shipengine_label_id = fields.Char(string="Ship Engine Label ID", help="Ship Engine Label ID", readonly=True,
                                      copy=False)
    shipengine_shipment_id = fields.Char(string="Ship Engine Shipment ID", help="Ship Engine Shipment ID",
                                         readonly=True, copy=False)
    shipengine_bill_to_account = fields.Char(string="Shipengine Bill To Account",
                                             help="This field is used to bill shipping costs to a third party. This field must be used in conjunction with the bill_to_country_code, bill_to_party, and bill_to_postal_code fields.",
                                             copy=False)

    carrier_shipping_charge_ids = fields.One2many("carrier.shipping.charge", "picking_id", string="Carrier Cost")
    carrier_shipping_charge_id = fields.Many2one("carrier.shipping.charge", string="Shipping Method", copy=False)

    def get_shipengine_response_data(self, shipper_address=False, recipient_address=False, total_bulk_weight=False,
                                     packages=False, shipengine_bill_to_account=False):
        api_name = 'rates'
        headers = {"Accept": "application/json",
                   "api-key": "%s" % (self.carrier_id.company_id and self.carrier_id.company_id.ship_engine_api_key),
                   "Content-Type": "application/json"}
        url = "%s%s" % (self.carrier_id.company_id and self.carrier_id.company_id.ship_engine_api_url, api_name)
        shipengine_carrier_ids = []
        for shipengine_carrier in self.carrier_id.shipengine_carrier_ids:
            shipengine_carrier_ids.append(shipengine_carrier.shipengine_carrier_id)
        try:
            alcohol = True if self.move_lines.filtered(
                lambda x: 'lcohol' in x.product_id.categ_id.display_name) else False
            body = {
                "shipment": {
                    # We are Not Sending Address Validation API So Directly set Non Validation
                    "validate_address": "no_validation",
                    "ship_to": self.carrier_id.ship_engine_address_dict(recipient_address),
                    "ship_from": self.carrier_id.ship_engine_address_dict(shipper_address),
                    "return_to": self.carrier_id.ship_engine_address_dict(shipper_address),
                    "confirmation": "%s" % (self.carrier_id.shipengine_confirmation_type),
                    "customs": {
                        "contents": "%s" % (self.carrier_id.customs_content_type),
                        "non_delivery": "return_to_sender"
                    },
                    "advanced_options": {
                        "contains_alcohol": alcohol,
                        "delivered_duty_paid": "%s" % (self.carrier_id.delivered_duty_paid),
                        "non_machinable": "%s" % (self.carrier_id.non_machinable),
                        "saturday_delivery": "%s" % (self.carrier_id.saturday_delivery),
                        "use_ups_ground_freight_pricing": "%s" % (self.carrier_id.use_ups_ground_freight_pricing),
                        "freight_class": self.carrier_id.ship_engine_ups_freight_class if self.carrier_id.use_ups_ground_freight_pricing else ""
                    },
                    "insurance_provider": "%s" % (self.carrier_id.insurance_provider),
                    "packages": self.get_shipengine_packages(total_bulk_weight, packages),
                    "total_weight": {
                        "value": "%s" % (self.shipping_weight),
                        "unit": "%s" % (self.carrier_id.shipengine_weight_unit)
                    }
                },
                "rate_options": {
                    "carrier_ids": shipengine_carrier_ids
                }
            }
            if self.carrier_id.company_id.security_lead and self.company_id.security_lead < 30:
                sdate = fields.Date.today() + timedelta(days=self.company_id.security_lead)
                body['shipment']['ship_date'] = '%s-%s-%s' % (sdate.year, sdate.month, sdate.day)

            if self.carrier_id.shipengine_bill_to_party and shipengine_bill_to_account:
                body['shipment']['advanced_options'].update({
                    "bill_to_account": "%s" % (shipengine_bill_to_account),
                    "bill_to_country_code": "%s" % (
                            recipient_address.country_id and recipient_address.country_id.code or ""),
                    "bill_to_party": "%s" % (self.carrier_id.shipengine_bill_to_party),
                    "bill_to_postal_code": "%s" % (recipient_address.zip)
                })

            data = json.dumps(body)
            _logger.info("Request Data %s" % (data))
            response_body = request(method='POST', url=url, data=data, headers=headers)
            return response_body
        except Exception as e:
            raise ValidationError(e)

    @api.model
    def get_shipengine_packages(self, bulk_weight=False, packages=False):
        res = []
        for package in packages:
            pack_dict = {"weight": {
                "value": "%s" % (package.shipping_weight),
                "unit": "%s" % (self.carrier_id.shipengine_weight_unit)},
                "dimensions": {
                    "unit": "%s" % (self.carrier_id.package_dimensions),
                    "length": "%s" % (package.package_type_id.packaging_length),
                    "width": "%s" % (package.package_type_id.width),
                    "height": "%s" % (package.package_type_id.height)
                },
                # "insured_value": {
                #     "currency": "usd",
                #     "amount": 110
                # },
                "label_messages": {"reference1": "%s" % (package.name)}}
            res.append(pack_dict)
        if bulk_weight:
            pack_dict = {"weight": {
                "value": "%s" % (bulk_weight),
                "unit": "%s" % (self.carrier_id.shipengine_weight_unit)},
                "dimensions": {
                    "unit": "%s" % (self.carrier_id.package_dimensions),
                    "length": "%s" % (self.carrier_id.shipengine_default_product_packaging_id.packaging_length),
                    "width": "%s" % (self.carrier_id.shipengine_default_product_packaging_id.width),
                    "height": "%s" % (self.carrier_id.shipengine_default_product_packaging_id.height)
                },
                # "insured_value": {
                #     "currency": "usd",
                #     "amount": 110
                # },
                "label_messages": {"reference1": "%s" % (self.name)}}
            res.append(pack_dict)

        return res

    def generate_shipengine_rate(self):
        try:
            charges_obj = self.env['carrier.shipping.charge']
            receipient_address = self.partner_id
            shipper_address = self.picking_type_id.warehouse_id.partner_id
            total_bulk_weight = self.weight_bulk
            packages = self.package_ids
            res = self.get_shipengine_response_data(shipper_address, receipient_address, total_bulk_weight,
                                                    packages=packages,
                                                    shipengine_bill_to_account=False)
            if res.status_code == 200:

                existing_records = self.env['carrier.shipping.charge'].search(
                    [('picking_id', '=', self.id)])
                existing_records.sudo().unlink()

                response_data = res.json()
                _logger.info("Response Data %s" % (response_data))
                rate_responses = response_data.get('rate_response')
                rate_response_info = response_data.get('rate_response').get('rates', False)
                if rate_responses.get('errors'):
                    errors = rate_responses.get('errors')
                    charges_obj.create(
                        {'picking_id': self.id,
                         'rate_amount': 0.0,
                         'service_availability': False,
                         'delivery_carrier_id': self.carrier_id and self.carrier_id.id,
                         'message': "Rate Not Found For This Location %s" %
                                    (errors)})
                if rate_responses.get('status') == "error" and not rate_response_info:
                    errors = rate_responses.get('errors')
                    charges_obj.create(
                        {'picking_id': self.id,
                         'rate_amount': 0.0,
                         'service_availability': False,
                         'delivery_carrier_id': self.carrier_id and self.carrier_id.id,
                         'message': "Rate Not Found For This Location %s" % (errors)})

                for rate_response in rate_response_info:
                    rate_id = rate_response.get('rate_id')
                    shipengine_package_type = rate_response.get('package_type')
                    carrier_code = rate_response.get('carrier_code')
                    shipping_amount = rate_response.get('shipping_amount').get('amount')
                    shipengine_carrier_id = rate_response.get('carrier_id')
                    carrier_delivery_days = rate_response.get('carrier_delivery_days')
                    estimated_delivery_date = rate_response.get('estimated_delivery_date')
                    service_code = rate_response.get('service_code')
                    message = rate_response.get('warning_messages')
                    currency_code = rate_response.get('shipping_amount').get('currency')
                    rate_currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                    exact_price = rate_currency.compute(float(shipping_amount), self.sale_id.currency_id)
                    charges_obj.create({'picking_id': self.id,
                                        'rate_amount': exact_price,
                                        'service_availability': True,
                                        'delivery_carrier_id': self.carrier_id and self.carrier_id.id,
                                        # 'request_with_packages': True,
                                        'message': message if message else "",
                                        'shipengine_rate_id': rate_id,
                                        'shipengine_delivery_days': carrier_delivery_days,
                                        'shipengine_estimated_delivery_date': estimated_delivery_date,
                                        'carrier_id': shipengine_carrier_id,
                                        'carrier_code': carrier_code,
                                        'service_code': service_code,
                                        'shipengine_package_type': shipengine_package_type,
                                        })

                charge_id = charges_obj.search(
                    [('picking_id', '=', self.id), ('service_availability', '=', True), ('rate_amount', '>', 0)],
                    order='rate_amount', limit=1)
                self.carrier_shipping_charge_id = charge_id and charge_id.id
                return {'success': True, 'price': charge_id and charge_id.rate_amount or 0.0,
                        'error_message': False, 'warning_message': False}

            else:
                raise ValidationError("%s, %s, %s" % (res, res.reason, res.text))
        except Exception as e:
            raise ValidationError(e)
