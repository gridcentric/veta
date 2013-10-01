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

"""
Handles all processes relating to Veta Backup functionality

The :py:class:`VetaManager` class is a :py:class:`nova.manager.Manager` that
does periodic processing of backup tasks.
"""

import datetime
from copy import copy

from nova import context as novacontext
from nova import exception
from nova import manager
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova.openstack.common.gettextutils import _

from oslo.config import cfg

from . import meta
from cobalt.nova import api

LOG = logging.getLogger('nova.veta.manager')
CONF = cfg.CONF

veta_opts = [
                cfg.IntOpt('veta_poll_frequency',
                default=60,
                help='The frequency with which the veta'
                     ' service should wake up and perform peroidic tasks'
                     ' (such as triggering new backups or cleaning up'
                     ' old backups.')]
CONF.register_opts(veta_opts)

# Round (down) to nearest minute
def _nearest_minute(dt):
    return datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)

class VetaManager(manager.SchedulerDependentManager):
    def __init__(self, *args, **kwargs):
        self.cobalt_api = api.API()
        super(VetaManager, self).__init__(service_name="veta", *args, **kwargs)

    @manager.periodic_task(spacing=CONF.veta_poll_frequency)
    def _run_periodic_tasks(self, context):
        self._run_backups(context)

    def _run_backups(self, context):
        # The current time
        now = _nearest_minute(timeutils.utcnow())

        # Find instances with backup schedules
        filters = { 'metadata' : { meta.BACKUP_ACTIVE_KEY : True } }
        instances = self.db.instance_get_all_by_filters(context,
                                                        filters)
        LOG.info(_("Instances with backup schedules: %s" % \
                    [instance['uuid'] for instance in instances]))
        for instance in instances:
            # Get instance UUID
            uuid = instance['uuid']

            # Get backup schedules
            instance_metadata = self._instance_metadata_get(instance)
            schedules = jsonutils.loads(instance_metadata.get(
                                            meta.BACKUP_SCHEDULE_KEY, '[]'))

            # Get backups
            filters = { 'metadata' : { meta.BACKUP_FOR_KEY: uuid } }
            backups = self.db.instance_get_all_by_filters(context,
                                                          filters)

            # Trigger new backups for instance
            self._trigger_instance_backups(context, instance, schedules,
                                           backups, now)

            # Cull old instance backups
            self._prune_instance_backups(context, instance, schedules,
                                         backups, now)

    def _trigger_instance_backups(self, context, instance, schedules,
                                  backups, now):
        # List of needed backups
        backups_needed = []

        # Most recent backup for all schedules
        most_recent = self._last_backup(backups)

        # For each schedule,
        for schedule in schedules:
            # Get schedule metadata
            (schedule_uuid, frequency, retention, active) = \
                self._schedule_metadata_get(schedule)

            # Skip inactive backups
            if active != True:
                continue

            # Get last backup for schedule
            last_backup = self._last_backup(backups, schedule_uuid)

            # If the last backup is current,
            if self._backup_is_current(last_backup, now, frequency):
                # Skip this schedule
                continue
            # Else if the most recent backup will do,
            elif self._backup_will_satisfy(most_recent, last_backup,
                                           now, frequency):
                # Update the backup metadata
                self._update_backup_satisfies(context, most_recent,
                                              [schedule_uuid])

                # Move on
                continue
            # Else schedule a backup
            backups_needed.append(schedule_uuid)

        # If we need to perform a backup,
        if len(backups_needed) > 0:
            # Do it
            self._create_backup(context, instance, backups_needed, now)

    def _last_backup(self, backups, schedule_uuid=None):
        for backup in backups:
            (__, __, satisfies) = self._backup_metadata_get(backup)
            if schedule_uuid is None or schedule_uuid in satisfies:
                return backup

        return None

    def _backup_is_current(self, backup, now, frequency):
        # If the backup doesn't exist, it's not current :)
        if not backup:
            return False

        # Get backup metadata
        (ts, __, __) = self._backup_metadata_get(backup)

        # Is the timestamp within the range?
        delta = timeutils.delta_seconds(ts, now)
        return delta < frequency

    def _backup_will_satisfy(self, most_recent, last_backup, now,
                             frequency, fudge_factor=0.04):
        # If the backup doesn't exist, it's won't satisfy
        if not most_recent:
            return False

        # Get backup metadata and time since backup
        (mr_ts, __, __) = self._backup_metadata_get(most_recent)
        mr_delta = timeutils.delta_seconds(mr_ts, now)

        # If the backup isn't recent enough, it won't satisfy
        if mr_delta >= frequency:
            return False

        # Check that the backup was done long enough after the last
        # backup for this schedule
        if last_backup:
            (lb_ts, __, __) = self._backup_metadata_get(last_backup)
            spacing = timeutils.delta_seconds(lb_ts, mr_ts)
            # Allow a bit of a fudge factor to encourage backup
            # schedules not to get out of sync.
            if spacing < (frequency * (1.0 - fudge_factor)):
                return False

        # Everything looks OK
        return True

    def _backup_metadata_get(self, backup):
        backup_metadata = self._instance_metadata_get(backup)
        backup_ts = timeutils.parse_strtime(
                        backup_metadata.get(meta.BACKUP_AT_KEY))
        backup_for = backup_metadata.get(meta.BACKUP_FOR_KEY)
        satisfies = jsonutils.loads(
            backup_metadata.get(meta.BACKUP_SATISFIES_KEY, '[]'))
        return (backup_ts, backup_for, satisfies)

    def _schedule_metadata_get(self, schedule):
        return (schedule[meta.SCHEDULE_ID_KEY],
                schedule[meta.SCHEDULE_FREQUENCY_KEY],
                schedule[meta.SCHEDULE_RETENTION_KEY],
                schedule[meta.SCHEDULE_ACTIVE_KEY])

    def _create_backup(self, context, instance, backups_needed, ts):
        instance_uuid = instance['uuid']
        backup_context = novacontext.RequestContext(instance['user_id'],
                                                    instance['project_id'])
        backup_ts = timeutils.strtime(at=ts)
        backup_name = "%s-backup-%s" % (instance['display_name'],
                                        backup_ts)
        backup = self.cobalt_api.bless_instance(backup_context, instance_uuid,
                    params={ "name" : backup_name })
        backup_uuid = backup['uuid']
        LOG.info(_("Created backup with uuid %s for schedules %s" % \
                (backup_uuid, backups_needed)))
        metadata = {
            meta.BACKUP_AT_KEY : backup_ts,
            meta.BACKUP_FOR_KEY : instance_uuid,
            meta.BACKUP_SATISFIES_KEY : jsonutils.dumps(backups_needed)
        }
        self.db.instance_metadata_update(context, backup_uuid,
                                         metadata, False)

    def _update_backup_satisfies(self, context, backup, uuids,
                                 clean=False):
        uuids = copy(uuids)
        if not clean:
            (__, __, old_uuids) = self._backup_metadata_get(backup)
            uuids.extend(old_uuids)
        metadata = {
            meta.BACKUP_SATISFIES_KEY : jsonutils.dumps(uuids)
        }
        self.db.instance_metadata_update(context, backup['uuid'],
                                         metadata, False)

    def _prune_instance_backups(self, context, instance, schedules,
                                backups, now):
        # For each backup,
        for backup in backups:
            # Get backup metadata
            (__, __, satisfies) = self._backup_metadata_get(backup)

            # Find schedules that it's needed for
            needed_by = self._backup_needed_by(backup, schedules, now)
            LOG.debug(_("Backup %s needed by %s" % (backup['uuid'], needed_by)))

            # If it is still needed,
            if len(needed_by) > 0:
                # Update the backup metadata if necessary
                if needed_by != satisfies:
                    self._update_backup_satisfies(context, backup,
                        needed_by, True)
            # Else,
            else:
                # Discard the backup
                self._discard_backup(context, backup)

    def _backup_needed_by(self, backup, schedules, now):
        # List of schedules needing this backup
        needed_by = []

        # Get backup metadata
        (ts, __, satisfies) = self._backup_metadata_get(backup)

        # For each schedule,
        for schedule in schedules:
            # Get schedule metadata
            (schedule_id, __, retention, active) = \
                self._schedule_metadata_get(schedule)

            # If this backup was made for this schedule,
            if schedule_id in satisfies:
                # If this schedule is inactive, or if
                # this backup is within the retention period,
                delta = timeutils.delta_seconds(ts, now)
                if active == False or delta < retention:
                    # Add the schedule to the list
                    needed_by.append(schedule_id)

        # Return list
        return needed_by

    def _discard_backup(self, context, backup):
        backup_uuid = backup['uuid']
        backup_context = novacontext.RequestContext(backup['user_id'],
                                                    backup['project_id'])
        try:
            self.cobalt_api.discard_instance(backup_context, backup_uuid)
            LOG.info(_("Discarded backup with uuid %s" % backup_uuid))
        except:
            LOG.info(_("Cannot discard backup with uuid %s, will retry" % \
                       backup_uuid))

    def _instance_metadata_get(self, instance_ref):
        '''Returns {key:value} dict of metadata from instance_ref.'''
        result = {}
        for record in instance_ref.get('metadata', []):
            result[record['key']] = record['value']
        return result
