# Copyright 2013 Gridcentric Inc.
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

from nova.openstack.common import jsonutils
from nova.openstack.common import timeutils

from . import meta

def parse_backup(backup):
    backup_ts = timeutils.parse_strtime(
                    backup.get(meta.BACKUP_AT_KEY))
    backup_for = backup.get(meta.BACKUP_FOR_KEY)
    satisfies = jsonutils.loads(
        backup.get(meta.BACKUP_SATISFIES_KEY, '[]'))
    return (backup_ts, backup_for, satisfies)

def parse_schedule(schedule):
    return (schedule[meta.SCHEDULE_ID_KEY],
            schedule[meta.SCHEDULE_FREQUENCY_KEY],
            schedule[meta.SCHEDULE_RETENTION_KEY],
            schedule[meta.SCHEDULE_ACTIVE_KEY])

def find_schedule_item(schedules, schedule_id):
    for schedule in schedules:
        if schedule[meta.SCHEDULE_ID_KEY] == schedule_id:
            return schedule
    return None

def schedule_has_conflict(schedule, frequency, retention):
    for item in schedule:
        if item[meta.SCHEDULE_FREQUENCY_KEY] == frequency or \
                item[meta.SCHEDULE_RETENTION_KEY] == retention:
            return item
    return None
