# Copyright 2013 GridCentric Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import math

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from . import api

def _exp_range(exp, start, end):
    return map(lambda x: exp ** x,
        range(int(math.log(start, exp)), int(math.ceil(math.log(end, exp)))))

def _build_freq_choices():
    freq_choices = map(lambda x: (60 * x, "Every %d minutes" % x),
                    range(10, 60, 10))
    freq_choices.append((60*60, "Every hour"))
    freq_choices.extend(map(lambda x: (60*60 * x, "Every %d hours" % x),
                            _exp_range(2, 2, 24)))
    freq_choices.append((60*60*24, "Every day"))
    freq_choices.extend(map(lambda x: (60*60*24 * x, "Every %d days" % x),
                            range(2, 7)))
    freq_choices.append((60*60*24*7, "Every week"))
    return freq_choices

def _build_ret_choices():
    ret_choices = [(60*60, "For the last hour")]
    ret_choices.extend(map(lambda x: (60*60 * x, "For the last %d hours" % x),
                            _exp_range(2, 2, 24)))
    ret_choices.append((60*60*24, "For the last day"))
    ret_choices.extend(map(lambda x: (60*60*24 * x, "For the last %d days" % x),
                            range(2, 7)))
    ret_choices.append((60*60*24*7, "For the last week"))
    ret_choices.extend(map(
        lambda x: (60*60*24*7 * x, "For the last %d weeks" % x), range(2, 6)))
    return ret_choices

class CreateSchedule(forms.SelfHandlingForm):
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput())
    frequency = forms.ChoiceField(choices=_build_freq_choices())
    retention = forms.ChoiceField(choices=_build_ret_choices())

    def clean(self):
        data = super(CreateSchedule, self).clean()
        if int(data['frequency']) >= int(data['retention']):
            raise ValidationError(
                _("Retention must be greater than Frequency"))
        else:
            return data

    def handle(self, request, data):
        try:
            schedules = api.schedule_create(request,
                                            data['instance_id'],
                                            int(data['frequency']),
                                            int(data['retention']))
            messages.success(request, _('Schedule created'))
            return True
        except:
            redirect = reverse("horizon:project:veta:index")
            exceptions.handle(request,
                              _('Unable to create schedule.'),
                              redirect=redirect)

class EditSchedule(forms.SelfHandlingForm):
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput())
    schedule_id = forms.CharField(label=_("Schedule ID"),
                                  widget=forms.HiddenInput())
    frequency = forms.ChoiceField(choices=_build_freq_choices())
    retention = forms.ChoiceField(choices=_build_ret_choices())

    def clean(self):
        data = super(EditSchedule, self).clean()
        if int(data['frequency']) >= int(data['retention']):
            raise ValidationError(
                _("Retention must be greater than Frequency"))
        else:
            return data

    def handle(self, request, data):
        try:
            schedules = api.schedule_update(request,
                                            data['instance_id'],
                                            data['schedule_id'],
                                            int(data['frequency']),
                                            int(data['retention']))
            messages.success(request, _('Schedule updated'))
            return True
        except:
            redirect = reverse("horizon:project:veta:schedules",
                kwargs={"instance_id" : data['instance_id']})
            exceptions.handle(request,
                              _('Unable to update schedule.'),
                              redirect=redirect)
