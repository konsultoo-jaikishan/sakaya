from odoo import models, fields, api


class ShippingMerchant(models.Model):
    _name = "ksc.shipping.merchant"
    _description = "Mapping for multiple deliver and sale order by merchant"

    merchant_id = fields.Many2one('res.partner')
    order_id = fields.Many2one('sale.order')
    carrier_id = fields.Many2one('delivery.carrier')
    price_subtotal = fields.Float(string='Price Subtotal')
    carrier_shipping_charge_id = fields.Many2one("carrier.shipping.charge", string="Shipping Method", copy=False)
