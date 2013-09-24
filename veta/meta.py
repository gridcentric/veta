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


"""Metadata keys for Veta Backup functionality."""

VETA_META_PREFIX = "veta_"
def _meta_key(key):
    """ Returns the metadata key with the correct prefix prepended """
    return "%s%s" % (VETA_META_PREFIX, key)

# Do backups on this instance
_BACKUP_ACTIVE_KEY = "backup"
BACKUP_ACTIVE_KEY = _meta_key(_BACKUP_ACTIVE_KEY)

# Backup schedule
_BACKUP_SCHEDULE_KEY = "backup_sched"
BACKUP_SCHEDULE_KEY = _meta_key(_BACKUP_SCHEDULE_KEY)

# Schedule item keys
# Note: the shorter these are, the more schedule items
# we can fit.
SCHEDULE_ID_KEY = "i"
SCHEDULE_FREQUENCY_KEY = "f"
SCHEDULE_RETENTION_KEY = "r"
SCHEDULE_ACTIVE_KEY = "a"

# From empirical testing
MAX_SCHEDULE_ITEMS = 5

# Backup time
_BACKUP_AT_KEY = "backup_at"
BACKUP_AT_KEY = _meta_key(_BACKUP_AT_KEY)

# Backup parent
_BACKUP_FOR_KEY = "backup_for"
BACKUP_FOR_KEY = _meta_key(_BACKUP_FOR_KEY)

# Backup schedules satisfied
_BACKUP_SATISFIES_KEY = "backup_ids"
BACKUP_SATISFIES_KEY = _meta_key(_BACKUP_SATISFIES_KEY)
