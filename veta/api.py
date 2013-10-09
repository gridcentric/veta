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


"""Handles all requests relating to Veta Backup functionality."""
import sys

from nova import exception
from nova import utils as novautils
from nova.db import base
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging

from . import driver
from . import meta
from . import utils

LOG = logging.getLogger('nova.veta.api')

class API(base.Base):
    """API for interacting with the Veta backup manager."""

    # Allow passing in dummy image_service, but normally use the default
    def __init__(self, **kwargs):
        super(API, self).__init__(**kwargs)
        self.driver = driver.load_snapshot_driver()

    def backup_schedule_list(self, context, instance_uuid):
        return self.driver.instance_backup_schedule(context, instance_uuid)

    def backup_schedule_add(self, context, instance_uuid, params):
        if not 'frequency' in params:
            raise exception.NovaException(
                "Backup schedule is missing 'frequency'")
        if not 'retention' in params:
            raise exception.NovaException(
                "Backup schedule is missing 'retention'")

        frequency = int(params['frequency'])
        retention = int(params['retention'])

        if retention < frequency:
            raise exception.NovaException(
                "Invalid backup schedule: retention < frequency")

        schedule = self.driver.instance_backup_schedule(context, instance_uuid)

        # Make sure we're not already full
        if len(schedule) >= meta.MAX_SCHEDULE_ITEMS:
            raise exception.NovaException(
                "Maximum number of schedules (%d) already reached" % \
                    meta.MAX_SCHEDULE_ITEMS)

        # Make sure we don't have any conflicts
        conflict = utils.schedule_has_conflict(schedule, frequency, retention)
        if conflict:
            raise exception.NovaException(
                "Schedule conflicts with existing schedule %s" % \
                    conflict[meta.SCHEDULE_ID_KEY])

        # Good to go
        schedule_id = novautils.generate_uid('b')
        new_item = { meta.SCHEDULE_ID_KEY : schedule_id,
                     meta.SCHEDULE_FREQUENCY_KEY : frequency,
                     meta.SCHEDULE_RETENTION_KEY : retention,
                     meta.SCHEDULE_ACTIVE_KEY : 1 }
        schedule.append(new_item)
        return self.driver.instance_backup_schedule_update(context,
                                                           instance_uuid,
                                                           schedule)

    def backup_schedule_update(self, context, instance_uuid, params):
        if not 'schedule_id' in params:
            raise exception.NovaException(
                "Backup schedule is missing")
        if not 'frequency' in params:
            raise exception.NovaException(
                "Backup schedule is missing 'frequency'")
        if not 'retention' in params:
            raise exception.NovaException(
                "Backup schedule is missing 'retention'")

        schedule_id = params['schedule_id']
        frequency = int(params['frequency'])
        retention = int(params['retention'])

        if retention < frequency:
            raise exception.NovaException(
                "Invalid backup schedule: retention < frequency")

        schedule = self.driver.instance_backup_schedule(context, instance_uuid)
        # Make sure we don't have any conflicts
        conflict = utils.schedule_has_conflict(schedule, frequency, retention)
        if conflict and conflict[meta.SCHEDULE_ID_KEY] != schedule_id:
            raise exception.NovaException(
                "Schedule conflicts with existing schedule %s" % \
                    conflict[meta.SCHEDULE_ID_KEY])
        # Update item
        item = utils.find_schedule_item(schedule, schedule_id)
        if not item:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        item[meta.SCHEDULE_FREQUENCY_KEY] = frequency
        item[meta.SCHEDULE_RETENTION_KEY] = retention
        return self.driver.instance_backup_schedule_update(context,
                                                           instance_uuid,
                                                           schedule)

    def backup_schedule_del(self, context, instance_uuid, params):
        if not 'schedule_id' in params:
            raise exception.NovaException(
                "Backup schedule is missing")
        schedule_id = params['schedule_id']
        schedule = self.driver.instance_backup_schedule(context, instance_uuid)
        item = utils.find_schedule_item(schedule, schedule_id)
        if item:
            schedule.remove(item)
        else:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        return self.driver.instance_backup_schedule_update(context,
                                                           instance_uuid,
                                                           schedule)

    def backup_schedule_set_active(self, context, instance_uuid, params):
        if not 'schedule_id' in params:
            raise exception.NovaException("Backup schedule is missing")
        if not 'active' in params:
            raise exception.NovaException("Missing argument 'active'")
        schedule_id = params['schedule_id']
        active = int(params['active'])
        schedule = self.driver.instance_backup_schedule(context, instance_uuid)
        item = utils.find_schedule_item(schedule, schedule_id)
        if item:
            item[meta.SCHEDULE_ACTIVE_KEY] = active
        else:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        return self.driver.instance_backup_schedule_update(context,
                                                           instance_uuid,
                                                           schedule)

    def backup_schedule_clear(self, context, instance_uuid):
        return self.driver.instance_backup_schedule_update(context,
                                                           instance_uuid,
                                                           None)

    def backup_schedule_list_backups(self, context, instance_uuid, params):
        schedule_id = params.get('schedule_id')
        if schedule_id:
            schedule = self.driver.instance_backup_schedule(context,
                                                            instance_uuid)
            item = utils.find_schedule_item(schedule, schedule_id)
            if not item:
                raise exception.NovaException(
                    "Backup schedule not found: %s" % schedule_id)
        return self.driver.instance_backups(context, instance_uuid,
                                            schedule_id)
