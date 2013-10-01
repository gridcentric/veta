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

import json
import webob
from webob import exc
import functools

from nova import exception as novaexc
from nova.openstack.common import log as logging
from nova.api.openstack import extensions
from nova.api.openstack import wsgi

from veta.api import API

LOG = logging.getLogger("nova.api.extensions.veta")

authorizer = extensions.extension_authorizer('compute', 'veta')

def convert_exception(action):
    def fn(self, *args, **kwargs):
        try:
            return action(self, *args, **kwargs)
        except novaexc.NovaException as error:
            raise exc.HTTPBadRequest(explanation=unicode(error))
    # note(dscannell): Openstack sometimes does matching on the function name
    # so we need to ensure that the decorated function returns with the same
    # function name as the action.
    fn.__name__ = action.__name__
    return fn

def authorize(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        context = kwargs['req'].environ["nova.context"]
        authorizer(context)
        return f(*args, **kwargs)
    return wrapper

class VetaServerControllerExtension(wsgi.Controller):
    """
    The OpenStack Extension definition for Veta Backup capabilities.
    """

    def __init__(self):
        super(VetaServerControllerExtension, self).__init__()
        self.backup_api = API()

    @wsgi.action('backup_schedule_list')
    @convert_exception
    @authorize
    def _backup_schedule_list(self, req, id, body):
        context = req.environ["nova.context"]
        result = self.backup_api.backup_schedule_list(context, id)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_add')
    @convert_exception
    @authorize
    def _backup_schedule_add(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_add', {})
        result = self.backup_api.backup_schedule_add(context, id, params)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_update')
    @convert_exception
    @authorize
    def _backup_schedule_update(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_update', {})
        result = self.backup_api.backup_schedule_update(context, id, params)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_delete')
    @convert_exception
    @authorize
    def _backup_schedule_del(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_delete', {})
        result = self.backup_api.backup_schedule_del(context, id, params)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_enable')
    @convert_exception
    @authorize
    def _backup_schedule_enable(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_enable', {})
        params.update({ "active" : 1 })
        result = self.backup_api.backup_schedule_set_active(context, id, params)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_disable')
    @convert_exception
    @authorize
    def _backup_schedule_disable(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_disable', {})
        params.update({ "active" : 0 })
        result = self.backup_api.backup_schedule_set_active(context, id, params)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_clear')
    @convert_exception
    @authorize
    def _backup_schedule_clear(self, req, id, body):
        context = req.environ["nova.context"]
        result = self.backup_api.backup_schedule_clear(context, id)
        return self._build_schedule(req, result)

    @wsgi.action('backup_schedule_list_backups')
    @convert_exception
    @authorize
    def _backup_schedule_list_backups(self, req, id, body):
        context = req.environ["nova.context"]
        params = body.get('backup_schedule_list_backups', {})
        result = self.backup_api.backup_schedule_list_backups(context, id,
                                                              params)
        return self._build_instance_list(req, result)

    def _build_schedule(self, req, schedule):
        return webob.Response(status_int=200, body=json.dumps(schedule))

    def _build_instance_list(self, req, instances):
        return webob.Response(status_int=200, body=json.dumps(instances))

class Veta_extension(object):
    """
    The OpenStack Extension definition for Veta Backup capabilities.
    """

    name = "Veta"
    alias = "GC-EXT-VETA"
    namespace = "http://docs.gridcentric.com/openstack/ext/backup/api/v1"
    updated = '2013-04-10T13:52:50-07:00' ##TIMESTAMP##

    def __init__(self, ext_mgr):
        ext_mgr.register(self)

    def get_controller_extensions(self):
        extension_list = []
        extension_set = [
            (VetaServerControllerExtension, 'servers'),
            ]
        for class_ref, collection in extension_set:
            controller = class_ref()
            ext = extensions.ControllerExtension(self, collection, controller)
            extension_list.append(ext)

        return extension_list
