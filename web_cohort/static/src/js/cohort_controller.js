odoo.define('web_cohort.CohortController', function (require) {
'use strict';

const AbstractController = require('web.AbstractController');
const config = require('web.config');
const core = require('web.core');
const framework = require('web.framework');
const session = require('web.session');

const qweb = core.qweb;
const _t = core._t;

var CohortController = AbstractController.extend({
    custom_events: Object.assign({}, AbstractController.prototype.custom_events, {
        row_clicked: '_onRowClicked',
    }),
    /**
     * @override
     * @param {Widget} parent
     * @param {CohortModel} model
     * @param {CohortRenderer} renderer
     * @param {Object} params
     * @param {string} params.modelName
     * @param {string} params.title
     * @param {Object} params.measures
     * @param {Object} params.intervals
     * @param {string} params.dateStartString
     * @param {string} params.dateStopString
     * @param {string} params.timeline
     * @param {Array[]} params.views
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.title = params.title;
        this.measures = params.measures;
        this.intervals = params.intervals;
        this.dateStartString = params.dateStartString;
        this.dateStopString = params.dateStopString;
        this.timeline = params.timeline;
        this.views = params.views;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the current mode, measure and groupbys, so we can restore the
     * view when we save the current state in the search view, or when we add it
     * to the dashboard.
     *
     * @override
     * @returns {Object}
     */
    getOwnedQueryParams: function () {
        var state = this.model.get();
        return {
            context: {
                cohort_measure: state.measure,
                cohort_interval: state.interval,
            }
        };
    },

    /**
     * @override
     * @param {jQuery} [$node]
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('CohortView.buttons', {
            measures: _.sortBy(_.pairs(this.measures), function(x){ return x[1].toLowerCase(); }),
            intervals: this.intervals,
            isMobile: config.device.isMobile
        }));
        this.$measureList = this.$buttons.find('.o_cohort_measures_list');
        this.$buttons.on('click', 'button', this._onButtonClick.bind(this));
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Makes sure that the buttons in the control panel matches the current
     * state (so, correct active buttons and stuff like that);
     *
     * @override
     */
    updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        var data = this.model.get();
        // Hide download button if no cohort data
        var noData = !data.report.rows.length &&
                    (!data.comparisonReport ||
                    !data.comparisonReport.rows.length);
        this.$buttons.find('.o_cohort_download_button').toggleClass(
            'd-none',
            noData
        );
        if (config.device.isMobile) {
            var $activeInterval = this.$buttons
                .find('.o_cohort_interval_button[data-interval="' + data.interval + '"]');
            this.$buttons.find('.dropdown_cohort_content').text($activeInterval.text());
        }
        this.$buttons.find('.o_cohort_interval_button').removeClass('active');
        this.$buttons
            .find('.o_cohort_interval_button[data-interval="' + data.interval + '"]')
            .addClass('active');
        _.each(this.$measureList.find('.dropdown-item'), function (el) {
            var $el = $(el);
            $el.toggleClass('selected', $el.data('field') === data.measure);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Export cohort data in Excel file
     *
     * @private
     */
    _downloadExcel: function () {
        var data = this.model.get();
        data = _.extend(data, {
            title: this.title,
            interval_string: this.intervals[data.interval].toString(), // intervals are lazy-translated
            measure_string: this.measures[data.measure] || _t('Count'),
            date_start_string: this.dateStartString,
            date_stop_string: this.dateStopString,
            timeline: this.timeline,
        });
        framework.blockUI();
        session.get_file({
            url: '/web/cohort/export',
            data: {data: JSON.stringify(data)},
            complete: framework.unblockUI,
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        });
    },
    /**
     * @private
     * @param {string} interval
     */
    _setInterval: function (interval) {
      this.update({interval: interval});
    },
    /**
     * @private
     * @param {string} measure should be a valid (and aggregatable) field name
     */
    _setMeasure: function (measure) {
        this.update({measure: measure});
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _update: function () {
      this.updateButtons();
      return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Do what need to be done when a button from the control panel is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonClick: function (ev) {
        var $btn = $(ev.currentTarget);
        if ($btn.hasClass('o_cohort_interval_button')) {
            this._setInterval($btn.data('interval'));
        } else if ($btn.hasClass('o_cohort_download_button')) {
            this._downloadExcel();
        } else if ($btn.closest('.o_cohort_measures_list').length) {
            ev.preventDefault();
            ev.stopPropagation();
            this._setMeasure($btn.data('field'));
        }
    },
    /**
     * Open view when clicked on row
     *
     * @private
     * @param {OdooEvent} event
     */
    _onRowClicked: function (event) {
        this.do_action({
            type: 'ir.actions.act_window',
            name: this.title,
            res_model: this.modelName,
            views: this.views,
            domain: event.data.domain,
        });
    },
});

return CohortController;

});
