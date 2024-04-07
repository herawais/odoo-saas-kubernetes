odoo.define('web_cohort.CohortView', function (require) {
'use strict';

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var view_registry = require('web.view_registry');
var CohortController = require('web_cohort.CohortController');
var CohortModel = require('web_cohort.CohortModel');
var CohortRenderer = require('web_cohort.CohortRenderer');
const RendererWrapper = require('web.RendererWrapper');

var _t = core._t;
var _lt = core._lt;

var intervals = {
    day: _lt('Day'),
    week: _lt('Week'),
    month: _lt('Month'),
    year: _lt('Year'),
};

var CohortView = AbstractView.extend({
    display_name: _lt('Cohort'),
    icon: 'fa-signal',
    config: _.extend({}, AbstractView.prototype.config, {
        Model: CohortModel,
        Controller: CohortController,
        Renderer: CohortRenderer,
    }),
    viewType: 'cohort',
    searchMenuTypes: ['filter', 'comparison', 'favorite'],

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var fields = this.fields;
        var attrs = this.arch.attrs;
        const additionalMeasures = params.additionalMeasures || [];

        if (!attrs.date_start) {
            throw new Error(_lt('Cohort view has not defined "date_start" attribute.'));
        }
        if (!attrs.date_stop) {
            throw new Error(_lt('Cohort view has not defined "date_stop" attribute.'));
        }


        // Renderer Parameters
        var measures = {};
        _.each(fields, function (field, name) {
            if (name !== 'id' && field.store === true && _.contains(['integer', 'float', 'monetary'], field.type)) {
                measures[name] = field.string;
            }
        });

        this.arch.children.forEach(field => {
            let fieldName = field.attrs.name;
            // Remove invisible fields from the measures
            if (
                !additionalMeasures.includes(fieldName) &&
                field.attrs.invisible && py.eval(field.attrs.invisible)
            ) {
                delete measures[fieldName];
                return;
            }
            if (fieldName in measures && field.attrs.string) {
                measures[fieldName] = field.attrs.string;
            }
        });

        measures.__count__ = _t('Count');
        this.rendererParams.measures = measures;
        this.rendererParams.intervals = intervals;

        // Controller Parameters
        this.controllerParams.measures = _.omit(measures, '__count__');
        this.controllerParams.intervals = intervals;
        this.controllerParams.title = params.title || attrs.string || _t('Untitled');
        // Used in export
        // Retrieve form and list view ids from the action to open those views
        // when a row of the cohort view is clicked
        this.controllerParams.views = [
            _findViewID('list'),
            _findViewID('form'),
        ];
        function _findViewID(viewType) {
            var action = params.action;

            if (action === undefined) {
                return [false, viewType];
            }
            var contextID = viewType === 'list' ? action.context.list_view_id : action.context.form_view_id;
            var result = _.findWhere(action.views, {type: viewType});
            return [contextID || (result ? result.viewID : false), viewType];
        }
    },


    _updateMVCParams: function () {
        this._super.apply(this, arguments);
        // Model Parameters
        var context = this.loadParams.context;
        var attrs = this.arch.attrs;
        this.loadParams.dateStart = context.cohort_date_start ||  attrs.date_start;
        this.loadParams.dateStop = context.cohort_date_stop ||  attrs.date_stop;
        this.loadParams.mode = context.cohort_mode || attrs.mode || 'retention';
        this.loadParams.timeline = context.cohort_timeline || attrs.timeline || 'forward';
        this.loadParams.measure = context.cohort_measure ||  attrs.measure || '__count__';
        this.loadParams.interval = context.cohort_interval || attrs.interval || 'day';

        this.rendererParams.mode = this.loadParams.mode;
        this.rendererParams.timeline = this.loadParams.timeline;
        this.rendererParams.dateStartString = this.fields[this.loadParams.dateStart].string;
        this.rendererParams.dateStopString = this.fields[this.loadParams.dateStop].string;

        this.controllerParams.dateStartString = this.rendererParams.dateStartString;
        this.controllerParams.dateStopString = this.rendererParams.dateStopString;
        this.controllerParams.timeline = this.rendererParams.timeline;
    },
     /**
     * @override
     */
    getRenderer(parent, state) {
        state = Object.assign({}, state, this.rendererParams);
        return new RendererWrapper(null, this.config.Renderer, state);
    },
});

view_registry.add('cohort', CohortView);

return CohortView;

});
