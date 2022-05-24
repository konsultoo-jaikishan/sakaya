# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PartnerInherit(models.Model):
    _inherit = 'res.partner'

    update_city = fields.Boolean(compute="_compute_update_city", store=True)

    @api.depends('x_studio_city')
    def _compute_update_city(self):
        for partner in self:
            partner.update_city = True
            if partner.x_studio_city:
                partner.city = partner.x_studio_city.x_name

    def _get_portal_order(self, merchant, sale_order):
        result_list = []
        if self.env.user.id != self.env.ref('base.public_user').id:
            partner = self.env.user.partner_id
        else:
            partner = sale_order.partner_id

        if merchant.country_id.name == 'Japan' and partner.x_studio_city.id != merchant.x_studio_city.id:
            result_list = self.get_merchant_carrier(['shipengine'])
        elif merchant.x_studio_city.id == partner.x_studio_city.id:
            result_list = self.get_merchant_carrier(['fixed', 'base_on_rule'])
        else:
            sale_order.order_line.filtered(lambda x: x.product_id.x_studio_merchant.id == merchant.id).unlink()

        return result_list

    def get_merchant_carrier(self, domain):
        return self.env['delivery.carrier'].sudo().search(
            [('delivery_type', 'in', domain)]).ids
