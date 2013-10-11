Veta
====

Veta is a backup manager for OpenStack, supporting fine-grained backup schedules and retention policies.

Veta supports both regular nova snapshots and Gridcentric VMS live-images as snapshot backends.

Installation
------------

Veta must be installed on API nodes, Horizon nodes (if the Horizon plugin is desired) and on a controller node designated to run the Veta manager.

To install Veta, clone the repository and run:

    sudo python setup.py install

Setting up API extensions
-------------------------

You should add the Veta extension to your nova.conf in order to expose the API. You can do so by appending the following lines to nova.conf:

    osapi_compute_extension=nova.api.openstack.compute.contrib.standard_extensions
    osapi_compute_extension=veta.extension.Veta_extension

Next, you should restart the API server.

    sudo restart nova-api

Setting up the manager
----------------------

Veta comes with an upstart script for automatically starting on upstart-based
systems. To start veta manually, use:

    start veta

Setting up the dashboard
------------------------

Note that [the veta novaclient plugin](https://github.com/gridcentric/vetaclient) must be installed on the Horizon node(s) in order for the Veta Horizon plugin to work.

To enable the Veta Horizon plugin, modify
`/etc/openstack-dashboard/local_settings.py` (on Ubuntu Server 12.04) or `/etc/openstack-dashboard/local_settings` (on RHEL 6.4 / CentOS 6.4) and add the following lines:

    import sys
    mod = sys.modules['openstack_dashboard.settings']
    mod.INSTALLED_APPS += ('veta.horizon',)

Then, restart the web server with `service apache2 restart` and navigate to
Horizon. There will be a new panel labeled "Instance Backups".

Setting the Snapshot Driver
---------------------------

To set the backup snapshot driver, you must add the option `veta_snapshot_driver` to a configuration file that is read by **both** `nova-api` and `veta-manager`, for example the `/etc/nova/nova.conf` file.

The following drivers are included with Veta:

* `novadriver.NovaSnapshotDriver` - uses Nova "snapshots" (i.e. the output of `nova image-create` for instance backups.
* `cobaltdriver.CobaltSnapshotDriver` - uses [Cobalt live images](https://github.com/gridcentric/cobalt) for instance backups.

For example, to use the Cobalt driver, append the following to `/etc/nova/nova.conf`:

    veta_snapshot_driver=cobaltdriver.CobaltSnapshotDriver

