# -*- coding: utf-8 -*-pack
{
    # App information
    'name': 'Ship Engine Odoo Shipping Integration',
    'category': 'Website',
    'version': '15.0.25.11.2021',
    'summary': " ",
    'description': """ Using ShipEngine Odoo Integration we easily manage shipping operation in odoo. using 
    integration easily export order information to shipengine and generate label and get tracking detail in odoo.We 
    are providing following modules shipstation,canada post,bigcommerce,ebay.""",
    'depends': ['delivery', 'sale'],
    'live_test_url': 'https://www.vrajatechnologies.com/contactus',
    'data': [
        'views/res_company.xml',
        'security/ir.model.access.csv',
        'views/delivery_carrier_view.xml',
        'views/stock_picking.xml',
        'views/sale_order.xml'
    ],    
    'images': ['static/description/shipengine_cover_image.png'],
    'author': 'Vraja Technologies',
    'maintainer': 'Vraja Technologies',
    'website':'https://www.vrajatechnologies.com',
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '279',
    'currency': 'EUR',
    'license': 'OPL-1',

}
# Fix Bug On Get Rate Method
