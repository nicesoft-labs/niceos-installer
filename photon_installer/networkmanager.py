#/*
# * Copyright © 2020-2023 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */

import getopt
import json
import os
import re
import subprocess
import shutil
import sys


SYSTEMD_NETWORK_DIR = "etc/systemd/network"
HOSTS_FILE = "etc/hosts"
HOSTNAME_FILE = "etc/hostname"


def write_systemd_config(fout, config):
    """Write systemd-networkd config file from a dictionary."""
    for sname, section in config.items():
        fout.write(f"[{sname}]\n")
        for option in section:
            if isinstance(section[option], (str, int)):
                fout.write(f"{option}={section[option]}\n")
            elif isinstance(section[option], list):
                for val in section[option]:
                    fout.write(f"{option}={val}\n")
        fout.write("\n")


def is_valid_hostname(hostname):
    """Validate hostname according to RFC 1123."""
    if len(hostname) > 255:
        return False
    allowed = re.compile("(?!-)[A-Z\d_-]{1,63}(?<!-)$", re.IGNORECASE)
    return allowed.match(hostname)


def netmask_to_cidr(netmask):
    """Convert netmask to CIDR notation (e.g., 255.255.255.0 -> 24)."""
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])


class NetworkManager:
    IFACE_TYPE_ETHERNET = 0
    IFACE_TYPE_VLAN = 1
    SYSTEMD_NETWORKD_PREFIX = "50-"
    SYSTEMD_NETWORK_UID = 76
    SYSTEMD_NETWORK_GID = 76
    SYSTEMD_NETWORK_MODE = 0o660

    def __init__(self, config, root_dir="/", logger=None):
        """
        Initialize NetworkManager with a network configuration.

        Args:
            config (dict): Network configuration dictionary.
            root_dir (str): Root directory for file operations (default: "/").
            logger: Logger object for logging messages.
        """
        self.root_dir = root_dir
        self.systemd_network_dir = os.path.join(self.root_dir, SYSTEMD_NETWORK_DIR)
        self.logger = logger

        if config.get('version') != '2':
            if 'type' in config or config.get('version') == '1':
                config = self._convert_legacy_config(config)

        self.config = config

    def get_interfaces(self) -> List[str]:
        """
        Retrieve a list of available network interfaces.

        Returns:
            List[str]: List of network interface names (e.g., ['eth0', 'eth1']).

        Raises:
            Exception: If the command to list interfaces fails.
        """
        try:
            # Use 'ip link show' to list interfaces
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            interfaces = []
            for line in result.stdout.splitlines():
                if ':' in line and 'link/ether' in line:
                    # Extract interface name (e.g., "2: eth0: ...")
                    iface = line.split(':')[1].strip().split()[0]
                    if iface != 'lo':  # Exclude loopback
                        interfaces.append(iface)
            if not interfaces and self.logger:
                self.logger.warning("No network interfaces found")
            return interfaces
        except subprocess.CalledProcessError as e:
            if self.logger:
                self.logger.error(f"Failed to list network interfaces: {e}")
            raise Exception(f"Failed to list network interfaces: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error listing interfaces: {e}")
            raise

    def _convert_legacy_config(self, old_config):
        """Convert legacy network configuration to version 2 format."""
        if 'type' not in old_config:
            raise Exception("property 'type' must be set for legacy network configuration, or use 'version':'2'")

        config = {'version': '2'}

        if 'hostname' in old_config:
            config['hostname'] = old_config['hostname']

        type = old_config['type']
        if type == 'dhcp':
            config['ethernets'] = {'dhcp-en': {'match': {'name': 'e*'}, 'dhcp4': True}}
        elif type == 'static':
            config['ethernets'] = {'static-en': {'match': {'name': 'eth0'}}}
            if 'ip_addr' not in old_config:
                raise Exception("need 'ip_addr' property for static network configuration")
            address = old_config['ip_addr']
            if 'netmask' in old_config:
                cidr = netmask_to_cidr(old_config['netmask'])
                address = f'{address}/{cidr}'
            if_cfg = config['ethernets']['static-en']
            if_cfg['addresses'] = [address]
            if 'gateway' in old_config:
                if_cfg['gateway'] = old_config['gateway']
            if 'nameserver' in old_config:
                if_cfg['nameservers'] = {'addresses': [old_config['nameserver']]}
        elif type == 'vlan':
            config['ethernets'] = {'dhcp-en': {'match': {'name': 'eth0'}, 'dhcp4': True}}
            if 'vlan_id' not in old_config:
                raise Exception("need 'vlan_id' property for VLAN configuration")
            vlan_id = old_config['vlan_id']
            if_id = f'dhcp-en.vlan_{vlan_id}'
            if_name = f'eth0.{vlan_id}'
            config['vlans'] = {if_id: {'match': {'name': if_name}, 'dhcp4': True, 'link': 'dhcp-en', 'id': int(vlan_id)}}
        else:
            raise Exception(f"unknown network type '{type}")

        return config

    def prepare_filesystem(self):
        """Create systemd network directory if it doesn't exist."""
        os.makedirs(os.path.join(self.root_dir, SYSTEMD_NETWORK_DIR), exist_ok=True)

    def _find_vlan_configs(self, if_id):
        """Find VLAN configurations linked to the given interface ID."""
        vif_ids = []
        if 'vlans' in self.config:
            for vif_id, vif_cfg in self.config['vlans'].items():
                if 'link' in vif_cfg and vif_cfg['link'] == if_id:
                    vif_ids.append(vif_id)
        return vif_ids

    def _get_vlan_iface_name(self, vif_id):
        """Construct VLAN interface name from physical interface and VLAN ID."""
        vif_cfg = self.config['vlans'][vif_id]
        if 'link' in vif_cfg:
            link = vif_cfg['link']
            pif_cfg = self.config['ethernets'][link]
            if 'name' not in pif_cfg['match']:
                raise Exception("physical interface configuration needs a name to set for VLAN")
            if 'id' in vif_cfg:
                name = f"{pif_cfg['match']['name']}.{vif_cfg['id']}"
            else:
                raise Exception("need 'id' property for vlan configuration")
        else:
            raise Exception("need 'link' property for vlan configuration")
        return name

    def _get_iface_filename(self, if_id, type):
        """Generate filename for network or netdev file."""
        return os.path.join(self.root_dir, SYSTEMD_NETWORK_DIR, f"{self.SYSTEMD_NETWORKD_PREFIX}{if_id}.{type}")

    def write_network_file(self, if_id, iface_config, type=IFACE_TYPE_ETHERNET):
        """Write systemd-networkd network file for an interface."""
        sysdict = {}
        name = None

        if type == self.IFACE_TYPE_VLAN:
            name = self._get_vlan_iface_name(if_id)
            sysdict['Match'] = {'Name': name}
        elif type == self.IFACE_TYPE_ETHERNET:
            if 'match' in iface_config:
                sysdict['Match'] = {}
                if 'macaddress' in iface_config['match']:
                    sysdict['Match']['MACAddress'] = iface_config['match']['macaddress']
                if 'name' in iface_config['match']:
                    name = iface_config['match']['name']
                    sysdict['Match']['Name'] = name
        else:
            raise Exception(f"unknown interface type {type}")

        sysdict['Network'] = {}
        if 'dhcp4' in iface_config or 'dhcp6' in iface_config:
            if iface_config.get('dhcp4', False):
                if iface_config.get('dhcp6', False):
                    sysdict['Network']['DHCP'] = 'yes'
                else:
                    sysdict['Network']['DHCP'] = 'ipv4'
            else:
                if iface_config.get('dhcp6', False):
                    sysdict['Network']['DHCP'] = 'ipv6'
                else:
                    sysdict['Network']['DHCP'] = 'no'

        sysdict['Network']['IPv6AcceptRA'] = 'yes' if iface_config.get('accept-ra', False) else 'no'

        if 'addresses' in iface_config:
            sysdict['Network']['Address'] = iface_config['addresses']
        if 'nameservers' in iface_config:
            sysdict['Network']['DNS'] = []
            nss = iface_config['nameservers']
            for entry in nss:
                if entry == 'addresses':
                    for addr in nss['addresses']:
                        sysdict['Network']['DNS'].append(addr)
                elif entry == 'search':
                    domains = ' '.join(nss['search'])
                    sysdict['Network']['Domains'] = domains
        if 'gateway' in iface_config:
            sysdict['Network']['Gateway'] = iface_config['gateway']
        if type == self.IFACE_TYPE_ETHERNET:
            for vif_id in self._find_vlan_configs(if_id):
                vname = self._get_vlan_iface_name(vif_id)
                sysdict['Network']['VLAN'] = vname

        with open(self._get_iface_filename(if_id, "network"), "w") as f:
            write_systemd_config(f, sysdict)

    def write_netdev_file(self, if_id, iface_config, type):
        """Write systemd-networkd netdev file for a VLAN interface."""
        sysdict = {}
        if type == self.IFACE_TYPE_VLAN:
            name = self._get_vlan_iface_name(if_id)
            sysdict['NetDev'] = {'Name': name, 'Kind': 'vlan'}
            if 'id' not in iface_config:
                raise Exception("need 'id' property for vlan configuration")
            id = iface_config['id']
            if not 1 <= id <= 4094:
                raise Exception("'id' must be in range 1..4094")
            sysdict['VLAN'] = {'Id': id}
        with open(self._get_iface_filename(if_id, "netdev"), "w") as f:
            write_systemd_config(f, sysdict)

    def write_interfaces(self):
        """Write all network configuration files."""
        for if_id, if_cfg in self.config['ethernets'].items():
            self.write_network_file(if_id, if_cfg)
        if 'vlans' in self.config:
            for if_id, if_cfg in self.config['vlans'].items():
                if if_cfg['link'] not in self.config['ethernets']:
                    raise Exception("'link' property in VLAN config must be one of the ids set in 'ethernets'")
                self.write_network_file(if_id, if_cfg, type=self.IFACE_TYPE_VLAN)
                self.write_netdev_file(if_id, if_cfg, type=self.IFACE_TYPE_VLAN)

    def set_hostname(self):
        """Set hostname in /etc/hostname and append to /etc/hosts."""
        if 'hostname' in self.config:
            hostname = self.config['hostname']
            if not is_valid_hostname(hostname):
                raise Exception(f"hostname '{hostname}' is invalid")
            hosts_file = os.path.join(self.root_dir, HOSTS_FILE)
            found = False
            if os.path.exists(hosts_file):
                with open(hosts_file, 'r') as fin:
                    for line in fin.readlines():
                        if line.startswith('#'):
                            continue
                        if line.startswith('127.0.0.1') and len(line.split()) > 1:
                            if line.split()[1] == hostname:
                                found = True
                                break
            if not found:
                with open(hosts_file, 'a') as fout:
                    fout.write('\n127.0.0.1 {}\n'.format(hostname))
            hostname_file = os.path.join(self.root_dir, HOSTNAME_FILE)
            with open(hostname_file, 'w') as fout:
                fout.write(hostname)

    def exec_cmd(self, cmd):
        """Execute a shell command and return success status."""
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, shell=True)
        return process.wait() == 0

    def restart_networkd(self):
        """Restart systemd-networkd service."""
        if self.root_dir != "/":
            return
        if not self.exec_cmd('systemctl restart systemd-networkd'):
            raise Exception('Failed to restart networkd')

    def setup_network(self, do_clean=True):
        """Set up network configuration files and hostname."""
        if do_clean and os.path.isdir(self.systemd_network_dir):
            for filename in os.listdir(self.systemd_network_dir):
                filepath = os.path.join(self.systemd_network_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        self.prepare_filesystem()
        self.write_interfaces()
        self.set_hostname()
        return True

    def set_perms(self, uid=SYSTEMD_NETWORK_UID, gid=SYSTEMD_NETWORK_GID, mode=SYSTEMD_NETWORK_MODE):
        """Set permissions and ownership for network configuration files."""
        try:
            for filename in os.listdir(self.systemd_network_dir):
                filepath = os.path.join(self.systemd_network_dir, filename)
                if os.path.isfile(filepath):
                    os.chmod(filepath, mode)
                    os.chown(filepath, uid, gid)
        except PermissionError:
            pass


def main():
    config_file = None
    dest_dir = "/"
    do_perms = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'D:f:p')
    except:
        print("invalid option")
        sys.exit(2)

    for o, a in opts:
        if o == '-D':
            dest_dir = a
        elif o == '-f':
            config_file = a
        elif o == '-p':
            do_perms = True
        else:
            assert False, "unhandled option 'o'"

    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = json.load(sys.stdin)

    nm = NetworkManager(config, dest_dir)
    nm.setup_network()
    if do_perms:
        nm.set_perms()


if __name__ == "__main__":
    main()
