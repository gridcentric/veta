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

from nova import db
from nova import context as novacontext
from nova.compute import api as novaapi
from nova.image import glance
from nova.openstack.common import jsonutils

from oslo.config import cfg

from .. import driver
from .. import meta
from .. import utils

class NovaSnapshotDriver(driver.SnapshotDriver):
    def __init__(self, **kwargs):
        super(NovaSnapshotDriver, self).__init__(**kwargs)
        self.glance = glance.get_default_image_service()
        self.nova = novaapi.API()

    def _instance_metadata(self, context, instance_uuid):
        """ Looks up and returns the instance metadata """
        return db.instance_metadata_get(context, instance_uuid)

    def _instance_metadata_update(self, context, instance_uuid, metadata):
        """ Updates the instance metadata """
        return db.instance_metadata_update(context, instance_uuid,
            metadata, False)

    def _instance_backup_schedule(self, context, instance_uuid):
        """ Returns the backup schedule for the given instance uuid """
        metadata = self._instance_metadata(context, instance_uuid)
        return jsonutils.loads(
            metadata.get(meta.BACKUP_SCHEDULE_KEY, "[]"))

    def _get_backup_schedules(self, backup):
        # Get the backup metadata
        metadata = backup['properties']
        return jsonutils.loads(
            metadata.get(meta.BACKUP_SATISFIES_KEY, "[]"))

    def _clean_backup_dict(self, backup):
        metadata = backup['properties']
        return {
            'uuid' : backup['id'],
            'name' : backup['name'],
            'status' : backup['status'],
            meta.BACKUP_FOR_KEY : metadata[meta.BACKUP_FOR_KEY],
            meta.BACKUP_AT_KEY : metadata[meta.BACKUP_AT_KEY],
            meta.BACKUP_SATISFIES_KEY : metadata.get(
                meta.BACKUP_SATISFIES_KEY, "[]")
        }

    def instance_backup_schedule(self, context, instance_uuid):
        return self._instance_backup_schedule(context, instance_uuid)

    def instance_backup_schedule_update(self, context, instance_uuid,
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

    def backup_metadata_update(self, context, backup_uuid, metadata):
        image_meta = self.glance.show(context, backup_uuid)
        image_meta["properties"].update(metadata)
        self.glance.update(context, backup_uuid, image_meta, purge_props=False)

    def instance_backups(self, context, instance_uuid,
                         schedule_id=None):
        """Get backups for the given instance."""
        filters = { 'properties' : { meta.BACKUP_FOR_KEY : instance_uuid } }
        backups = self.glance.detail(context,
                                     filters=filters)

        # Filter for schedule
        if schedule_id:
            backups = filter(
                lambda b: schedule_id in \
                    self._get_backup_schedules(b), backups)

        # Sort by creation time
        backups = sorted(backups, key=lambda b: b['created_at'])

        # Return backups
        return map(lambda b: self._clean_backup_dict(b), backups)

    def create_snapshot(self, context, instance, name, metadata=None):
        properties = {
            'instance_uuid' : instance['uuid'],
            'image_type' : 'snapshot'
        }
        properties.update(metadata or {})
        image_meta = {
            'owner' : instance['project_id'],
            'name' : name,
            'is_public' : False,
            'properties' : properties
        }
        sent_meta = self.glance.create(context, image_meta)
        return self._clean_backup_dict(
            self.nova.snapshot(context, instance, name=name,
                               image_id=sent_meta['id']))

    def discard_snapshot(self, context, backup_uuid):
        return self.glance.delete(context, backup_uuid)
