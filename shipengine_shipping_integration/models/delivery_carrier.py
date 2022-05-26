import json
from requests import request
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[('shipengine', 'Ship Engine')], ondelete={'shipengine': 'set default'})
    shipengine_confirmation_type = fields.Selection([('none', 'none'),
                                                     ('delivery', 'delivery'),
                                                     ('signature', 'signature'),
                                                     ('adult_signature', 'adult_signature'),
                                                     ('direct_signature', 'direct_signature')],
                                                    string="Confirmation Type", default="none",
                                                    help="The possible confirmation values")
    customs_content_type = fields.Selection([('merchandise', 'merchandise'),
                                             ('documents', 'documents'),
                                             ('gift', 'gift'),
                                             ('returned_goods', 'returned_goods'),
                                             ('sample', 'sample')],
                                            string="Customs Content Type", default="merchandise",
                                            help="The type of contents in this shipment. This may impact import duties or customs treatment.")
    insurance_provider = fields.Selection([('none', 'none'),
                                           ('shipsurance', 'shipsurance'),
                                           ('carrier', 'carrier'),
                                           ('third_party', 'third_party')],
                                          string="Insurance Provider", default="none",
                                          help="The possible insurance provider values.")
    non_machinable = fields.Boolean(string="Non Machinable",
                                    help="Indicates that the package cannot be processed automatically because it is too large or irregularly shaped. This is primarily for USPS shipments. See Section 1.2 of the USPS parcel standards for details.",
                                    default=False)
    saturday_delivery = fields.Boolean(string="Saturday Delivery",
                                       help="Enables Saturday delivery, if supported by the carrier.",
                                       default=False)
    use_ups_ground_freight_pricing = fields.Boolean(string="Use UPS Ground Freight Pricing",
                                                    help="Whether to use UPS Ground Freight pricing. If enabled, then a freight_class must also be specified..",
                                                    default=False)
    ship_engine_ups_freight_class = fields.Char(string="UPS Freight Class",
                                                help="Must need to enter if freight class is true")
    delivered_duty_paid = fields.Boolean(string="Delivered Duty Paid",
                                         help="Indicates that the shipper is paying the international delivery duties for this shipment. This option is supported by UPS, FedEx, and DHL Express.",
                                         default=False)
    shipengine_bill_to_party=fields.Selection([('recipient', 'recipient'), ('third_party', 'third_party')],
                                          string="Bill To Part",help="Indicates whether to bill shipping costs to the recipient or to a third-party. When billing to a third-party, the bill_to_account, bill_to_country_code, and bill_to_postal_code fields must also be set.")
    shipengine_weight_unit = fields.Selection([('pound', 'LBS-Pounds'),
                                               ('kilogram', 'KGS-Kilograms'),
                                               ('ounce', 'OZS-Ounces'),
                                               ('gram', 'GM-Gram')], string="Weight UOM",
                                              help="The possible weight unit values", default="kilogram")
    shipengine_default_product_packaging_id = fields.Many2one('stock.package.type', string="Default Package Type")
    package_dimensions = fields.Selection([('inch', 'Inches'), ('centimeter', 'Centimeter')],
                                          string="Package Dimensions", default="inch",
                                          help="The dimension units that are supported by ShipEngine")
    shipengine_lable_print_methods = fields.Selection([('pdf', 'pdf'),
                                                       ('png', 'png'),
                                                       ('zpl', 'zpl')], string="Label File Type",
                                                      help="Specifies the type of label formats. The possible file formats in which shipping labels can be downloaded. We recommend pdf format because it is supported by all carriers, whereas some carriers do not support the png or zpl formats.",
                                                      default="pdf")
    shipengine_carrier_ids = fields.Many2many('shipengine.carrier.details', string="Carrier Details",
                                              help="Carrier details.")

    def shipengine_rate_shipment(self, order):
        # Shipper and Recipient Address
        shipper_address = order.warehouse_id.partner_id
        receipient_address = order.partner_shipping_id
        charges_obj = self.env['carrier.shipping.charge']

        # check sender Address
        if not shipper_address.zip or not shipper_address.city or not shipper_address.country_id:
            return {'success': False, 'price': 0.0,
                    'error_message': ("Please Define Proper Sender Address!"),
                    'warning_message': False}

        # check Receiver Address
        if not receipient_address.zip or not receipient_address.city or not receipient_address.country_id:
            return {'success': False, 'price': 0.0,
                    'error_message': ("Please Define Proper Recipient Address!"),
                    'warning_message': False}

        total_weight = sum([(line.product_id.weight * line.product_uom_qty) for line in order.order_line]) or 0.0
        total_value = order.amount_total
        try:

            res = self.get_shipengine_response_data(shipper_address, receipient_address, total_weight, declared_value=total_value,
                                                           shipengine_bill_to_account=False)
            if res.status_code == 200:
                response_data = res.json()
                _logger.info("Response Data %s" % (response_data))
                rate_responses = response_data.get('rate_response')
                rate_response_info = response_data.get('rate_response').get('rates', False)
                if rate_responses.get('errors'):
                    errors = rate_responses.get('errors')
                    charges_obj.create(
                        {'sale_id': order.id,
                         'rate_amount': 0.0,
                         'service_availability': False,
                         'delivery_carrier_id': self.id,
                         'message': "Rate Not Found For This Location %s" %
                                    (errors)})
                if rate_responses.get('status') == "error" and not rate_response_info:
                    errors = rate_responses.get('errors')
                    charges_obj.create(
                        {'sale_id': order.id,
                         'rate_amount': 0.0,
                         'service_availability': False,
                         'delivery_carrier_id': self.id,
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
                    exact_price = rate_currency.compute(float(shipping_amount), order.currency_id)
                    charges_obj.create({'sale_id': order.id,
                                        'rate_amount': exact_price,
                                        'service_availability': True,
                                        'delivery_carrier_id': self.id,
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
                    [('sale_id', '=', order.id), ('service_availability', '=', True), ('rate_amount', '>', 0)],
                    order='rate_amount', limit=1)
                order.carrier_shipping_charge_id = charge_id and charge_id.id
                return {'success': True, 'price': charge_id and charge_id.rate_amount or 0.0,
                        'error_message': False, 'warning_message': False}

            else:
                raise ValidationError("%s, %s, %s" % (res, res.reason, res.text))
        except Exception as e:
            raise ValidationError(e)

    
    def get_shipengine_response_data(self, shipper_address=False, recipient_address=False, total_weight=False,
                                      declared_value=False,shipengine_bill_to_account=False):
        api_name = 'rates'
        headers = {"Accept": "application/json",
                   "api-key": "%s" % (self.company_id and self.company_id.ship_engine_api_key),
                   "Content-Type": "application/json"}
        url = "%s%s" % (self.company_id and self.company_id.ship_engine_api_url, api_name)
        shipengine_carrier_ids = []
        for shipengine_carrier in self.shipengine_carrier_ids:
            shipengine_carrier_ids.append(shipengine_carrier.shipengine_carrier_id)
        try:
            body = {
                "shipment": {
                    # We are Not Sending Address Validation API So Directly set Non Validation
                    "validate_address": "no_validation",
                    "ship_to": self.ship_engine_address_dict(recipient_address),
                    "ship_from": self.ship_engine_address_dict(shipper_address),
                    "return_to": self.ship_engine_address_dict(shipper_address),
                    "confirmation": "%s" % (self.shipengine_confirmation_type),
                    "customs": {
                        "contents": "%s" % (self.customs_content_type),
                        "non_delivery": "return_to_sender"
                    },
                    "advanced_options": {
                        "contains_alcohol": False,
                        "delivered_duty_paid": "%s" % (self.delivered_duty_paid),
                        "non_machinable": "%s" % (self.non_machinable),
                        "saturday_delivery": "%s" % (self.saturday_delivery),
                        "use_ups_ground_freight_pricing": "%s" % (self.use_ups_ground_freight_pricing),
                        "freight_class": self.ship_engine_ups_freight_class if self.use_ups_ground_freight_pricing else ""
                    },
                    "insurance_provider": "%s" % (self.insurance_provider),
                    "packages": self.get_shipengine_packages(total_weight),
                    "total_weight": {
                        "value": "%s" % (total_weight),
                        "unit": "%s" % (self.shipengine_weight_unit)
                    }
                },
                "rate_options": {
                    "carrier_ids": shipengine_carrier_ids
                }
            }
            if self.shipengine_bill_to_party and shipengine_bill_to_account:
                body['shipment']['advanced_options'].update({
                    "bill_to_account": "%s" % (shipengine_bill_to_account),
                    "bill_to_country_code": "%s" % (
                            recipient_address.country_id and recipient_address.country_id.code or ""),
                    "bill_to_party": "%s" % (self.shipengine_bill_to_party),
                    "bill_to_postal_code": "%s" % (recipient_address.zip)
                })

            data = json.dumps(body)
            _logger.info("Request Data %s" % (data))
            response_body = request(method='POST', url=url, data=data, headers=headers)
            return response_body
        except Exception as e:
            raise ValidationError(e)

    @api.model
    def get_shipengine_packages(self, weight=False):
        res = []
        pack_dict = {"weight": {
            "value": "%s" % (weight),
            "unit": "%s" % (self.shipengine_weight_unit)},
            "dimensions": {
                "unit": "%s" % (self.package_dimensions),
                "length": "%s" % (self.shipengine_default_product_packaging_id.packaging_length),
                "width": "%s" % (self.shipengine_default_product_packaging_id.width),
                "height": "%s" % (self.shipengine_default_product_packaging_id.height)
            },
            # "insured_value": {
            #     "currency": "usd",
            #     "amount": 110
            # },
            "label_messages": {"reference1": "%s"%(self.shipengine_default_product_packaging_id and self.shipengine_default_product_packaging_id.name)}}
        res.append(pack_dict)
        return res

    @api.model
    def shipengine_send_shipping(self, pickings):
        for picking in pickings:
            try:
                if not picking.sale_id.carrier_shipping_charge_id and picking.sale_id.carrier_shipping_charge_id.shipengine_rate_id:
                    raise ValidationError("Rate ID Not Found! Please Click Get Rate!")
                rate_id = picking.carrier_shipping_charge_id.shipengine_rate_id if picking.carrier_shipping_charge_id.shipengine_rate_id else picking.sale_id.carrier_shipping_charge_id.shipengine_rate_id
                url = "%slabels/rates/%s" % (
                self.company_id and self.company_id.ship_engine_api_url,rate_id)
                headers = {"Accept": "application/json",
                           "api-key": "%s" % (
                               self.company_id and self.company_id.ship_engine_api_key),
                           "Content-Type": "application/json"}
                body = {"test_label": not self.prod_environment, "validate_address": "no_validation",
                        "label_format": "pdf"}
                data = json.dumps(body)
                _logger.info("Shipengine Request Data %s" % (data))
                response_data = request(method='POST', url=url, data=data, headers=headers)
                if response_data.status_code in [200, 201]:
                    response_data = response_data.json()
                    _logger.info("Shipengine Response Data %s" % (response_data))
                    final_tracking_no = []
                    for package in response_data.get('packages'):
                        if not package.get('tracking_number') == None:
                            final_tracking_no.append(package.get('tracking_number'))
                        # Add tracking Number in package.
                    label_url = response_data.get('label_download').get('href')
                    label_id = response_data.get('label_id')
                    shipment_id = response_data.get('shipment_id')
                    picking.shipengine_label_url = label_url
                    picking.shipengine_label_id = label_id
                    picking.shipengine_shipment_id = shipment_id
                    picking.carrier_tracking_ref = ','.join(final_tracking_no) if final_tracking_no else ""
                    shipping_data = {
                        'exact_price': float(
                            picking.sale_id.carrier_shipping_charge_id and picking.sale_id.carrier_shipping_charge_id.rate_amount or 0.0),
                        'tracking_number': ','.join(final_tracking_no) if final_tracking_no else ""}
                    shipping_data = [shipping_data]
                    return shipping_data
                else:
                    raise ValidationError(
                        _("Response Code : %s Response Data : %s ") % (response_data.status_code, response_data.text))
            except Exception as e:
                raise ValidationError(e)

    
    def shipengine_cancel_shipment(self, picking):
        label_id= picking.shipengine_label_id
        if label_id and self.company_id:
            headers = {"Accept": "application/json", "api-key": "%s" % (self.company_id and self.company_id.ship_engine_api_key),
                       "Content-Type": "application/json"}
            url = "%slabels/%s/void" % (self.company_id and self.company_id.ship_engine_api_url, label_id)
            try:
                response_data = request(method='PUT', url=url, headers=headers)
                if response_data.status_code == 200:
                    response_data = response_data.json()
                    if response_data.get('approved'):
                        return True
                    else :
                        raise ValidationError("Cancel process not successed, %s" % (response_data))
                else:
                    raise ValidationError("Cancel process not successed, %s" % (response_data.text))
            except Exception as e:
                raise ValidationError(e)
        else:
            raise Warning(_("Shipengine label id is not available!"))
        return True

    @api.model
    def ship_engine_address_dict(self, address_id):
        phone_number = address_id.phone
        if phone_number:
            for special_char in ["&", "\\", "-", "<", ">", '"', '_', '(', ')', ' ']:
                if special_char in phone_number:
                    phone_number = phone_number.replace(special_char, "")

        return {"name": address_id.name,
                "phone": phone_number,
                "company_name": address_id.name or "",
                "address_line1": address_id.street or "",
                "address_line2": address_id.street2 or "",
                "city_locality": address_id.city or "",
                "state_province": address_id.state_id and address_id.state_id.code or "",
                "postal_code": address_id.zip or "",
                "country_code": address_id.country_id and address_id.country_id.code or "",
                # unknown bcz we doesn't pass residential indicator parameter
                "address_residential_indicator": "unknown"}
