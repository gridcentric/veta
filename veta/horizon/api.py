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

import openstack_dashboard.api as api

from novaclient import shell
from novaclient.v1_1 import client

from .. import meta

# NOTE: We have to reimplement this function here (although it is
# impemented in the API module above). The base module does not currently
# support loading extensions. We will attempt to fix this upstream,
# but in the meantime it is necessary to have this functionality here.
def novaclient(request):
    insecure = getattr(api.nova.settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    api.nova.LOG.debug('novaclient connection created using token "%s" and url "%s"' %
                  (request.user.token.id, api.nova.url_for(request, 'compute')))
    extensions = shell.OpenStackComputeShell()._discover_extensions("1.1")
    c = client.Client(request.user.username,
                      request.user.token.id,
                      extensions=extensions,
                      project_id=request.user.tenant_id,
                      auth_url=api.nova.url_for(request, 'compute'),
                      insecure=insecure)
    c.client.auth_token = request.user.token.id
    c.client.management_url = api.nova.url_for(request, 'compute')
    return c

def populate_instance(client, instance):
    class Instance(object):
        def __init__(self, instance_id, name, schedules, backups):
            self.id = instance_id
            self.name = name
            self.schedules = schedules
            self.backups = backups

    # Populate schedules
    schedules = client.veta.backup_schedule_list(instance)

    # Populate backups
    backups = client.veta.backup_schedule_list_backups(instance, None)

    # Return populated object
    return Instance(instance.id, instance.name, schedules, backups)

def instance_list(request):
    client = novaclient(request)
    instances = client.servers.list(True, {'status': 'active'})

    instance_list = \
        [populate_instance(client, instance) for instance in instances]

    # Sort it, so it doesn't look so dumb.
    return sorted(instance_list, key=lambda i: i.name)

def instance_get(request, instance_id):
    client = novaclient(request)
    instance = client.servers.get(instance_id)
    return populate_instance(client, instance)

def populate_schedule(client, instance_id, schedule):
    class Schedule(object):
        def __init__(self, schedule_id, instance_id,
                     frequency, retention, active):
            self.id = schedule_id
            self.name = schedule_id
            self.instance_id = instance_id
            self.frequency = frequency
            self.retention = retention
            self.active = (active == 1 and "True" or "False")

    # Pull out fields
    schedule_id = schedule[meta.SCHEDULE_ID_KEY]
    frequency = schedule[meta.SCHEDULE_FREQUENCY_KEY]
    retention = schedule[meta.SCHEDULE_RETENTION_KEY]
    active = schedule[meta.SCHEDULE_ACTIVE_KEY]

    # Return populated object
    return Schedule(schedule_id, instance_id, frequency, retention, active)

def schedule_get(request, instance_id, schedule_id):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_list(
        client.servers.get(instance_id))

    for schedule in schedules:
        if schedule[meta.SCHEDULE_ID_KEY] == schedule_id:
            return populate_schedule(client, instance_id, schedule)

    return None

def schedule_list(request, instance_id):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_list(
        client.servers.get(instance_id))

    return [populate_schedule(client, instance_id, schedule) \
            for schedule in schedules]

def schedule_create(request, instance_id, frequency, retention):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_add(
        client.servers.get(instance_id), frequency, retention)

    return schedules

def schedule_enable(request, instance_id, schedule_id):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_enable(
        client.servers.get(instance_id), schedule_id)

    return schedules

def schedule_disable(request, instance_id, schedule_id):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_disable(
        client.servers.get(instance_id), schedule_id)

    return schedules

def schedule_update(request, instance_id, schedule_id,
        frequency, retention):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_update(
        client.servers.get(instance_id), schedule_id,
            frequency, retention)

    return schedules

def schedule_delete(request, instance_id, schedule_id):
    client = novaclient(request)
    schedules = client.veta.backup_schedule_delete(
        client.servers.get(instance_id), schedule_id)

    return schedules

def populate_backup(client, backup):
    class Backup(object):
        def __init__(self, backup_id, name, status):
            self.id = backup_id
            self.name = name
            self.status = status

    # Pull out fields
    backup_id = backup['uuid']
    name = backup['name']
    status = backup['status']

    # Return populated object
    return Backup(backup_id, name, status)

def backup_list(request, instance_id, schedule_id=None):
    client = novaclient(request)
    backups = client.veta.backup_schedule_list_backups(
        client.servers.get(instance_id), schedule_id)

    return [populate_backup(client, backup) \
            for backup in backups]
