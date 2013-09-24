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

from django.conf.urls.defaults import patterns, url
from .views import IndexView, SchedulesView, BackupsView, CreateView, EditView

urlpatterns = patterns('veta.horizon.views',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^(?P<instance_id>[^/]+)/schedules/$', SchedulesView.as_view(), name='schedules'),
    url(r'^(?P<instance_id>[^/]+)/schedules/(?P<schedule_id>[^/]+)/edit$',
        EditView.as_view(), name='edit'),
    url(r'^(?P<instance_id>[^/]+)/backups/$', BackupsView.as_view(), name='backups'),
    url(r'^(?P<instance_id>[^/]+)/create$', CreateView.as_view(), name='create')
)
