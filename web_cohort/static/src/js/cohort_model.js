odoo.define('web_cohort.CohortModel', function (require) {
'use strict';

var AbstractModel = require('web.AbstractModel');

var CohortModel = AbstractModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
    * @override
    * @returns {Object}
    */
    __get: function () {
        const { rangeDescription, comparisonRangeDescription } = this.timeRanges;
        return Object.assign({}, this.data, {
            hasContent: !this._isEmpty(),
            isSample: this.isSampleModel,
            rangeDescription,
            comparisonRangeDescription
        });
    },
    /**
     * @override
     * @param {Object} params
     * @param {string} params.modelName
     * @param {string} params.dateStart
     * @param {string} params.dateStop
     * @param {string} params.measure
     * @param {string} params.interval
     * @param {Array[]} params.domain
     * @param {string} params.mode
     * @param {string} params.timeline
     * @param {Object} params.timeRanges
     * @returns {Promise}
     */
    __load: function (params) {
        this.modelName = params.modelName;
        this.dateStart = params.dateStart;
        this.dateStop = params.dateStop;
        this.measure = params.measure;
        this.interval = params.interval;
        this.domain = params.domain;
        this.mode = params.mode;
        this.timeline = params.timeline;
        this.data = {
            measure: this.measure,
            interval: this.interval,
        };
        this.context = params.context;
        this.timeRanges = params.timeRanges;
        return this._fetchData();
    },
    /**
     * Reload data.
     *
     * @param {any} handle
     * @param {Object} params
     * @param {string} [params.measure]
     * @param {string} [params.interval]
     * @param {Array[]} [params.domain]
     * @param {Object} [params.timeRanges]
     * @returns {Promise}
     */
    __reload: function (handle, params) {
        if ('measure' in params) {
            this.data.measure = params.measure;
        }
        if ('interval' in params) {
            this.data.interval = params.interval;
        }
        if ('domain' in params) {
            this.domain = params.domain;
        }
        if ('timeRanges' in params) {
            this.timeRanges = params.timeRanges;
        }
        return this._fetchData();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch cohort data.
     *
     * @private
     * @returns {Promise}
     */
    _fetchData: function () {
        const domains = this._getDomains();
        const proms = domains.map(domain => {
            return this._rpc({
                model: this.modelName,
                method: 'get_cohort_data',
                kwargs: {
                    date_start: this.dateStart,
                    date_stop: this.dateStop,
                    measure: this.data.measure,
                    interval: this.data.interval,
                    domain: domain,
                    mode: this.mode,
                    timeline: this.timeline,
                    context: this.context
                }
            });
        });
        return Promise.all(proms).then(([report, comparisonReport]) => {
            this.data.report = report;
            this.data.comparisonReport = comparisonReport;
        });
    },
    /**
     * @private
     * @returns {Array[]}
     */
    _getDomains: function () {
        const { range, comparisonRange } = this.timeRanges;
        if (!range) {
            return [this.domain];
        }
        return [
            this.domain.concat(range),
            this.domain.concat(comparisonRange),
        ];
    },
    /**
     * @override
     */
    _isEmpty() {
        let rowCount = this.data.report.rows.length;
        if (this.data.comparisonReport) {
            rowCount += this.data.comparisonReport.rows.length;
        }
        return rowCount === 0;
    },
});

return CohortModel;

});
