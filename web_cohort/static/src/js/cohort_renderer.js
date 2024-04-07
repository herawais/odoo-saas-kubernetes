odoo.define('web_cohort.CohortRenderer', function (require) {
    'use strict';

    const OwlAbstractRenderer = require('web.AbstractRendererOwl');
    const field_utils = require('web.field_utils');
    const patchMixin = require('web.patchMixin');

    class CohortRenderer extends OwlAbstractRenderer {

        constructor() {
            super(...arguments);
            this.sampleDataTargets = ['table'];
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @param {integer} value
         * @returns {Array} first integers from 0 to value-1
         */
        _range(value) {
            return _.range(value);
        }
        /**
         * @param {float} value
         * @returns {string} formatted value with 1 digit
         */
        _formatFloat(value) {
            return field_utils.format.float(value, null, {
                digits: [42, 1],
            });
        }
        /**
         * @param {float} value
         * @returns {string} formatted value with 1 digit
         */
        _formatPercentage(value) {
            return field_utils.format.percentage(value, null, {
                digits: [42, 1],
            });
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickRow(ev) {
            if (!ev.target.classList.contains('o_cohort_value')) {
                return;
            }
            const rowData = ev.currentTarget.dataset;
            const rowIndex = rowData.rowIndex;
            const colIndex = ev.target.dataset.colIndex;
            const row = (rowData.type === 'data') ?
                this.props.report.rows[rowIndex] :
                this.props.comparisonReport.rows[rowIndex];
            const rowDomain = row ? row.domain : [];
            const cellContent = row ? row.columns[colIndex] : false;
            const cellDomain = cellContent ? cellContent.domain : [];

            const fullDomain = rowDomain.concat(cellDomain);
            if (cellDomain.length) {
                fullDomain.unshift('&');
            }
            if (fullDomain.length) {
                this.trigger('row_clicked', {
                    domain: fullDomain
                });
            }
        }
    }

    CohortRenderer.template = 'web_cohort.CohortRenderer';

    return patchMixin(CohortRenderer);

});
