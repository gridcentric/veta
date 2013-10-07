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

import sys

from oslo.config import cfg

from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.openstack.common.gettextutils import _

from nova import utils

driver_opts = [
    cfg.StrOpt('veta_snapshot_driver',
               default='novadriver.NovaSnapshotDriver',
               help='Driver to use for taking snapshots. Options '
                    'include: novadriver.NovaSnapshotDriver, '
                    'cobaltdriver.CobaltSnapshotDriver.')
]

CONF = cfg.CONF
CONF.register_opts(driver_opts)
LOG = logging.getLogger('nova')

# Snapshot driver interface
class SnapshotDriver(object):
    def instance_backup_schedule(self, context, instance_uuid):
        ''' Get instance backup schedules. '''
        pass

    def instance_backup_schedule_update(self, context, instance_uuid,
                                         schedule):
        ''' Update instance backup schedules. '''
        pass

    def instance_backups(self, context, instance_id,
                         schedule_id=None):
        ''' List instance backups, optionally filtering by
            schedule ID. '''
        pass

    def backup_metadata_update(self, context, backup_uuid, metadata):
        pass

    def create_snapshot(self, context, instance, name, metadata=None):
        pass

    def discard_snapshot(self, context, backup_uuid):
        pass

# Load the snapshot driver
def load_snapshot_driver():
    if not CONF.veta_snapshot_driver:
        LOG.error(_("Snapshot driver option required, but not specified"))
        sys.exit(1)

    LOG.info(_("Loading snapshot driver '%s'") % CONF.veta_snapshot_driver)
    try:
        driver = importutils.import_object_ns('veta.driver',
                                              CONF.veta_snapshot_driver)
        return utils.check_isinstance(driver, SnapshotDriver)
    except ImportError:
        LOG.exception(_("Unable to load the snapshot driver"))
        sys.exit(1)
