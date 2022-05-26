# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    merchant_del_ids = fields.One2many("ksc.shipping.merchant", "order_id")

    def ksc_check_carrier_quotation(self, carrier_id, merchant_id):
        carrier = self.env['delivery.carrier'].browse(carrier_id)
        res = carrier.rate_shipment_by_merchant(self, merchant_id)
        if res.get('success'):
            self.set_delivery_line_by_merchant(carrier, merchant_id, res['price'])
            self.delivery_rating_success = True
            self.delivery_message = res['warning_message']
        else:
            self.delivery_rating_success = False
            self.delivery_message = res['error_message']

    def set_delivery_line_by_merchant(self, carrier, merchant_id, price):
        shipping_merchant = self.env['ksc.shipping.merchant'].sudo().search(
            [('merchant_id', '=', merchant_id), ('order_id', '=', self.id)])

        if shipping_merchant:
            shipping_merchant.sudo().write({
                'carrier_id': carrier.id,
                 'price_subtotal': price
            })
        else:
            self.env['ksc.shipping.merchant'].sudo().create({
                'carrier_id': carrier.id,
                'price_subtotal': price,
                'order_id': self.id,
                'merchant_id': merchant_id
            })

        delivery_charge = sum(self.env['ksc.shipping.merchant'].sudo().search(
            [('order_id', '=', self.id)]).mapped('price_subtotal'))

        delv_line = self.order_line.filtered(lambda l: l.is_delivery)

        del_name = ''

        for line in self.env['ksc.shipping.merchant'].sudo().search(
            [('order_id', '=', self.id)]):
            del_name += line.carrier_id.name + ': ' + str(line.price_subtotal) + ', '

        if delv_line:
            delv_line.write({
                'price_unit': delivery_charge,
                'name': del_name
            })
        else:
            values = {
                'order_id': self.id,
                'name': del_name,
                'product_uom_qty': 1,
                'product_uom': carrier.product_id.uom_id.id,
                'product_id': carrier.product_id.id,
                'price_unit': delivery_charge,
                'is_delivery': True,
            }
            self.env['sale.order.line'].create(values)

        return bool(carrier)

    def _check_carrier_quotation(self, force_carrier_id=None):
        self.ensure_one()
        shipping_merchant = self.env['ksc.shipping.merchant'].sudo().search(
            [('order_id', '=', self.id)])
        if shipping_merchant:
            shipping_merchant.sudo().unlink()

        delv_line = self.order_line.filtered(lambda l: l.is_delivery)

        if delv_line:
            delv_line.sudo().unlink()

        self.delivery_rating_success = True
        DeliveryCarrier = self.env['delivery.carrier'].search([], limit=1)
        if DeliveryCarrier:
            self.write({'carrier_id': DeliveryCarrier.id})

        DeliveryCarrier = self.env['delivery.carrier']

        if self.only_services:
            self.write({'carrier_id': None})
            return True
        else:
            self = self.with_company(self.company_id)
            if not force_carrier_id and self.partner_shipping_id.property_delivery_carrier_id:
                force_carrier_id = self.partner_shipping_id.property_delivery_carrier_id.id

            carrier = force_carrier_id and DeliveryCarrier.browse(force_carrier_id) or self.carrier_id
            available_carriers = self._get_delivery_methods()
            if carrier:
                if carrier not in available_carriers:
                    carrier = DeliveryCarrier
                else:
                    available_carriers -= carrier
                    available_carriers = carrier + available_carriers
            if force_carrier_id or not carrier or carrier not in available_carriers:
                for delivery in available_carriers:
                    verified_carrier = delivery._match_address(self.partner_shipping_id)
                    if verified_carrier:
                        carrier = delivery
                        break
                self.write({'carrier_id': carrier.id})

        return bool(carrier)

    # def _remove_delivery_line(self):
    #     shipping_merchant = self.env['ksc.shipping.merchant'].search(
    #         [('order_id', '=', self.id)])
    #
    #     if shipping_merchant:
    #         shipping_merchant.unlink()
    #     return super(SaleOrder, self)._remove_delivery_line()


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def base_on_rule_rate_shipment_by_merchant(self, order, merchant_id):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}

        try:
            price_unit = self._get_price_available_by_merchant(order, merchant_id)
        except UserError as e:
            return {'success': False,
                    'price': 0.0,
                    'error_message': e.args[0],
                    'warning_message': False}

        price_unit = self._compute_currency(order, price_unit, 'company_to_pricelist')

        return {'success': True,
                'price': price_unit,
                'error_message': False,
                'warning_message': False}

    def rate_shipment_by_merchant(self, order, merchant_id):
        self.ensure_one()
        if hasattr(self, '%s_rate_shipment_by_merchant' % self.delivery_type):
            res = getattr(self, '%s_rate_shipment_by_merchant' % self.delivery_type)(order, merchant_id)
            # apply margin on computed price
            res['price'] = float(res['price']) * (1.0 + (self.margin / 100.0))
            # save the real price in case a free_over rule overide it to 0
            res['carrier_price'] = res['price']
            # free when order is large enough
            if res['success'] and self.free_over and order._compute_amount_total_without_delivery() >= self.amount:
                res['warning_message'] = _('The shipping is free since the order amount exceeds %.2f.') % (self.amount)
                res['price'] = 0.0
            return res

    def fixed_rate_shipment_by_merchant(self, order, merchant_id):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}
        price = order.pricelist_id.get_product_price(self.product_id, 1.0, order.partner_id)
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def shipengine_rate_shipment_by_merchant(self, order, merchant_id):
        # Shipper and Recipient Address
        # shipper_address = order.warehouse_id.partner_id
        shipper_address = self.env['res.partner'].browse(merchant_id)
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

        total_weight = sum([(line.product_id.weight * line.product_uom_qty) for line in order.order_line.filtered(
            lambda l: l.product_id.x_studio_merchant.id == merchant_id)]) or 0.0
        total_value = sum(order.order_line.filtered(lambda l: l.product_id.x_studio_merchant.id == merchant_id).mapped(
            'price_subtotal'))
        try:

            res = self.get_shipengine_response_data(shipper_address, receipient_address, total_weight,
                                                    declared_value=total_value,
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

    def _get_price_available_by_merchant(self, order, merchant_id):
        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = 0
        total_delivery = 0.0
        for line in order.order_line.filtered(lambda l: l.product_id.x_studio_merchant == merchant_id):
            if line.state == 'cancel':
                continue
            if line.is_delivery:
                total_delivery += line.price_total
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type == "service":
                continue
            qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
        total = (order.amount_total or 0.0) - total_delivery

        total = self._compute_currency(order, total, 'pricelist_to_company')

        return self._get_price_from_picking(total, weight, volume, quantity)
