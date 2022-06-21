# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    use_zonos = fields.Boolean("Use Zonos?")
    zonos_service_token = fields.Char(string="API Key (Zonos)")
