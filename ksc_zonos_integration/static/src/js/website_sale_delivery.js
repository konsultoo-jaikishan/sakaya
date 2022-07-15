odoo.define('ksc_zonos_integration.checkout', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
require('website_sale_delivery.checkout');

var _t = core._t;

publicWidget.registry.websiteSaleDelivery.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _handleCarrierUpdateResult: function (result) {
        this._super.apply(this, arguments);
        if (result.new_amount_duties) {
            $('#order_duties .monetary_field').html(result.new_amount_duties);
        }
        if (result.new_amount_fees) {
            $('#order_fees .monetary_field').html(result.new_amount_fees);
        }
        if (result.new_zonos_tax) {
            $('#zonos_tax .monetary_field').html(result.new_zonos_tax);
        }
    },
});
});
