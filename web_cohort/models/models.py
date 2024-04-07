# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.osv import expression

DISPLAY_FORMATS = {
    'day': '%d %b %Y',
    'week': 'W%W %Y',
    'month': '%B %Y',
    'year': '%Y',
}


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_cohort_data(self, date_start, date_stop, measure, interval, domain, mode, timeline):
        """
            Get all the data needed to display a cohort view

            :param date_start: the starting date to use in the group_by clause
            :param date_stop: the date field which mark the change of state
            :param measure: the field to aggregate
            :param interval: the interval of time between two cells ('day', 'week', 'month', 'year')
            :param domain: a domain to limit the read_group
            :param mode: the mode of aggregation ('retention', 'churn') [default='retention']
            :param timeline: the direction to display data ('forward', 'backward') [default='forward']
            :return: dictionary containing a total amount of records considered and a
                     list of rows each of which contains 16 cells.
        """
        rows = []
        columns_avg = defaultdict(lambda: dict(percentage=0, count=0))
        total_value = 0
        initial_churn_value = 0
        measure_is_many2one = self._fields.get(measure) and self._fields.get(measure).type == 'many2one'
        field_measure = (
            [measure + ':count_distinct']
            if measure_is_many2one
            else ([measure] if  self._fields.get(measure) else [])
        )
        row_groups = self._read_group_raw(
            domain=domain,
            fields=[date_start] + field_measure,
            groupby=date_start + ':' + interval
        )
        for group in row_groups:
            dates = group['%s:%s' % (date_start, interval)]
            if not dates:
                continue
            # Split with space for smoothly format datetime field
            clean_start_date = dates[0].split('/')[0].split(' ')[0]
            cohort_start_date = fields.Datetime.from_string(clean_start_date)
            if measure == '__count__':
                value = float(group[date_start + '_count'])
            else:
                value = float(group[measure] or 0.0)
            total_value += value

            sub_group = self._read_group_raw(
                domain=group['__domain'],
                fields=[date_stop] + field_measure,
                groupby=date_stop + ':' + interval
            )
            sub_group_per_period = {}
            for g in sub_group:
                d_stop = g["%s:%s" % (date_stop, interval)]
                if d_stop:
                    date_group = fields.Datetime.from_string(d_stop[0].split('/')[0])
                    group_interval = date_group.strftime(DISPLAY_FORMATS[interval])
                    sub_group_per_period[group_interval] = g

            columns = []
            initial_value = value
            col_range = range(-15, 1) if timeline == 'backward' else range(0, 16)
            for col_index, col in enumerate(col_range):
                col_start_date = cohort_start_date
                if interval == 'day':
                    col_start_date += relativedelta(days=col)
                    col_end_date = col_start_date + relativedelta(days=1)
                elif interval == 'week':
                    col_start_date += relativedelta(days=7 * col)
                    col_end_date = col_start_date + relativedelta(days=7)
                elif interval == 'month':
                    col_start_date += relativedelta(months=col)
                    col_end_date = col_start_date + relativedelta(months=1)
                else:
                    col_start_date += relativedelta(years=col)
                    col_end_date = col_start_date + relativedelta(years=1)

                if col_start_date > datetime.today():
                    columns_avg[col_index]
                    columns.append({
                        'value': '-',
                        'churn_value': '-',
                        'percentage': '',
                    })
                    continue

                significative_period = col_start_date.strftime(DISPLAY_FORMATS[interval])
                col_group = sub_group_per_period.get(significative_period, {})
                if not col_group:
                    col_value = 0.0
                elif measure == '__count__':
                    col_value = col_group[date_stop + '_count']
                else:
                    col_value = col_group[measure] or 0.0

                # In backward timeline, if columns are out of given range, we need
                # to set initial value for calculating correct percentage
                if timeline == 'backward' and col_index == 0:
                    outside_timeline_domain = expression.AND(
                        [
                            group['__domain'],
                            ['|',
                                (date_stop, '=', False),
                                (date_stop, '>=', fields.Datetime.to_string(col_start_date)),
                            ]
                        ]
                    )
                    col_group = self._read_group_raw(
                        domain=outside_timeline_domain,
                        fields=field_measure,
                        groupby=[]
                    )
                    if measure == '__count__':
                        initial_value = float(col_group[0]['__count'])
                    else:
                        initial_value = float(col_group[0][measure] or 0.0)
                    initial_churn_value = value - initial_value

                previous_col_remaining_value = initial_value if col_index == 0 else columns[-1]['value']
                col_remaining_value = previous_col_remaining_value - col_value
                percentage = value and (col_remaining_value) / value or 0
                if mode == 'churn':
                    percentage = 1 - percentage

                percentage = round(100 * percentage, 1)

                columns_avg[col_index]['percentage'] += percentage
                columns_avg[col_index]['count'] += 1
                # For 'week' interval, we display a better tooltip (range like : '02 Jul - 08 Jul')
                if interval == 'week':
                    period = "%s - %s" % (col_start_date.strftime('%d %b'), (col_end_date - relativedelta(days=1)).strftime('%d %b'))
                else:
                    period = col_start_date.strftime(DISPLAY_FORMATS[interval])

                if mode == 'churn':
                    domain = [
                        (date_stop, '<', col_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                    ]
                else:
                    domain = ['|',
                        (date_stop, '>=', col_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                        (date_stop, '=', False),
                    ]

                columns.append({
                    'value': col_remaining_value,
                    'churn_value': col_value + (columns[-1]['churn_value'] if col_index > 0 else initial_churn_value),
                    'percentage': percentage,
                    'domain': domain,
                    'period': period,
                })

            rows.append({
                'date': dates[1],
                'value': value,
                'domain': group['__domain'],
                'columns': columns,
            })

        return {
            'rows': rows,
            'avg': {'avg_value': total_value / len(rows) if rows else 0, 'columns_avg': columns_avg},
        }
