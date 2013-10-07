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

from nova import context as novacontext
from nova import db
from nova.openstack.common import jsonutils

from cobalt.nova import api as cobaltapi

from . import novadriver
from .. import meta

class CobaltSnapshotDriver(novadriver.NovaSnapshotDriver):
    def __init__(self, **kwargs):
        super(CobaltSnapshotDriver, self).__init__(**kwargs)
        self.cobalt = cobaltapi.API()

    def _get_backup_schedules(self, context, backup_uuid):
        # Get the backup metadata
        metadata = self._instance_metadata(context, backup_uuid)
        return jsonutils.loads(
            metadata.get(meta.BACKUP_SATISFIES_KEY, "[]"))

    def _get_backup_dict(self, context, backup):
        backup_uuid = backup['uuid']
        metadata = self._instance_metadata(context, backup_uuid)
        return {
            'uuid' : backup_uuid,
            'name' : backup['name'],
            'status' : 'active',
            meta.BACKUP_FOR_KEY : metadata[meta.BACKUP_FOR_KEY],
            meta.BACKUP_AT_KEY : metadata[meta.BACKUP_AT_KEY],
            meta.BACKUP_SATISFIES_KEY : metadata.get(
                meta.BACKUP_SATISFIES_KEY, "[]")
        }

    def instance_backups(self, context, instance_uuid,
            schedule_id=None):
        """Get backups for the given instance."""
        filters = { 'metadata' : { meta.BACKUP_FOR_KEY : instance_uuid } }
        backups = db.instance_get_all_by_filters(context,
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
        return map(lambda b: self._get_backup_dict(context, b), backups)

    def backup_metadata_update(self, context, backup_uuid, metadata):
        db.instance_metadata_update(context, backup_uuid,
                                    metadata, False)

    def create_snapshot(self, context, instance, name, metadata=None):
        backup_context = novacontext.RequestContext(instance['user_id'],
                                                    instance['project_id'])
        backup = self.cobalt.bless_instance(backup_context,
                                                instance['uuid'],
                                                params={ "name" : name })
        backup_uuid = backup['uuid']
        db.instance_metadata_update(context, backup_uuid,
                                    metadata, False)

    def discard_snapshot(self, context, backup_uuid):
        backup = db.instance_get_by_uuid(context, backup_uuid)
        backup_context = novacontext.RequestContext(backup['user_id'],
                                                    backup['project_id'])
        self.cobalt.discard_instance(backup_context, backup_uuid)
