from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):
    @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        res = super(WebsiteSale, self).shop_payment(**post)
        order = request.website.sale_get_order()
        if order and order.company_id.use_zonos:
            order.prepare_zonos_lines_by_merchant()
        return res
