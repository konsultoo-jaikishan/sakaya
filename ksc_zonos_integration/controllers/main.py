from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):
    # @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    # def shop_payment(self, **post):
    #     res = super(WebsiteSale, self).shop_payment(**post)
    #     order = request.website.sale_get_order()
    #     if order and order.company_id.use_zonos:
    #         order.prepare_zonos_lines_by_merchant()
    #     return res

    @http.route(['/shop/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_eshop_carrier(self, **post):
        res = super(WebsiteSale, self).update_eshop_carrier(**post)
        order = request.website.sale_get_order()
        if order and order.company_id.use_zonos:
            order.prepare_zonos_lines_by_merchant()
            Monetary = request.env['ir.qweb.field.monetary']
            currency = order.currency_id
            if res:
                res['new_amount_duties'] = Monetary.value_to_html(order.amount_duties,
                                                                  {'display_currency': currency})
                res['new_amount_fees'] = Monetary.value_to_html((order.amount_fees),
                                                                {'display_currency': currency})
                res['new_zonos_tax'] = Monetary.value_to_html((order.zonos_tax),
                                                              {'display_currency': currency})
        return res
