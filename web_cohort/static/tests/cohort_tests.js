odoo.define('web_cohort.cohort_tests', function (require) {
'use strict';

var CohortView = require('web_cohort.CohortView');
var testUtils = require('web.test_utils');

const cpHelpers = testUtils.controlPanel;
var createView = testUtils.createView;
var createActionManager = testUtils.createActionManager;
var patchDate = testUtils.mock.patchDate;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            subscription: {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    start: {string: 'Start', type: 'date', sortable: true},
                    stop: {string: 'Stop', type: 'date', sortable: true},
                    recurring: {string: 'Recurring Price', type: 'integer', store: true},
                },
                records: [
                    {id: 1, start: '2017-07-12', stop: '2017-08-11', recurring: 10},
                    {id: 2, start: '2017-08-14', stop: '', recurring: 20},
                    {id: 3, start: '2017-08-21', stop: '2017-08-29', recurring: 10},
                    {id: 4, start: '2017-08-21', stop: '', recurring: 20},
                    {id: 5, start: '2017-08-23', stop: '', recurring: 10},
                    {id: 6, start: '2017-08-24', stop: '', recurring: 22},
                    {id: 7, start: '2017-08-24', stop: '2017-08-29', recurring: 10},
                    {id: 8, start: '2017-08-24', stop: '', recurring: 22},
                ]
            },
            lead: {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    start: {string: 'Start', type: 'date'},
                    stop: {string: 'Stop', type: 'date'},
                    revenue: {string: 'Revenue', type: 'float', store: true},
                },
                records: [
                    {id: 1, start: '2017-07-12', stop: '2017-08-11', revenue: 1200.20},
                    {id: 2, start: '2017-08-14', stop: '', revenue: 500},
                    {id: 3, start: '2017-08-21', stop: '2017-08-29', revenue: 5599.99},
                    {id: 4, start: '2017-08-21', stop: '', revenue: 13500},
                    {id: 5, start: '2017-08-23', stop: '', revenue: 6000},
                    {id: 6, start: '2017-08-24', stop: '', revenue: 1499.99},
                    {id: 7, start: '2017-08-24', stop: '2017-08-29', revenue: 16000},
                    {id: 8, start: '2017-08-24', stop: '', revenue: 22000},
                ]
            },
            attendee: {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    event_begin_date: {string: 'Event Start Date', type: 'date'},
                    registration_date: {string: 'Registration Date', type: 'date'},
                },
                records: [
                    {id: 1, event_begin_date: '2018-06-30', registration_date: '2018-06-13'},
                    {id: 2, event_begin_date: '2018-06-30', registration_date: '2018-06-20'},
                    {id: 3, event_begin_date: '2018-06-30', registration_date: '2018-06-22'},
                    {id: 4, event_begin_date: '2018-06-30', registration_date: '2018-06-22'},
                    {id: 5, event_begin_date: '2018-06-30', registration_date: '2018-06-29'},
                ]
            },
        };
    }
}, function () {
    QUnit.module('CohortView');

    QUnit.test('simple cohort rendering', async function (assert) {
        assert.expect(7);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        assert.containsOnce(cohort, '.table',
            'should have a table');
        assert.ok(cohort.$('.table thead tr:first th:first:contains(Start)').length,
            'should contain "Start" in header of first column');
        assert.ok(cohort.$('.table thead tr:first th:nth-child(3):contains(Stop - By Day)').length,
            'should contain "Stop - By Day" in title');
        assert.ok(cohort.$('.table thead tr:nth-child(2) th:first:contains(+0)').length,
            'interval should start with 0');
        assert.ok(cohort.$('.table thead tr:nth-child(2) th:nth-child(16):contains(+15)').length,
            'interval should end with 15');

        assert.strictEqual(cohort.$buttons.find('.o_cohort_measures_list').length, 1,
            'should have list of measures');
        assert.strictEqual(cohort.$buttons.find('.o_cohort_interval_button').length, 4,
            'should have buttons of intervals');

        cohort.destroy();
    });

    QUnit.test('no content helper', async function (assert) {
        assert.expect(1);
        this.data.subscription.records = [];

        var cohort = await createView({
            View: CohortView,
            model: "subscription",
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        assert.containsOnce(cohort, 'div.o_view_nocontent');

        cohort.destroy();
    });

    QUnit.test('no content helper after update', async function (assert) {
        assert.expect(2);

        var cohort = await createView({
            View: CohortView,
            model: "subscription",
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" measure="recurring"/>',
        });

        assert.containsNone(cohort, 'div.o_view_nocontent');

        await cohort.update({domain: [['recurring', '>', 25]]});

        assert.containsOnce(cohort, 'div.o_view_nocontent');

        cohort.destroy();
    });

    QUnit.test('correctly set by default measure and interval', async function (assert) {
        assert.expect(4);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />'
        });

        assert.hasClass(cohort.$buttons.find('.o_cohort_measures_list [data-field=__count__]'),'selected',
                'count should by default for measure');
        assert.hasClass(cohort.$buttons.find('.o_cohort_interval_button[data-interval=day]'),'active',
                'day should by default for interval');

        assert.ok(cohort.$('.table thead tr:first th:nth-child(2):contains(Count)').length,
            'should contain "Count" in header of second column');
        assert.ok(cohort.$('.table thead tr:first th:nth-child(3):contains(Stop - By Day)').length,
            'should contain "Stop - By Day" in title');

        cohort.destroy();
    });

    QUnit.test('correctly sort measure items', async function (assert) {
        assert.expect(1);

        var data = this.data;
        // It's important to compare capitalized and lowercased words
        // to be sure the sorting is effective with both of them
        data.subscription.fields.flop = {string: 'Abc', type: 'integer', store: true};
        data.subscription.fields.add = {string: 'add', type: 'integer', store: true};
        data.subscription.fields.zoo = {string: 'Zoo', type: 'integer', store: true};

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop"/>',
        });

        const buttonsEls = cpHelpers.getButtons(cohort);
        const measureButtonEls = buttonsEls[0].querySelectorAll('.o_cohort_measures_list > button');
        assert.deepEqual(
            [...measureButtonEls].map(e => e.innerText.trim()),
            ["Abc", "add", "Recurring Price", "Zoo", "Count"]
        );

        cohort.destroy();
    });

    QUnit.test('correctly set measure and interval after changed', async function (assert) {
        assert.expect(8);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" measure="recurring" interval="week" />'
        });

        assert.hasClass(cohort.$buttons.find('.o_cohort_measures_list [data-field=recurring]'),'selected',
                'should recurring for measure');
        assert.hasClass(cohort.$buttons.find('.o_cohort_interval_button[data-interval=week]'),'active',
                'should week for interval');

        assert.ok(cohort.$('.table thead tr:first th:nth-child(2):contains(Recurring Price)').length,
            'should contain "Recurring Price" in header of second column');
        assert.ok(cohort.$('.table thead tr:first th:nth-child(3):contains(Stop - By Week)').length,
            'should contain "Stop - By Week" in title');

        await testUtils.dom.click(cohort.$buttons.find('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(cohort.$buttons.find('.o_cohort_measures_list [data-field=__count__]'));
        assert.hasClass(cohort.$buttons.find('.o_cohort_measures_list [data-field=__count__]'),'selected',
                'should active count for measure');
        assert.ok(cohort.$('.table thead tr:first th:nth-child(2):contains(Count)').length,
            'should contain "Count" in header of second column');

        await testUtils.dom.click(cohort.$buttons.find('.o_cohort_interval_button[data-interval=month]'));
        assert.hasClass(cohort.$buttons.find('.o_cohort_interval_button[data-interval=month]'),'active',
                'should active month for interval');
        assert.ok(cohort.$('.table thead tr:first th:nth-child(3):contains(Stop - By Month)').length,
            'should contain "Stop - By Month" in title');

        cohort.destroy();
    });

    QUnit.test('cohort view without attribute invisible on field', async function (assert) {
        assert.expect(3);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: `<cohort string="Subscription" date_start="start" date_stop="stop"/>`,
        });

        await testUtils.dom.click(cohort.$('.btn-group:first button'));
        assert.containsN(cohort, '.o_cohort_measures_list button', 2);
        assert.containsOnce(cohort, '.o_cohort_measures_list button[data-field="recurring"]');
        assert.containsOnce(cohort, '.o_cohort_measures_list button[data-field="__count__"]');

        cohort.destroy();
    });

    QUnit.test('cohort view with attribute invisible on field', async function (assert) {
        assert.expect(2);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: `
                <cohort string="Subscription" date_start="start" date_stop="stop">
                    <field name="recurring" invisible="1"/>
                </cohort>`,
        });

        await testUtils.dom.click(cohort.$('.btn-group:first button'));
        assert.containsOnce(cohort, '.o_cohort_measures_list button');
        assert.containsNone(cohort, '.o_cohort_measures_list button[data-field="recurring"]');

        cohort.destroy();
    });

    QUnit.test('export cohort', async function (assert) {
        assert.expect(6);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
            session: {
                get_file: async function (params) {
                    var data = JSON.parse(params.data.data);
                    assert.strictEqual(params.url, '/web/cohort/export');
                    assert.strictEqual(data.interval_string, 'Day');
                    assert.strictEqual(data.measure_string, 'Count');
                    assert.strictEqual(data.date_start_string, 'Start');
                    assert.strictEqual(data.date_stop_string, 'Stop');
                    assert.strictEqual(data.title, 'Subscription');
                    params.complete();
                    return true;
                },
            },
        });

        await testUtils.dom.click(cohort.$buttons.find('.o_cohort_download_button'));

        cohort.destroy();
    });

    QUnit.test('when clicked on cell redirects to the correct list/form view ', async function(assert) {
        assert.expect(6);

        var actionManager = await createActionManager({
            data: this.data,
            archs: {
                'subscription,false,cohort': '<cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count__" interval="week" />',
                'subscription,my_list_view,list': '<tree>' +
                        '<field name="start"/>' +
                        '<field name="stop"/>' +
                    '</tree>',
                'subscription,my_form_view,form': '<form>' +
                        '<field name="start"/>' +
                        '<field name="stop"/>' +
                    '</form>',
                'subscription,false,list': '<tree>' +
                        '<field name="recurring"/>' +
                        '<field name="start"/>' +
                    '</tree>',
                'subscription,false,form': '<form>' +
                        '<field name="recurring"/>' +
                        '<field name="start"/>' +
                    '</form>',
                'subscription,false,search': '<search></search>',
            },
            intercepts: {
                do_action: function (ev) {
                    actionManager.doAction(ev.data.action, ev.data.options);
                },
            },
        });

        await actionManager.doAction({
            name: 'Subscriptions',
            res_model: 'subscription',
            type: 'ir.actions.act_window',
            views: [[false, 'cohort'], ['my_list_view', 'list'], ['my_form_view', 'form']],
        });

        // Going to the list view, while clicking Period / Count cell
        await testUtils.dom.click(actionManager.$('td.o_cohort_value:first'));
        assert.strictEqual(actionManager.$('.o_list_view th:nth(1)').text(), 'Start',
                "First field in the list view should be start");
        assert.strictEqual(actionManager.$('.o_list_view th:nth(2)').text(), 'Stop',
                "Second field in the list view should be stop");

        // Going back to cohort view
        await testUtils.dom.click(actionManager.$('.o_back_button'));
        // Going to the list view
        await testUtils.dom.click(actionManager.$('td div.o_cohort_value:first'));
        assert.strictEqual(actionManager.$('.o_list_view th:nth(1)').text(), 'Start',
                "First field in the list view should be start");
        assert.strictEqual(actionManager.$('.o_list_view th:nth(2)').text(), 'Stop',
                "Second field in the list view should be stop");

        // Going to the form view
        await testUtils.dom.click(actionManager.$('.o_list_view .o_data_row'));

        assert.hasAttrValue(actionManager.$('.o_form_view span:first'), 'name', 'start',
                "First field in the form view should be start");
        assert.hasAttrValue(actionManager.$('.o_form_view span:nth(1)'), 'name', 'stop',
                "Second field in the form view should be stop");

        actionManager.destroy();
    });

    QUnit.test('test mode churn', async function(assert) {
        assert.expect(3);

        var cohort = await createView({
            View: CohortView,
            model: 'lead',
            data: this.data,
            arch: '<cohort string="Leads" date_start="start" date_stop="stop" interval="week" mode="churn" />',
            mockRPC: function(route, args) {
                assert.strictEqual(args.kwargs.mode, "churn", "churn mode should be sent via RPC");
                return this._super(route, args);
            },
        });

        assert.strictEqual(cohort.$('td .o_cohort_value:first').text().trim(), '0%', 'first col should display 0 percent');
        assert.strictEqual(cohort.$('td .o_cohort_value:nth(4)').text().trim(), '100%', 'col 5 should display 100 percent');

        cohort.destroy();
    });

    QUnit.test('test backward timeline', async function (assert) {
        assert.expect(7);

        var cohort = await createView({
            View: CohortView,
            model: 'attendee',
            data: this.data,
            arch: '<cohort string="Attendees" date_start="event_begin_date" date_stop="registration_date" interval="day" timeline="backward" mode="churn"/>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.kwargs.timeline, "backward", "backward timeline should be sent via RPC");
                return this._super(route, args);
            },
        });
        assert.ok(cohort.$('.table thead tr:nth-child(2) th:first:contains(-15)').length,
            'interval should start with -15');
        assert.ok(cohort.$('.table thead tr:nth-child(2) th:nth-child(16):contains(0)').length,
            'interval should end with 0');
        assert.strictEqual(cohort.$('td .o_cohort_value:first').text().trim(), '20%', 'first col should display 20 percent');
        assert.strictEqual(cohort.$('td .o_cohort_value:nth(5)').text().trim(), '40%', 'col 6 should display 40 percent');
        assert.strictEqual(cohort.$('td .o_cohort_value:nth(7)').text().trim(), '80%', 'col 8 should display 80 percent');
        assert.strictEqual(cohort.$('td .o_cohort_value:nth(14)').text().trim(), '100%', 'col 15 should display 100 percent');

        cohort.destroy();
    });

    QUnit.test('when clicked on cell redirects to the action list/form view passed in context', async function(assert) {
        assert.expect(6);

        var actionManager = await createActionManager({
            data: this.data,
            archs: {
                'subscription,false,cohort': '<cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count__" interval="week" />',
                'subscription,my_list_view,list': '<tree>' +
                        '<field name="start"/>' +
                        '<field name="stop"/>' +
                    '</tree>',
                'subscription,my_form_view,form': '<form>' +
                        '<field name="start"/>' +
                        '<field name="stop"/>' +
                    '</form>',
                'subscription,false,list': '<tree>' +
                    '<field name="recurring"/>' +
                    '<field name="start"/>' +
                    '</tree>',
                'subscription,false,form': '<form>' +
                        '<field name="recurring"/>' +
                        '<field name="start"/>' +
                    '</form>',
                'subscription,false,search': '<search></search>',
            },
            intercepts: {
                do_action: function (ev) {
                    actionManager.doAction(ev.data.action, ev.data.options);
                },
            },
        });

        await actionManager.doAction({
            name: 'Subscriptions',
            res_model: 'subscription',
            type: 'ir.actions.act_window',
            views: [[false, 'cohort']],
            context: {list_view_id: 'my_list_view', form_view_id: 'my_form_view'},
        });

        // Going to the list view, while clicking Period / Count cell
        await testUtils.dom.click(actionManager.$('td.o_cohort_value:first'));
        assert.strictEqual(actionManager.$('.o_list_view th:nth(1)').text(), 'Start',
                "First field in the list view should be start");
        assert.strictEqual(actionManager.$('.o_list_view th:nth(2)').text(), 'Stop',
                "Second field in the list view should be stop");

        // Going back to cohort view
        await testUtils.dom.click($('.o_back_button'));

        // Going to the list view
        await testUtils.dom.click(actionManager.$('td div.o_cohort_value:first'));
        assert.strictEqual(actionManager.$('.o_list_view th:nth(1)').text(), 'Start',
                "First field in the list view should be start");
        assert.strictEqual(actionManager.$('.o_list_view th:nth(2)').text(), 'Stop',
                "Second field in the list view should be stop");

        // Going to the form view
        await testUtils.dom.click(actionManager.$('.o_list_view .o_data_row'));

        assert.hasAttrValue(actionManager.$('.o_form_view span:first'), 'name', 'start',
                "First field in the form view should be start");
        assert.hasAttrValue(actionManager.$('.o_form_view span:nth(1)'), 'name', 'stop',
                "Second field in the form view should be stop");

        actionManager.destroy();
    });

    QUnit.test('rendering of a cohort view with comparison', async function (assert) {
        assert.expect(29);

        var unpatchDate = patchDate(2017, 7, 25, 1, 0, 0);

        var actionManager = await createActionManager({
            data: this.data,
            archs: {
                'subscription,false,cohort': '<cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count__" interval="week" />',
                'subscription,false,search': `
                    <search>
                        <filter date="start" name="date_filter" string="Date"/>
                    </search>
                `,
            },
            intercepts: {
                do_action: function (ev) {
                    actionManager.doAction(ev.data.action, ev.data.options);
                },
            },
        });

        await actionManager.doAction({
            name: 'Subscriptions',
            res_model: 'subscription',
            type: 'ir.actions.act_window',
            views: [[false, 'cohort']],
        });

        function verifyContents(results) {
            var $tables = actionManager.$('table');
            assert.strictEqual($tables.length, results.length, 'There should be ' + results.length + ' tables');
            var result;
            $tables.each(function () {
                result = results.shift();
                var $table = $(this);
                var rowCount = $table.find('.o_cohort_row_clickable').length;

                if (rowCount) {
                    assert.strictEqual(rowCount, result, 'the table should contain ' + result + ' rows');
                } else {
                    assert.strictEqual($table.find('th:first').text().trim(), result,
                    'the table should contain the time range description' + result);
                }
            });
        }

        // with no comparison, with data (no filter)
        verifyContents([3]);
        assert.containsNone(actionManager, '.o_cohort_no_data');
        assert.containsNone(actionManager, 'div.o_view_nocontent');

        // with no comparison with no data (filter on 'last_year')
        await cpHelpers.toggleFilterMenu(actionManager);
        await cpHelpers.toggleMenuItem(actionManager, 'Date');
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', '2016');

        verifyContents([]);
        assert.containsNone(actionManager, '.o_cohort_no_data');
        assert.containsOnce(actionManager, 'div.o_view_nocontent');

        // with comparison active, data and comparisonData (filter on 'this_month' + 'previous_period')
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', '2016');
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', 'August');
        await cpHelpers.toggleComparisonMenu(actionManager);
        await cpHelpers.toggleMenuItem(actionManager, 'Date: Previous period');

        verifyContents(['August 2017', 2, 'July 2017', 1]);
        assert.containsNone(actionManager, '.o_cohort_no_data');
        assert.containsNone(actionManager, 'div.o_view_nocontent');

        // with comparison active, data, no comparisonData (filter on 'this_year' + 'previous_period')
        await cpHelpers.toggleFilterMenu(actionManager);
        await cpHelpers.toggleMenuItem(actionManager, 'Date');
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', 'August');

        verifyContents(['2017', 3, '2016']);
        assert.containsOnce(actionManager, '.o_cohort_no_data');
        assert.containsNone(actionManager, 'div.o_view_nocontent');

        // with comparison active, no data, comparisonData (filter on 'Q4' + 'previous_period')
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', 'Q4');

        verifyContents(['Q4 2017', 'Q3 2017', 3]);
        assert.containsOnce(actionManager, '.o_cohort_no_data');
        assert.containsNone(actionManager, 'div.o_view_nocontent');

        // with comparison active, no data, no comparisonData (filter on 'last_year' + 'previous_period')
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', '2016');
        await cpHelpers.toggleMenuItemOption(actionManager, 'Date', '2017');

        verifyContents([]);
        assert.containsNone(actionManager, '.o_cohort_no_data');
        assert.containsOnce(actionManager, 'div.o_view_nocontent');

        unpatchDate();
        actionManager.destroy();
    });

    QUnit.test('verify context', async function (assert) {
        assert.expect(1);

        var cohort = await createView({
            View: CohortView,
            model: 'subscription',
            data: this.data,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
            mockRPC: function (route, args) {
                if (args.method === 'get_cohort_data') {
                    assert.ok(args.kwargs.context);
                }
                return this._super.apply(this, arguments);
            },
        });

        cohort.destroy();
    });

    QUnit.test('empty cohort view with action helper', async function (assert) {
        assert.expect(4);

        const cohort = await createView({
            View: CohortView,
            model: "subscription",
            data: this.data,
            arch: '<cohort date_start="start" date_stop="stop"/>',
            domain: [['id', '<', 0]],
            viewOptions: {
                action: {
                    context: {},
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.containsOnce(cohort, '.o_view_nocontent .abc');
        assert.containsNone(cohort, 'table');

        await cohort.reload({ domain: [] });

        assert.containsNone(cohort, '.o_view_nocontent .abc');
        assert.containsOnce(cohort, 'table');

        cohort.destroy();
    });

    QUnit.test('empty cohort view with sample data', async function (assert) {
        assert.expect(7);

        const cohort = await createView({
            View: CohortView,
            model: "subscription",
            data: this.data,
            arch: '<cohort sample="1" date_start="start" date_stop="stop"/>',
            domain: [['id', '<', 0]],
            viewOptions: {
                action: {
                    context: {},
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.hasClass(cohort.el, 'o_view_sample_data');
        assert.containsOnce(cohort, '.o_view_nocontent .abc');
        assert.containsOnce(cohort, 'table.o_sample_data_disabled');

        await cohort.reload({ domain: [] });

        assert.doesNotHaveClass(cohort.el, 'o_view_sample_data');
        assert.containsNone(cohort, '.o_view_nocontent .abc');
        assert.containsOnce(cohort, 'table');
        assert.doesNotHaveClass(cohort.$('table'), 'o_sample_data_disabled');

        cohort.destroy();
    });

    QUnit.test('non empty cohort view with sample data', async function (assert) {
        assert.expect(7);

        const cohort = await createView({
            View: CohortView,
            model: "subscription",
            data: this.data,
            arch: '<cohort sample="1" date_start="start" date_stop="stop"/>',
            viewOptions: {
                action: {
                    context: {},
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.doesNotHaveClass(cohort.el, 'o_view_sample_data');
        assert.containsNone(cohort, '.o_view_nocontent .abc');
        assert.containsOnce(cohort, 'table');
        assert.doesNotHaveClass(cohort.$('table'), 'o_sample_data_disabled');

        await cohort.reload({ domain: [['id', '<', 0]] });

        assert.doesNotHaveClass(cohort.el, 'o_view_sample_data');
        assert.containsOnce(cohort, '.o_view_nocontent .abc');
        assert.containsNone(cohort, 'table');

        cohort.destroy();
    });
});
});
