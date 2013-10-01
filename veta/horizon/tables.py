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

import json

from django import template
from django.core.urlresolvers import reverse
from django.template.defaultfilters import title
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from horizon.utils.filters import replace_underscores

from .. import meta
from . import api
from . import utils

class CreateSchedule(tables.LinkAction):
    name = "schedule"
    verbose_name = _("New Schedule")
    url = "horizon:project:veta:create"
    classes = ("ajax-modal", "btn-camera")

    def get_link_url(self, datum=None):
        if datum:
            instance_id = self.table.get_object_id(datum)
        else:
            instance_id = self.table.kwargs.get("instance_id")
        return reverse(self.url, args=(instance_id,))

class ViewSchedules(tables.LinkAction):
    name = "schedules"
    verbose_name = _("View Schedules")
    url = "horizon:project:veta:schedules"
    classes = ("btn-camera", )

class ViewBackups(tables.LinkAction):
    name = "backups"
    verbose_name = _("View Backups")
    url = "horizon:project:veta:backups"
    classes = ("btn-camera", )

class InstanceRow(tables.Row):
    ajax = False # We may want to change this...

    def get_data(self, request, instance_id):
        instance = api.server_get(request, instance_id)
        return instance

def get_schedules(instance):
    if len(instance.schedules) == 0:
        return "None"
    else:
        freqs = [utils.seconds_to_epoch(s[meta.SCHEDULE_FREQUENCY_KEY]) \
                    for s in instance.schedules]
        return "Every %s" % ", ".join(freqs)

def get_backups(instance):
    if len(instance.backups) == 0:
        return "None"

    return "%d backups" % len(instance.backups)

class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Instance"))
    schedules = tables.Column(get_schedules,
                              verbose_name=_("Backups Scheduled"),
                              sortable=False)
    backups = tables.Column(get_backups,
                            verbose_name=_("Backups"),
                            sortable=False)

    class Meta:
        name = "instances"
        verbose_name = _("Instances")
        row_class = InstanceRow
        row_actions = (CreateSchedule, ViewSchedules, ViewBackups)

class EditSchedule(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Schedule")
    url = "horizon:project:veta:edit"
    classes = ("ajax-modal", "btn-edit")

    def get_link_url(self, datum):
        schedule = datum
        return reverse(self.url, kwargs={
            "instance_id" : schedule.instance_id,
            "schedule_id" : schedule.id})

class EnableSchedule(tables.BatchAction):
    name = "enable"
    action_present = _("Enable")
    action_past = _("Enabled")
    data_type_singular = _("Schedule")
    classes = ("btn-camera", )
    succes_url = "horizon:project:veta:schedules"

    def allowed(self, request, schedule):
        return schedule.active == "False"

    def action(self, request, schedule_id):
        schedule = self.table.get_object_by_id(schedule_id)
        api.schedule_enable(request, schedule.instance_id, schedule_id)

class DisableSchedule(tables.BatchAction):
    name = "disable"
    action_present = _("Disable")
    action_past = _("Disabled")
    data_type_singular = _("Schedule")
    classes = ("btn-camera", )
    succes_url = "horizon:project:veta:schedules"

    def allowed(self, request, schedule):
        return schedule.active == "True"

    def action(self, request, schedule_id):
        schedule = self.table.get_object_by_id(schedule_id)
        api.schedule_disable(request, schedule.instance_id, schedule_id)

class DeleteSchedule(tables.DeleteAction):
    data_type_singular = _("Schedule")
    classes = ("btn-camera", )
    succes_url = "horizon:project:veta:schedules"

    def delete(self, request, schedule_id):
        schedule = self.table.get_object_by_id(schedule_id)
        api.schedule_delete(request, schedule.instance_id, schedule_id)

def get_frequency(schedule):
    return "Every %s" % utils.seconds_to_epoch(schedule.frequency)

def get_retention(schedule):
    return "For the last %s" % utils.seconds_to_epoch(schedule.retention)

class BasicSchedulesTable(tables.DataTable):
    schedule_id = tables.Column("id",
                                verbose_name=_("Schedule ID"))
    frequency = tables.Column(get_frequency,
                              verbose_name=_("Frequency"))
    retention = tables.Column(get_retention,
                              verbose_name=_("Retention"))
    active = tables.Column("active",
                           verbose_name=_("Active"))

    class Meta:
        name = "schedules"
        verbose_name = _("Backup Schedules")

class SchedulesTable(BasicSchedulesTable):
    class Meta:
        multi_select = False
        table_actions = (CreateSchedule, )
        row_actions = (EditSchedule, EnableSchedule,
                       DisableSchedule, DeleteSchedule)

def get_backup_status(backup):
    mapping = {
        'BLESSED' : 'Complete',
        'ERROR' : 'Error'
    }

    return mapping.get(backup.status, "In Progress")

class BackupsTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Backup name"),
                         link=("horizon:project:instances:detail"))
    status = tables.Column(get_backup_status,
                           verbose_name=_("Status"))

    class Meta:
        name = "backups"
        verbose_name = _("Backups")
