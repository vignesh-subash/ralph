#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from django.db import models as db
from django.db.models.sql.aggregates import Aggregate
from ralph.discovery.models import HistoryCost, Processor


class SpanSum(Aggregate):
    sql_function = "SUM"
    sql_template = ("%(function)s(GREATEST(0, "
                    "DATEDIFF(LEAST(end, DATE('%(end)s')),"
                    "GREATEST(start, DATE('%(start)s')))) * %(field)s)")
    default_alias = 'spansum'

    def __init__(self, lookup, **extra):
        self.lookup = lookup
        self.extra = extra

    def add_to_query(self, query, alias, col, source, is_summary):
        super(SpanSum, self).__init__(col, source, is_summary, **self.extra)
        query.aggregate_select[alias] = self


def total_cost_count(query, start, end):
    total = query.aggregate(
            SpanSum(
                'daily_cost',
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
            ),
        )
    devices = HistoryCost.filter_span(start, end, query).values_list(
        'device')
    dev_ids = {dev[0] for dev in devices}
    count = len(dev_ids)
    core_count = Processor.objects.filter(device__id__in=dev_ids).aggregate(
        db.Sum('cores'))['cores__sum']
    today = datetime.date.today()
    count_now = query.filter(end__gte=today).values_list(
        'device').distinct().count()
    return total['spansum'], count, core_count, count_now

