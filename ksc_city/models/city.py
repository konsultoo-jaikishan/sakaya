from odoo import models, fields, api, _


class Xcity(models.Model):
    _name = 'x_city'
    _description = 'City'
    _rec_name = 'x_name'

    x_name = fields.Char(required=True, string="Name")


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_studio_city = fields.Many2one('x_city', string="City")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_studio_merchant = fields.Many2one('res.partner', string="Merchant")
    x_studio_merchant_city = fields.Many2one('x_city', string="Merchant - City",
                                             related="x_studio_merchant.x_studio_city")
    x_studio_merchant_country = fields.Many2one('res.country', string="Merchant - Country",
                                                related="x_studio_merchant.country_id")
