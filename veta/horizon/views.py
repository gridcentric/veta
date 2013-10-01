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

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables

from openstack_dashboard.api import nova as novaapi

from .. import meta
from . import api
from .forms import CreateSchedule, EditSchedule
from .tables import InstancesTable, BasicSchedulesTable, SchedulesTable, \
                    BackupsTable

class IndexView(tables.DataTableView):
    table_class = InstancesTable
    template_name = 'veta/index.html'

    def get_data(self):
        # Gather our instances
        try:
            instances = api.instance_list(self.request)
        except:
            instances = []
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'))
        return instances

class SchedulesView(tables.DataTableView):
    table_class = SchedulesTable
    template_name = 'veta/schedules.html'

    def get_data(self):
        # Gather our schedules
        try:
            instance_id = self.kwargs['instance_id']
            schedules = api.schedule_list(self.request, instance_id)
        except:
            schedules = []
            exceptions.handle(self.request,
                              _('Unable to retrieve schedules.'))
        return schedules

class BackupsView(tables.DataTableView):
    table_class = BackupsTable
    template_name = 'veta/backups.html'

    def get_data(self):
        # Gather our backups
        try:
            instance_id = self.kwargs['instance_id']
            backups = api.backup_list(self.request, instance_id)
        except:
            backups = []
            exceptions.handle(self.request,
                              _('Unable to retrieve backups.'))
        return backups

class CreateView(forms.ModalFormView):
    form_class = CreateSchedule
    template_name = 'veta/create.html'
    success_url = reverse_lazy("horizon:project:veta:index")

    def get_object(self):
        if not hasattr(self, "_object"):
            try:
                self._object = novaapi.server_get(self.request,
                                                  self.kwargs["instance_id"])
            except:
                redirect = reverse('horizon:project:veta:index')
                exceptions.handle(self.request,
                                  _("Unable to retrieve instance."),
                                  redirect=redirect)
        return self._object

    def get_initial(self):
        return {"instance_id": self.kwargs["instance_id"]}

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        context['instance'] = self.get_object()
        # Add a table
        context['table'] = BasicSchedulesTable(self.request,
                                               data=self.get_data(),
                                               **kwargs)
        return context

    def get_data(self):
        # Gather our schedules
        try:
            instance_id = self.kwargs['instance_id']
            schedules = api.schedule_list(self.request, instance_id)
        except:
            schedules = []
            exceptions.handle(self.request,
                              _('Unable to retrieve schedules.'))
        return schedules

class EditView(forms.ModalFormView):
    form_class = EditSchedule
    template_name = 'veta/edit.html'

    def get_object(self):
        if not hasattr(self, "_object"):
            try:
                self._object = api.schedule_get(self.request,
                                                self.kwargs["instance_id"],
                                                self.kwargs["schedule_id"])
            except:
                redirect = reverse('horizon:project:veta:schedules')
                exceptions.handle(self.request,
                                  _("Unable to retrieve schedule."),
                                  redirect=redirect)
        return self._object

    def get_success_url(self):
        return reverse_lazy("horizon:project:veta:schedules",
            kwargs={"instance_id" : self.kwargs["instance_id"]})
        
    def get_initial(self):
        schedule = self.get_object()
        return {"instance_id": self.kwargs["instance_id"],
                "schedule_id": self.kwargs["schedule_id"],
                "frequency" : schedule.frequency,
                "retention" : schedule.retention}

    def get_context_data(self, **kwargs):
        context = super(EditView, self).get_context_data(**kwargs)
        context['schedule'] = self.get_object()
        return context
