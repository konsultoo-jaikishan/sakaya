# -*- coding: utf-8 -*-
import logging
import json
import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_duties = fields.Monetary(string='Import-Duties')
    amount_fees = fields.Monetary(string='Import-Fees')
    zonos_tax = fields.Monetary(string='Import-Tax')
    amount_total_zonos = fields.Monetary(string='Total')

    @api.depends('order_line.price_total', 'amount_duties', 'amount_fees', 'zonos_tax')
    def _amount_all(self):
        super(SaleOrder, self)._amount_all()
        for order in self:
            amount_untaxed = sum(order.order_line.mapped('price_subtotal'))
            amount_tax = sum(order.order_line.mapped('price_tax'))
            order.update({
                'amount_total_zonos': amount_untaxed + amount_tax,
                'amount_total': order.amount_total + order.amount_duties + order.amount_fees + order.zonos_tax
            })

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.company_id.use_zonos and not any([self.amount_fees, self.amount_tax, self.amount_duties]):
            self.prepare_zonos_lines_by_merchant()
        return res

    def prepare_zonos_lines_by_merchant(self):
        duties = fees = taxes = 0
        for merchant in self.order_line.product_id.mapped('x_studio_merchant'):
            response_data = self._get_international_charges(merchant)
            if response_data and response_data.get('amount_subtotal'):
                duties += response_data.get('amount_subtotal').get('duties') if response_data.get(
                    'amount_subtotal').get('duties') else 0
                fees += response_data.get('amount_subtotal').get('fees') if response_data.get('amount_subtotal').get(
                    'fees') else 0
                taxes += response_data.get('amount_subtotal').get('taxes') if response_data.get('amount_subtotal').get(
                    'taxes') else 0
        self.amount_duties = duties
        self.amount_fees = fees
        self.zonos_tax = taxes

    def _get_international_charges(self, merchant_id):
        order = self
        response_data = {}
        if order:
            secret_token = self.company_id.zonos_service_token
            if secret_token:
                url = "https://api.zonos.com/v1/landed_cost"
                headers = {
                    'zonos-version': '2021-01-01',
                    'Content-Type': 'application/json',
                    'serviceToken': secret_token,
                }

                items = []
                for line in order.order_line.filtered(
                        lambda rec: rec.product_id.x_studio_merchant.id == merchant_id.id and not rec.is_delivery):
                    line_vals = {
                        "id": line.id,
                        "amount": line.price_subtotal,
                        "amount_discount": line.discount,
                        "category": line.product_id.categ_id.name,
                        "description_retail": line.product_id.name,
                        "detail": "",
                        "quantity": line.product_uom_qty
                    }
                    items.append(line_vals)

                data = {
                    "currency": order.currency_id.name,
                    "items": items,
                    "ship_from_country": merchant_id.country_id.code,
                    "ship_to": {
                        "city": order.partner_shipping_id.city,
                        "country": order.partner_shipping_id.country_id.code,
                        "postal_code": order.partner_shipping_id.zip,
                        "state": order.partner_shipping_id.state_id.code
                    },
                    "shipping": {
                        "amount": 0.0,
                        "amount_discount": 0,
                        "service_level": ""
                    }
                }

                response = requests.post(url, headers=headers, data=json.dumps(data))
                if response.status_code == 401:
                    _logger.warning("Unauthorized Access")
                    return response_data

                _logger.warning(json.loads(response.content))
                response_data = json.loads(response.content)
        return response_data
