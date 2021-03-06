# VMware vCloud Director Python SDK
# Copyright (c) 2018 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from pyvcloud.vcd.client import E
from pyvcloud.vcd.client import E_VMEXT
from pyvcloud.vcd.client import EntityType
from pyvcloud.vcd.client import NSMAP
from pyvcloud.vcd.client import RelationType
from pyvcloud.vcd.exceptions import EntityNotFoundException
from pyvcloud.vcd.exceptions import InvalidParameterException
from pyvcloud.vcd.platform import Platform
from pyvcloud.vcd.utils import get_admin_href


class ExternalNetwork(object):
    def __init__(self, client, name=None, href=None, resource=None):
        """Constructor for External Network objects.

        :param pyvcloud.vcd.client.Client client: the client that will be used
            to make REST calls to vCD.
        :param str name: name of the entity.
        :param str href: URI of the entity.
        :param lxml.objectify.ObjectifiedElement resource: object containing
            EntityType.EXTERNAL_NETWORK XML data representing the external
            network.
        """
        self.client = client
        self.name = name
        if href is None and resource is None:
            raise InvalidParameterException(
                "External network initialization failed as arguments are "
                "either invalid or None")
        self.href = href
        self.resource = resource
        if resource is not None:
            self.name = resource.get('name')
            self.href = resource.get('href')
        self.href_admin = get_admin_href(self.href)

    def get_resource(self):
        """Fetches the XML representation of the external network from vCD.

        Will serve cached response if possible.

        :return: object containing EntityType.EXTERNAL_NETWORK XML data
        representing the external network.

        :rtype: lxml.objectify.ObjectifiedElement
        """
        if self.resource is None:
            self.reload()
        return self.resource

    def reload(self):
        """Reloads the resource representation of the external network.

        This method should be called in between two method invocations on the
        external network object, if the former call changes the representation
        of the external network in vCD.
        """
        self.resource = self.client.get_resource(self.href)
        if self.resource is not None:
            self.name = self.resource.get('name')
            self.href = self.resource.get('href')

    def add_subnet(self,
                   name,
                   gateway_ip,
                   netmask,
                   ip_ranges,
                   primary_dns_ip=None,
                   secondary_dns_ip=None,
                   dns_suffix=None):
        """Add subnet to an external network.

        :param str name: Name of external network.

        :param str gateway_ip: IP address of the gateway of the new network.

        :param str netmask: Netmask of the gateway.

        :param list ip_ranges: list of IP ranges used for static pool
            allocation in the network. For example, [192.168.1.2-192.168.1.49,
            192.168.1.100-192.168.1.149].

        :param str primary_dns_ip: IP address of primary DNS server.

        :param str secondary_dns_ip: IP address of secondary DNS Server.

        :param str dns_suffix: DNS suffix.

        :rtype: lxml.objectify.ObjectifiedElement
        """
        if self.resource is None:
            self.reload()

        platform = Platform(self.client)
        ext_net = platform.get_external_network(name)
        config = ext_net['{' + NSMAP['vcloud'] + '}Configuration']
        ip_scopes = config.IpScopes

        ip_scope = E.IpScope()
        ip_scope.append(E.IsInherited(False))
        ip_scope.append(E.Gateway(gateway_ip))
        ip_scope.append(E.Netmask(netmask))
        if primary_dns_ip is not None:
            ip_scope.append(E.Dns1(primary_dns_ip))
        if secondary_dns_ip is not None:
            ip_scope.append(E.Dns2(secondary_dns_ip))
        if dns_suffix is not None:
            ip_scope.append(E.DnsSuffix(dns_suffix))
        e_ip_ranges = E.IpRanges()
        for ip_range in ip_ranges:
            e_ip_range = E.IpRange()
            ip_range_token = ip_range.split('-')
            e_ip_range.append(E.StartAddress(ip_range_token[0]))
            e_ip_range.append(E.EndAddress(ip_range_token[1]))
            e_ip_ranges.append(e_ip_range)
        ip_scope.append(e_ip_ranges)
        ip_scopes.append(ip_scope)

        return self.client.put_linked_resource(
            ext_net,
            rel=RelationType.EDIT,
            media_type=EntityType.EXTERNAL_NETWORK.value,
            contents=ext_net)

    def enable_subnet(self, gateway_ip, is_enabled=None):
        """Enable subnet of an external network.

        :param str gateway_ip: IP address of the gateway of external network.

        :param bool is_enabled: flag to enable/disable the subnet

        :rtype: lxml.objectify.ObjectifiedElement
        """
        ext_net = self.client.get_resource(self.href)

        config = ext_net['{' + NSMAP['vcloud'] + '}Configuration']
        ip_scopes = config.IpScopes

        if is_enabled is not None:
            for ip_scope in ip_scopes.IpScope:
                if ip_scope.Gateway == gateway_ip:
                    if hasattr(ip_scope, 'IsEnabled'):
                        ip_scope['IsEnabled'] = E.IsEnabled(is_enabled)
                        return self.client. \
                            put_linked_resource(ext_net, rel=RelationType.EDIT,
                                                media_type=EntityType.
                                                EXTERNAL_NETWORK.value,
                                                contents=ext_net)
        return ext_net

    def add_ip_range(self, gateway_ip, ip_ranges):
        """Add new ip range into a subnet of an external network.

        :param str gateway_ip: IP address of the gateway of external network.

        :param list ip_ranges: list of IP ranges used for static pool
            allocation in the network. For example, [192.168.1.2-192.168.1.49,
            192.168.1.100-192.168.1.149]

        :rtype: lxml.objectify.ObjectifiedElement
        """
        ext_net = self.client.get_resource(self.href)

        config = ext_net['{' + NSMAP['vcloud'] + '}Configuration']
        ip_scopes = config.IpScopes

        for ip_scope in ip_scopes.IpScope:
            if ip_scope.Gateway == gateway_ip:
                existing_ip_ranges = ip_scope.IpRanges
                break

        for range in ip_ranges:
            range_token = range.split('-')
            e_ip_range = E.IpRange()
            e_ip_range.append(E.StartAddress(range_token[0]))
            e_ip_range.append(E.EndAddress(range_token[1]))
            existing_ip_ranges.append(e_ip_range)

        return self.client. \
            put_linked_resource(ext_net, rel=RelationType.EDIT,
                                media_type=EntityType.
                                EXTERNAL_NETWORK.value,
                                contents=ext_net)

    def modify_ip_range(self, gateway_ip, old_ip_range, new_ip_range):
        """Modify ip range of a subnet in external network.

        :param str gateway_ip: IP address of the gateway of external
             network.
        :param str old_ip_range: existing ip range present in the static pool
             allocation in the network. For example, [192.168.1.2-192.168.1.20]

        :param str new_ip_range: new ip range to replace the existing ip range
             present in the static pool allocation in the network.

        :return: object containing vmext:VMWExternalNetwork XML element that
             representing the external network.

        :rtype: lxml.objectify.ObjectifiedElement
        """
        if self.resource is None:
            self.reload()
        ext_net = self.resource
        old_ip_addrs = old_ip_range.split('-')
        new_ip_addrs = new_ip_range.split('-')
        config = ext_net['{' + NSMAP['vcloud'] + '}Configuration']
        ip_scopes = config.IpScopes
        ip_range_found = False

        for ip_scope in ip_scopes.IpScope:
            if ip_scope.Gateway == gateway_ip:
                for exist_ip_range in ip_scope.IpRanges.IpRange:
                    if exist_ip_range.StartAddress == \
                            old_ip_addrs[0] and \
                            exist_ip_range.EndAddress \
                            == old_ip_addrs[1]:
                        exist_ip_range['StartAddress'] = \
                            E.StartAddress(new_ip_addrs[0])
                        exist_ip_range['EndAddress'] = \
                            E.EndAddress(new_ip_addrs[1])
                        ip_range_found = True
                        break

        if not ip_range_found:
            raise EntityNotFoundException(
                'IP Range \'%s\' not Found' % old_ip_range)

        return self.client. \
            put_linked_resource(ext_net, rel=RelationType.EDIT,
                                media_type=EntityType.
                                EXTERNAL_NETWORK.value,
                                contents=ext_net)

    def attach_port_group(self, vim_server_name, port_group_name):
        """Attach a portgroup to an external network.

        :param str vc_name: name of vc where portgroup is present.
        :param str pg_name: name of the portgroup to be attached to
             external network.

        return: object containing vmext:VMWExternalNetwork XML element that
             representing the external network.
        :rtype: lxml.objectify.ObjectifiedElement
        """
        ext_net = self.get_resource()
        platform = Platform(self.client)

        if not vim_server_name or not port_group_name:
            raise InvalidParameterException(
                "Either vCenter Server name is none or portgroup name is none")

        vc_record = platform.get_vcenter(vim_server_name)
        vc_href = vc_record.get('href')
        pg_moref_types = \
            platform.get_port_group_moref_types(vim_server_name,
                                                port_group_name)

        if hasattr(ext_net,
                   '{' + NSMAP['vmext'] + '}VimPortGroupRef'):
            vim_port_group_refs = E_VMEXT.VimPortGroupRefs()
            vim_object_ref1 = self.__create_vimobj_ref(
                vc_href,
                pg_moref_types[0],
                pg_moref_types[1])

            # Create a new VimObjectRef using vc href, portgroup moref and type
            # from existing VimPortGroupRef. Add the VimObjectRef to
            # VimPortGroupRefs and then delete VimPortGroupRef
            # from external network.
            vim_pg_ref = ext_net['{' + NSMAP['vmext'] + '}VimPortGroupRef']
            vc2_href = vim_pg_ref.VimServerRef.get('href')
            vim_object_ref2 = self.__create_vimobj_ref(
                vc2_href,
                vim_pg_ref.MoRef.text,
                vim_pg_ref.VimObjectType.text)

            vim_port_group_refs.append(vim_object_ref1)
            vim_port_group_refs.append(vim_object_ref2)
            ext_net.remove(vim_pg_ref)
            ext_net.append(vim_port_group_refs)
        else:
            vim_port_group_refs = \
                ext_net['{' + NSMAP['vmext'] + '}VimPortGroupRefs']
            vim_object_ref1 = self.__create_vimobj_ref(
                vc_href,
                pg_moref_types[0],
                pg_moref_types[1])
            vim_port_group_refs.append(vim_object_ref1)

        return self.client. \
            put_linked_resource(ext_net, rel=RelationType.EDIT,
                                media_type=EntityType.
                                EXTERNAL_NETWORK.value,
                                contents=ext_net)

    def __create_vimobj_ref(self, vc_href, pg_moref, pg_type):
        """Creates the VimObjectRef."""
        vim_object_ref = E_VMEXT.VimObjectRef()
        vim_object_ref.append(E_VMEXT.VimServerRef(href=vc_href))
        vim_object_ref.append(E_VMEXT.MoRef(pg_moref))
        vim_object_ref.append(E_VMEXT.VimObjectType(pg_type))

        return vim_object_ref

    def detach_port_group(self, vim_server_name, port_group_name):
        """Detach a portgroup from an external network.

        :param str vim_server_name: name of vim server where
        portgroup is present.
        :param str port_group_name: name of the portgroup to be detached from
             external network.

        return: object containing vmext:VMWExternalNetwork XML element that
             representing the external network.
        :rtype: lxml.objectify.ObjectifiedElement
        """
        ext_net = self.get_resource()
        platform = Platform(self.client)

        if not vim_server_name or not port_group_name:
            raise InvalidParameterException(
                "Either vCenter Server name is none or portgroup name is none")

        vc_record = platform.get_vcenter(vim_server_name)
        vc_href = vc_record.get('href')
        if hasattr(ext_net, 'VimPortGroupRefs'):
            pg_moref_types = \
                platform.get_port_group_moref_types(vim_server_name,
                                                    port_group_name)
        else:
            raise \
                InvalidParameterException("External network"
                                          " has only one port group")

        vim_port_group_refs = ext_net.VimPortGroupRefs
        vim_obj_refs = vim_port_group_refs.VimObjectRef
        for vim_obj_ref in vim_obj_refs:
            if vim_obj_ref.VimServerRef.get('href') == vc_href \
                    and vim_obj_ref.MoRef == pg_moref_types[0] \
                    and vim_obj_ref.VimObjectType == pg_moref_types[1]:
                vim_port_group_refs.remove(vim_obj_ref)

        return self.client. \
            put_linked_resource(ext_net, rel=RelationType.EDIT,
                                media_type=EntityType.
                                EXTERNAL_NETWORK.value,
                                contents=ext_net)
