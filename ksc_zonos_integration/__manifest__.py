# -*- coding: utf-8 -*-
{
    "name": "Odoo Zonos Connector",
    "version": "1.0",
    "category": "API",
    "author": "Konsultoo",
    "website": "https://www.konsultoo.com",
    "summary": "Zonos API Integration",
    "depends": ["ksc_website_extended"],
    "data": [
        'views/res_company_views.xml',
        'views/sale_order.xml',
        'views/website_sale_delivery_templates.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False

}
