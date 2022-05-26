from odoo import models,fields,api
from odoo.exceptions import Warning, ValidationError, UserError

class CarrierWiseShippingCharge(models.Model):
    _name="carrier.shipping.charge"
    _description = "Carrier Shipping Charges"
    _rec_name="service_code"

    shipengine_rate_id = fields.Char(string="Rate Request ID", help="We are using this ID when confirm the label Request.")
    delivery_carrier_id = fields.Many2one("delivery.carrier", string="Carrier")
    rate_amount=fields.Float(string="Service Rate",help="Carrier Shipping Cost Given by Provider")
    shipengine_delivery_days= fields.Char(string="Delivery Days", help="Shipengine provide this information. Estimate delivery day indicates.")
    shipengine_estimated_delivery_date= fields.Char(string="Estimated Delivery Date", help="Shipengine provide this information. Estimate delivery dates indicates.")
    sale_id=fields.Many2one("sale.order",string="Sale Order")
    picking_id = fields.Many2one("stock.picking", string="Delivery Order")
    message=fields.Char(string="Message",help="Error Message given by provider")
    service_availability=fields.Boolean(string='Service Availability',help="If service available for available location than values is true otherwise false")
    shipengine_package_type= fields.Char(string="Shipengine Package Type", help="Shipengine package Type, Provided by shipengine.")
    carrier_id=fields.Char(string="Carrier ID", help="Shipengine provide this information. It indicates Carrier ID.")
    carrier_code=fields.Char(string="Carrier Name", help="Shipengine provide this information. It indicates Carrier name, Like UPS, USPS etc..")
    service_code=fields.Char(string="Shipping Service", help="Shipengine provide this information. It indicates Service Name.")
    requested_no_of_packages=fields.Integer(string='Number Of Packages',help="Number Of Packages indicates to identify total number of requested packages.")

    def set_service(self):
        self.ensure_one()
        if self.service_availability:
            if self.sale_id:
                self.sale_id.carrier_shipping_charge_id=self.id
            if self.picking_id:
                self.picking_id.carrier_shipping_charge_id = self.id
        else:
            raise ValidationError("This Carrier Is Not Useful For Existing Location! %s"%(self.message))
