from odoo import models, fields, api, _


class Xcity(models.Model):
    _name = 'x_city'
    _description = 'City'
    rec_name = 'x_name'

    x_name = fields.Char(required=True, string="Name")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_studio_merchant = fields.Many2one('res.partner', string="Merchant")


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_studio_city = fields.Many2one('x_city', string="City")
