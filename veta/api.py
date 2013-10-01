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

from nova import compute
from nova import exception
from nova import utils
from nova.db import base
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging

from . import meta

LOG = logging.getLogger('nova.veta.api')

class API(base.Base):
    """API for interacting with the Veta backup manager."""

    # Allow passing in dummy image_service, but normally use the default
    def __init__(self, **kwargs):
        super(API, self).__init__(**kwargs)
        self.compute_api = compute.API()

    def _get_instance(self, context, instance_uuid):
        """Get a single instance with the given instance_uuid."""
        rv = self.db.instance_get_by_uuid(context, instance_uuid)
        return dict(rv.iteritems())

    def _instance_metadata(self, context, instance_uuid):
        """ Looks up and returns the instance metadata """
        return self.db.instance_metadata_get(context, instance_uuid)

    def _instance_metadata_update(self, context, instance_uuid, metadata):
        """ Updates the instance metadata """
        return self.db.instance_metadata_update(context, instance_uuid,
            metadata, False)

    def _instance_backup_schedule(self, context, instance_uuid):
        """ Returns the backup schedule for the given instance uuid """
        metadata = self._instance_metadata(context, instance_uuid)
        return jsonutils.loads(
            metadata.get(meta.BACKUP_SCHEDULE_KEY, "[]"))

    def _instance_backup_schedule_update(self, context, instance_uuid,
                                         schedule):
        """ Updates the backup schedule for the given instance uuid """
        metadata = self._instance_metadata(context, instance_uuid)
        schedule_key = meta.BACKUP_SCHEDULE_KEY
        active_key = meta.BACKUP_ACTIVE_KEY
        if schedule and len(schedule) > 0:
            # Sort items by frequency
            sorted_schedule = sorted(schedule,
                key=lambda item: item[meta.SCHEDULE_FREQUENCY_KEY])
            metadata[schedule_key] = jsonutils.dumps(sorted_schedule)
            metadata[active_key] = True # This lingers forever, on purpose.
            self._instance_metadata_update(context, instance_uuid, metadata)
            return sorted_schedule
        else:
            metadata[schedule_key] = jsonutils.dumps([])
            self._instance_metadata_update(context, instance_uuid, metadata)
        return []

    def _get_backup_schedules(self, context, backup_uuid):
        # Get the backup metadata
        metadata = self._instance_metadata(context, backup_uuid)
        return jsonutils.loads(
            metadata.get(meta.BACKUP_SATISFIES_KEY, "[]"))

    def _get_instance_backups(self, context, instance_uuid,
            schedule_id=None):
        """Get backups for the given instance."""
        filters = { 'metadata' : { meta.BACKUP_FOR_KEY : instance_uuid } }
        backups = self.db.instance_get_all_by_filters(context,
                                                      filters)

        # Filter for schedule
        if schedule_id:
            backups = filter(
                lambda b: schedule_id in \
                    self._get_backup_schedules(context, b['uuid']),
                    backups)

        # Sort by creation time
        backups = sorted(backups, key=lambda b: b['created_at'])

        # Return UUIDs
        return map(lambda b: b['uuid'], backups)

    def _find_schedule_item(self, schedules, schedule_id):
        for schedule in schedules:
            if schedule[meta.SCHEDULE_ID_KEY] == schedule_id:
                return schedule

        return None

    def _schedule_has_conflict(self, schedule, frequency, retention):
        for item in schedule:
            if item[meta.SCHEDULE_FREQUENCY_KEY] == frequency or \
                    item[meta.SCHEDULE_RETENTION_KEY] == retention:
                return item
        return None

    def backup_schedule_list(self, context, instance_uuid):
        return self._instance_backup_schedule(context, instance_uuid)

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

        schedule = self._instance_backup_schedule(context, instance_uuid)

        # Make sure we're not already full
        if len(schedule) >= meta.MAX_SCHEDULE_ITEMS:
            raise exception.NovaException(
                "Maximum number of schedules (%d) already reached" % \
                    meta.MAX_SCHEDULE_ITEMS)

        # Make sure we don't have any conflicts
        conflict = self._schedule_has_conflict(schedule, frequency, retention)
        if conflict:
            raise exception.NovaException(
                "Schedule conflicts with existing schedule %s" % \
                    conflict[meta.SCHEDULE_ID_KEY])

        # Good to go
        schedule_id = utils.generate_uid('b')
        new_item = { meta.SCHEDULE_ID_KEY : schedule_id,
                     meta.SCHEDULE_FREQUENCY_KEY : frequency,
                     meta.SCHEDULE_RETENTION_KEY : retention,
                     meta.SCHEDULE_ACTIVE_KEY : 1 }
        schedule.append(new_item)
        return self._instance_backup_schedule_update(context, instance_uuid,
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

        schedule = self._instance_backup_schedule(context, instance_uuid)
        # Make sure we don't have any conflicts
        conflict = self._schedule_has_conflict(schedule, frequency, retention)
        if conflict and conflict[meta.SCHEDULE_ID_KEY] != schedule_id:
            raise exception.NovaException(
                "Schedule conflicts with existing schedule %s" % \
                    conflict[meta.SCHEDULE_ID_KEY])
        # Update item
        item = self._find_schedule_item(schedule, schedule_id)
        if not item:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        item[meta.SCHEDULE_FREQUENCY_KEY] = frequency
        item[meta.SCHEDULE_RETENTION_KEY] = retention
        return self._instance_backup_schedule_update(context, instance_uuid,
                                                     schedule)

    def backup_schedule_del(self, context, instance_uuid, params):
        if not 'schedule_id' in params:
            raise exception.NovaException(
                "Backup schedule is missing")
        schedule_id = params['schedule_id']
        schedule = self._instance_backup_schedule(context, instance_uuid)
        item = self._find_schedule_item(schedule, schedule_id)
        if item:
            schedule.remove(item)
        else:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        return self._instance_backup_schedule_update(context, instance_uuid,
                                                     schedule)

    def backup_schedule_set_active(self, context, instance_uuid, params):
        if not 'schedule_id' in params:
            raise exception.NovaException("Backup schedule is missing")
        if not 'active' in params:
            raise exception.NovaException("Missing argument 'active'")
        schedule_id = params['schedule_id']
        active = int(params['active'])
        schedule = self._instance_backup_schedule(context, instance_uuid)
        item = self._find_schedule_item(schedule, schedule_id)
        if item:
            item[meta.SCHEDULE_ACTIVE_KEY] = active
        else:
            raise exception.NovaException("Backup schedule not found: %s" % \
                schedule_id)
        return self._instance_backup_schedule_update(context, instance_uuid,
                                                     schedule)

    def backup_schedule_clear(self, context, instance_uuid):
        return self._instance_backup_schedule_update(context, instance_uuid,
                                                     None)

    def backup_schedule_list_backups(self, context, instance_uuid, params):
        schedule = self._instance_backup_schedule(context, instance_uuid)
        schedule_id = params.get('schedule_id')
        if schedule_id:
            item = self._find_schedule_item(schedule, schedule_id)
            if not item:
                raise exception.NovaException(
                    "Backup schedule not found: %s" % schedule_id)
        return self._get_instance_backups(context, instance_uuid, schedule_id)
