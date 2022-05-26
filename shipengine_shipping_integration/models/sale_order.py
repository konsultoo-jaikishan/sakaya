from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    carrier_shipping_charge_ids = fields.One2many("carrier.shipping.charge", "sale_id", string="Carrier Cost")
    carrier_shipping_charge_id = fields.Many2one("carrier.shipping.charge",string="Shipping Method",copy=False)
