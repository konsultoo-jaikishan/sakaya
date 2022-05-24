odoo.define('ksc_website_extended.delivery_selection', function (require) {
    'use strict';

    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    require('website_sale_delivery.checkout');

    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();
    var payment_status = false;
    publicWidget.registry.websiteSaleDelivery.include({
        start: function () {
            var self = this;
            /*My comment code*/
            // var $carriers = $('#delivery_carrier input[name="delivery_type"]');
            /*My comment code*/
            var $carriers = $('#delivery_carrier input[type="radio"]');
            var $payButton = $('button[name="o_payment_submit_button"]');
            // Workaround to:
            // - update the amount/error on the label at first rendering
            // - prevent clicking on 'Pay Now' if the shipper rating fails
            if ($carriers.length > 0) {
                if ($carriers.filter(':checked').length === 0) {
                    $payButton.prop('disabled', true);
                    var disabledReasons = $payButton.data('disabled_reasons') || {};
                    disabledReasons.carrier_selection = true;
                    $payButton.data('disabled_reasons', disabledReasons);
                }
                $carriers.filter(':checked').click();
            }
            // Asynchronously retrieve every carrier price
            _.each($carriers, function (carrierInput, k) {
                this._showLoading($(carrierInput));
                this1._rpc({
                    route: '/shop/carrier_rate_shipment',
                    params: {
                        'carrier_id': carrierInput.value,
                    },
                }).then(this._handleCarrierUpdateResultBadge.bind(this));
            });

            return this._super.apply(this, arguments);
        },
        _onCarrierClick: function (ev) {
            var self = this;
            var $radio = $(ev.currentTarget).find('input[type="radio"]');
            var radio_obj = {}

            radio_obj['merchant_id'] = $radio.attr('merchant');
            radio_obj['delivery_method_id'] = $radio.val();
            this._showLoading($radio);
            $radio.prop("checked", true);

            var $payButton = $('button[name="o_payment_submit_button"]');
            $payButton.prop('disabled', true);
            var disabledReasons = $payButton.data('disabled_reasons') || {};
            disabledReasons.carrier_selection = true;
            $payButton.data('disabled_reasons', disabledReasons);
            dp.add(this._rpc({
                route: '/shop/update_carrier',
                params: {
                    carrier_id: radio_obj,
                },
            })).then(this._handleCarrierUpdateResult.bind(this));
            // })).then(this._handleCarrierUpdateResult.bind(self));

        },


        _handleCarrierUpdateResultBadge: function (result) {
            // this._super.apply(this, arguments);
            // var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');
            var $carrierBadge = $('#delivery_carrier [value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');
            var $payButton = $('button[name="o_payment_submit_button"]');
            // console.log(":::::::::::::::::::::::::$carrierBadge::::::::::::::::::", $carrierBadge)
            if (result.status === true) {
                // if free delivery (`free_over` field), show 'Free', not '$0'
                if (result.is_free_delivery) {
                    $carrierBadge.text(_t('Free'));
                } else {
                    $carrierBadge.html(result.merchant_carrier_amount);
                }
                $carrierBadge.removeClass('o_wsale_delivery_carrier_error');
            } else {
                $carrierBadge.addClass('o_wsale_delivery_carrier_error');
                $carrierBadge.text(result.error_message);
            }
        },

        _handleCarrierUpdateResult: function (result) {
            console.log(":::::::::::::::dddd::::::::::result::::::::::::::::::",result)
            this._handleCarrierUpdateResultBadge(result);
            var $payButton = $('button[name="o_payment_submit_button"]');
            var $amountDelivery = $('#order_delivery .monetary_field');
            var $amountUntaxed = $('#order_total_untaxed .monetary_field');
            var $amountTax = $('#order_total_taxes .monetary_field');
            var $amountTotal = $('#order_total .monetary_field, #amount_total_summary.monetary_field');


            console.log(":::::::::::::::::::::::::result::::::::::::::::::",result)
            if (result.status === true) {
                $amountDelivery.html(result.new_amount_delivery);
                $amountUntaxed.html(result.new_amount_untaxed);
                $amountTax.html(result.new_amount_tax);
                $amountTotal.html(result.new_amount_total);
                var disabledReasons = $payButton.data('disabled_reasons') || {};
                disabledReasons.carrier_selection = false;
                var total_merchant = $('.merchant_name').length;
                var $carriers_my = $('#delivery_carrier input[type="radio"]');
                console.log(":::::::::::::::::::::::::result::::::::::::::::::",result)
                if (total_merchant == $carriers_my.filter(':checked').length) {
                    $payButton.data('disabled_reasons', disabledReasons);
                    $payButton.prop('disabled', _.contains($payButton.data('disabled_reasons'), true));
                }

            } else {
                $amountDelivery.html(result.new_amount_delivery);
                $amountUntaxed.html(result.new_amount_untaxed);
                $amountTax.html(result.new_amount_tax);
                $amountTotal.html(result.new_amount_total);
            }
            if (result.new_amount_total_raw !== undefined) {
                this._updateShippingCost(result.new_amount_total_raw);
            }
        },

        _showLoading: function ($carrierInput) {
            $carrierInput.siblings('.o_wsale_delivery_badge_price').empty();
            $carrierInput.siblings('.o_wsale_delivery_badge_price').append('<span class="fa fa-circle-o-notch fa-spin"/>');
        },


    });
});

