# -*- coding: utf-8 -*-
{
    'name': 'Website Extended',
    'version': '0.1',
    'category': 'Website/Website',
    'summary': 'Website Extended',
    'author':'Konsultoo Software Consulting PVT. LTD.',
    'maintainer': 'Konsultoo Software Consulting PVT. LTD.',
    'contributors': ["Konsultoo Software Consulting PVT. LTD."],
    'depends': ['website_sale_delivery', 'shipengine_shipping_integration'],
    'data': [
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'ksc_website_extended/static/src/js/delivery_selection.js',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': True,

}
