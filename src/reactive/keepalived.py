import os
import re
from subprocess import check_output

from charms.reactive import set_flag, when, when_not, hook
from charms.reactive.flags import clear_flag


from charmhelpers.core.templating import render
from charmhelpers.fetch import apt_update, apt_install
from charmhelpers.core.hookenv import config, is_leader
from charmhelpers.core.host import service_restart
from charmhelpers.core.host import service_pause, service_resume

from charms.layer import status


SYSCTL_FILE = os.path.join(os.sep, 'etc', 'sysctl.d', '50-keepalived.conf')
KEEPALIVED_CONFIG_FILE = os.path.join(os.sep, 'etc', 'keepalived',
                                      'keepalived.conf')


@when_not('keepalived.package.installed')
def install_keepalived_package():
    ''' Install keepalived package '''
    status.maintenance('Installing keepalived')

    apt_update(fatal=True)
    apt_install('keepalived', fatal=True)

    set_flag('keepalived.package.installed')


def default_route_interface():
    ''' Returns the network interface of the system's default route '''
    default_interface = None
    cmd = ['route']
    output = check_output(cmd).decode('utf8')
    for line in output.split('\n'):
        if 'default' in line:
            default_interface = line.split(' ')[-1]
            return default_interface


@when('keepalived.package.installed')
@when_not('keepalived.started')
@when_not('upgrade.series.in-progress')
def configure_keepalived_service():
    ''' Set up the keepalived service '''

    virtual_ip = config().get('virtual_ip')
    if virtual_ip == "":
        status.blocked('Please configure virtual ips')
        return

    network_interface = config().get('network_interface')
    if network_interface == "":
        network_interface = default_route_interface()

    context = {'is_leader': is_leader(),
               'virtual_ip': virtual_ip,
               'network_interface': network_interface,
               'router_id': config().get('router_id'),
               'service_port': config().get('port'),
               'healthcheck_interval': config().get('healthcheck_interval'),
               }
    render(source='keepalived.conf',
           target=KEEPALIVED_CONFIG_FILE,
           context=context,
           perms=0o644)
    service_restart('keepalived')

    render(source='50-keepalived.conf',
           target=SYSCTL_FILE,
           context={'sysctl': {'net.ipv4.ip_nonlocal_bind': 1}},
           perms=0o644)
    service_restart('procps')

    status.active('VIP ready')
    set_flag('keepalived.started')


@when('config.changed')
def reconfigure():
    clear_flag('keepalived.started')


@when('website.available', 'keepalived.started')
def website_available(website):
    ipaddr = re.split('/', config()['virtual_ip'])[0]
    vip_hostname = config()['vip_hostname']
    hostname = vip_hostname if vip_hostname else ipaddr
    # a port to export over a relation
    # TODO: this could be more tightly coupled with the actual
    # service via a relation
    port = config()['port']
    website.configure(port=port, private_address=ipaddr, hostname=hostname)


@when('loadbalancer.available', 'keepalived.started')
def loadbalancer_available(loadbalancer):
    ''' Send the virtual IP  '''
    ipaddr = re.split('/', config()['virtual_ip'])[0]
    port = config()['port']
    loadbalancer.set_address_port(ipaddr, port)


@hook('upgrade-charm')
def upgrade_charm():
    clear_flag('keepalived.started')


@hook('pre-series-upgrade')
def pre_series_upgrade():
    service_pause('keepalived')
    service_pause('procps')
    status.blocked('Series upgrade in progress')


@hook('post-series-upgrade')
def post_series_upgrade():
    service_resume('keepalived')
    service_resume('procps')
    clear_flag('keepalived.started')
