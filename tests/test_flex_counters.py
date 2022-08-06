import time
import pytest

from swsscommon import swsscommon

TUNNEL_TYPE_MAP           = "COUNTERS_TUNNEL_TYPE_MAP"
ROUTE_TO_PATTERN_MAP      = "COUNTERS_ROUTE_TO_PATTERN_MAP"
NUMBER_OF_RETRIES         = 10
CPU_PORT_OID              = "0x0"
PORT                      = "Ethernet0"
PORT_MAP                  = "COUNTERS_PORT_NAME_MAP"

counter_group_meta = {
    'port_counter': {
        'key': 'PORT',
        'group_name': 'PORT_STAT_COUNTER',
        'name_map': 'COUNTERS_PORT_NAME_MAP',
        'post_test':  'post_port_counter_test',
    },
    'queue_counter': {
        'key': 'QUEUE',
        'group_name': 'QUEUE_STAT_COUNTER',
        'name_map': 'COUNTERS_QUEUE_NAME_MAP',
    },
    'rif_counter': {
        'key': 'RIF',
        'group_name': 'RIF_STAT_COUNTER',
        'name_map': 'COUNTERS_RIF_NAME_MAP',
        'pre_test': 'pre_rif_counter_test',
        'post_test':  'post_rif_counter_test',
    },
    'buffer_pool_watermark_counter': {
        'key': 'BUFFER_POOL_WATERMARK',
        'group_name': 'BUFFER_POOL_WATERMARK_STAT_COUNTER',
        'name_map': 'COUNTERS_BUFFER_POOL_NAME_MAP',
    },
    'port_buffer_drop_counter': {
        'key': 'PORT_BUFFER_DROP',
        'group_name': 'PORT_BUFFER_DROP_STAT',
        'name_map': 'COUNTERS_PORT_NAME_MAP',
    },
    'pg_watermark_counter': {
        'key': 'PG_WATERMARK',
        'group_name': 'PG_WATERMARK_STAT_COUNTER',
        'name_map': 'COUNTERS_PG_NAME_MAP',
    },
    'trap_flow_counter': {
        'key': 'FLOW_CNT_TRAP',
        'group_name': 'HOSTIF_TRAP_FLOW_COUNTER',
        'name_map': 'COUNTERS_TRAP_NAME_MAP',
        'post_test':  'post_trap_flow_counter_test',
    },
    'tunnel_counter': {
        'key': 'TUNNEL',
        'group_name': 'TUNNEL_STAT_COUNTER',
        'name_map': 'COUNTERS_TUNNEL_NAME_MAP',
        'pre_test': 'pre_vxlan_tunnel_counter_test',
        'post_test':  'post_vxlan_tunnel_counter_test',
    },
    'acl_counter': {
        'key': 'ACL',
        'group_name': 'ACL_STAT_COUNTER',
        'name_map': 'ACL_COUNTER_RULE_MAP',
        'pre_test': 'pre_acl_tunnel_counter_test',
        'post_test':  'post_acl_tunnel_counter_test',
    },
    'route_flow_counter': {
        'key': 'FLOW_CNT_ROUTE',
        'group_name': 'ROUTE_FLOW_COUNTER',
        'name_map': 'COUNTERS_ROUTE_NAME_MAP',
        'pre_test': 'pre_route_flow_counter_test',
        'post_test':  'post_route_flow_counter_test',
    }
}

@pytest.mark.usefixtures('dvs_port_manager')
class TestFlexCounters(object):

    def setup_dbs(self, dvs):
        self.config_db = dvs.get_config_db()
        self.flex_db = dvs.get_flex_db()
        self.counters_db = dvs.get_counters_db()
        self.app_db = dvs.get_app_db()

    def wait_for_table(self, table):
        for retry in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(table)
            if len(counters_keys) > 0:
                return
            else:
                time.sleep(1)

        assert False, str(table) + " not created in Counters DB"

    def wait_for_table_empty(self, table):
        for retry in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(table)
            if len(counters_keys) == 0:
                return
            else:
                time.sleep(1)

        assert False, str(table) + " is still in Counters DB"

    def wait_for_id_list(self, stat, name, oid):
        for retry in range(NUMBER_OF_RETRIES):
            id_list = self.flex_db.db_connection.hgetall("FLEX_COUNTER_TABLE:" + stat + ":" + oid).items()
            if len(id_list) > 0:
                return
            else:
                time.sleep(1)

        assert False, "No ID list for counter " + str(name)

    def wait_for_id_list_remove(self, stat, name, oid):
        for retry in range(NUMBER_OF_RETRIES):
            id_list = self.flex_db.db_connection.hgetall("FLEX_COUNTER_TABLE:" + stat + ":" + oid).items()
            if len(id_list) == 0:
                return
            else:
                time.sleep(1)

        assert False, "ID list for counter " + str(name) + " is still there"

    def wait_for_interval_set(self, group, interval):
        interval_value = None
        for retry in range(NUMBER_OF_RETRIES):
            interval_value = self.flex_db.db_connection.hget("FLEX_COUNTER_GROUP_TABLE:" + group, 'POLL_INTERVAL')
            if interval_value == interval:
                return
            else:
                time.sleep(1)

        assert False, "Polling interval is not applied to FLEX_COUNTER_GROUP_TABLE for group {}, expect={}, actual={}".format(group, interval, interval_value)

    def verify_no_flex_counters_tables(self, counter_stat):
        counters_stat_keys = self.flex_db.get_keys("FLEX_COUNTER_TABLE:" + counter_stat)
        assert len(counters_stat_keys) == 0, "FLEX_COUNTER_TABLE:" + str(counter_stat) + " tables exist before enabling the flex counter group"

    def verify_no_flex_counters_tables_after_delete(self, counter_stat):
        for retry in range(NUMBER_OF_RETRIES):
            counters_stat_keys = self.flex_db.get_keys("FLEX_COUNTER_TABLE:" + counter_stat + ":")
            if len(counters_stat_keys) == 0:
                return
            else:
                time.sleep(1)
        assert False, "FLEX_COUNTER_TABLE:" + str(counter_stat) + " tables exist after removing the entries"

    def verify_flex_counters_populated(self, map, stat):
        counters_keys = self.counters_db.db_connection.hgetall(map)
        for counter_entry in counters_keys.items():
            name = counter_entry[0]
            oid = counter_entry[1]
            self.wait_for_id_list(stat, name, oid)

    def verify_tunnel_type_vxlan(self, meta_data, type_map):
        counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        for counter_entry in counters_keys.items():
            oid = counter_entry[1]
            fvs = self.counters_db.get_entry(type_map, "")
            assert fvs != {}
            assert fvs.get(oid) == "SAI_TUNNEL_TYPE_VXLAN"

    def verify_only_phy_ports_created(self, meta_data):
        port_counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        port_counters_stat_keys = self.flex_db.get_keys("FLEX_COUNTER_TABLE:" + meta_data['group_name'])
        for port_stat in port_counters_stat_keys:
            assert port_stat in dict(port_counters_keys.items()).values(), "Non PHY port created on PORT_STAT_COUNTER group: {}".format(port_stat)

    def set_flex_counter_group_status(self, group, map, status='enable', check_name_map=True):
        group_stats_entry = {"FLEX_COUNTER_STATUS": status}
        self.config_db.create_entry("FLEX_COUNTER_TABLE", group, group_stats_entry)
        if check_name_map:
            if status == 'enable':
                self.wait_for_table(map)
            else:
                self.wait_for_table_empty(map)

    def set_flex_counter_group_interval(self, key, group, interval):
        group_stats_entry = {"POLL_INTERVAL": interval}
        self.config_db.create_entry("FLEX_COUNTER_TABLE", key, group_stats_entry)
        self.wait_for_interval_set(group, interval)

    @pytest.mark.parametrize("counter_type", counter_group_meta.keys())
    def test_flex_counters(self, dvs, counter_type):
        """
        The test will check there are no flex counters tables on FlexCounter DB when the counters are disabled.
        After enabling each counter group, the test will check the flow of creating flex counters tables on FlexCounter DB.
        For some counter types the MAPS on COUNTERS DB will be created as well after enabling the counter group, this will be also verified on this test.
        """
        self.setup_dbs(dvs)
        meta_data = counter_group_meta[counter_type]
        counter_key = meta_data['key']
        counter_stat = meta_data['group_name']
        counter_map = meta_data['name_map']
        pre_test = meta_data.get('pre_test')
        post_test = meta_data.get('post_test')
        meta_data['dvs'] = dvs

        self.verify_no_flex_counters_tables(counter_stat)

        if pre_test:
            cb = getattr(self, pre_test)
            cb(meta_data)

        self.set_flex_counter_group_status(counter_key, counter_map)
        self.verify_flex_counters_populated(counter_map, counter_stat)
        self.set_flex_counter_group_interval(counter_key, counter_stat, '2500')

        if post_test:
            cb = getattr(self, post_test)
            cb(meta_data)

    def pre_rif_counter_test(self, meta_data):
        self.config_db.db_connection.hset('INTERFACE|Ethernet0', "NULL", "NULL")
        self.config_db.db_connection.hset('INTERFACE|Ethernet0|192.168.0.1/24', "NULL", "NULL")

    def pre_vxlan_tunnel_counter_test(self, meta_data):
        self.config_db.db_connection.hset("VLAN|Vlan10", "vlanid", "10")
        self.config_db.db_connection.hset("VXLAN_TUNNEL|vtep1", "src_ip", "1.1.1.1")
        self.config_db.db_connection.hset("VXLAN_TUNNEL_MAP|vtep1|map_100_Vlan10", "vlan", "Vlan10")
        self.config_db.db_connection.hset("VXLAN_TUNNEL_MAP|vtep1|map_100_Vlan10", "vni", "100")

    def pre_acl_tunnel_counter_test(self, meta_data):
        self.config_db.create_entry('ACL_TABLE', 'DATAACL',
            {
                'STAGE': 'INGRESS',
                'PORTS': 'Ethernet0',
                'TYPE': 'L3'
            }
        )
        self.config_db.create_entry('ACL_RULE', 'DATAACL|RULE0',
            {
                'ETHER_TYPE': '2048',
                'PACKET_ACTION': 'FORWARD',
                'PRIORITY': '9999'
            }
        )

    def pre_route_flow_counter_test(self, meta_data):
        dvs = meta_data['dvs']
        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '30'
            }
        )
        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '2000::/64',
            {
                'max_match_count': '30'
            }
        )

        self.create_l3_intf("Ethernet0", "")
        self.add_ip_address("Ethernet0", "10.0.0.0/31")
        self.set_admin_status("Ethernet0", "up")
        dvs.servers[0].runcmd("ip address add 10.0.0.1/31 dev eth0")
        dvs.servers[0].runcmd("ip route add default via 10.0.0.0")
        dvs.servers[0].runcmd("ping -c 1 10.0.0.1")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 1.1.1.0/24 10.0.0.1\"")

        self.create_l3_intf("Ethernet4", "")
        self.set_admin_status("Ethernet4", "up")
        self.add_ip_address("Ethernet4", "2001::1/64")
        dvs.runcmd("sysctl -w net.ipv6.conf.all.forwarding=1")
        dvs.servers[1].runcmd("ip -6 address add 2001::2/64 dev eth0")
        dvs.servers[1].runcmd("ip -6 route add default via 2001::1")
        time.sleep(2)
        dvs.servers[1].runcmd("ping -6 -c 1 2001::1")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ipv6 route 2000::/64 2001::2\"")

    def post_rif_counter_test(self, meta_data):
        self.config_db.db_connection.hdel('INTERFACE|Ethernet0|192.168.0.1/24', "NULL")

    def post_port_counter_test(self, meta_data):
        self.verify_only_phy_ports_created(meta_data)

    def post_trap_flow_counter_test(self, meta_data):
        """Post verification for test_flex_counters for trap_flow_counter. Steps:
               1. Disable test_flex_counters
               2. Verify name map and counter ID list are cleared
               3. Clear trap ids to avoid affecting further test cases

        Args:
            meta_data (object): flex counter meta data
        """
        counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], 'disable')

        for counter_entry in counters_keys.items():
            self.wait_for_id_list_remove(meta_data['group_name'], counter_entry[0], counter_entry[1])
        self.wait_for_table_empty(meta_data['name_map'])

    def post_vxlan_tunnel_counter_test(self, meta_data):
        self.verify_tunnel_type_vxlan(meta_data, TUNNEL_TYPE_MAP)
        self.config_db.delete_entry("VLAN","Vlan10")
        self.config_db.delete_entry("VLAN_TUNNEL","vtep1")
        self.config_db.delete_entry("VLAN_TUNNEL_MAP","vtep1|map_100_Vlan10")
        self.verify_no_flex_counters_tables_after_delete(meta_data['group_name'])

    def post_acl_tunnel_counter_test(self, meta_data):
        self.config_db.delete_entry('ACL_RULE', 'DATAACL|RULE0')
        self.config_db.delete_entry('ACL_TABLE', 'DATAACL')

    def post_route_flow_counter_test(self, meta_data):
        dvs = meta_data['dvs']
        # Verify prefix to route pattern name map
        self.wait_for_table(ROUTE_TO_PATTERN_MAP)

        # Remove route pattern and verify related couters are removed
        v4_name_map_key = '1.1.1.0/24'
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], v4_name_map_key)
        assert counter_oid
        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16')
        self.wait_for_id_list_remove(meta_data['group_name'], v4_name_map_key, counter_oid)
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], v4_name_map_key)
        assert not counter_oid
        route_pattern = self.counters_db.db_connection.hget(ROUTE_TO_PATTERN_MAP, v4_name_map_key)
        assert not route_pattern

        # Disable route flow counter and verify all counters are removed
        v6_name_map_key = '2000::/64'
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], v6_name_map_key)
        assert counter_oid
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], 'disable')
        self.wait_for_id_list_remove(meta_data['group_name'], v6_name_map_key, counter_oid)
        self.wait_for_table_empty(meta_data['name_map'])
        self.wait_for_table_empty(ROUTE_TO_PATTERN_MAP)

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} 10.0.0.1\"".format(v4_name_map_key))
        self.remove_ip_address("Ethernet0", "10.0.0.0/31")
        self.remove_l3_intf("Ethernet0")
        self.set_admin_status("Ethernet0", "down")
        dvs.servers[0].runcmd("ip route del default dev eth0")
        dvs.servers[0].runcmd("ip address del 10.0.0.1/31 dev eth0")

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ipv6 route 2000::/64 2001::2\"")
        self.remove_ip_address("Ethernet4", "2001::1/64")
        self.remove_l3_intf("Ethernet4")
        self.set_admin_status("Ethernet4", "down")
        dvs.servers[1].runcmd("ip -6 route del default dev eth0")
        dvs.servers[1].runcmd("ip -6 address del 2001::2/64 dev eth0")
        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '2000::/64')

    def test_add_remove_trap(self, dvs):
        """Test steps:
               1. Enable trap_flow_counter
               2. Remove a COPP trap
               3. Verify counter is automatically unbind
               4. Add the COPP trap back
               5. Verify counter is added back

        Args:
            dvs (object): virtual switch object
        """
        self.setup_dbs(dvs)
        meta_data = counter_group_meta['trap_flow_counter']
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'])

        removed_trap = None
        changed_group = None
        trap_ids = None
        copp_groups = self.app_db.db_connection.keys('COPP_TABLE:*')
        for copp_group in copp_groups:
            trap_ids = self.app_db.db_connection.hget(copp_group, 'trap_ids')
            if trap_ids and ',' in trap_ids:
                trap_ids = [x.strip() for x in trap_ids.split(',')]
                removed_trap = trap_ids.pop()
                changed_group = copp_group.split(':')[1]
                break

        if not removed_trap:
            pytest.skip('There is not copp group with more than 1 traps, skip rest of the test')

        oid = None
        for _ in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
            if removed_trap in counters_keys:
                oid = counters_keys[removed_trap]
                break
            else:
                time.sleep(1)

        assert oid, 'trap counter is not created for {}'.format(removed_trap)
        self.wait_for_id_list(meta_data['group_name'], removed_trap, oid)

        app_copp_table = swsscommon.ProducerStateTable(self.app_db.db_connection, 'COPP_TABLE')
        app_copp_table.set(changed_group, [('trap_ids', ','.join(trap_ids))])
        self.wait_for_id_list_remove(meta_data['group_name'], removed_trap, oid)
        counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        assert removed_trap not in counters_keys

        trap_ids.append(removed_trap)
        app_copp_table.set(changed_group, [('trap_ids', ','.join(trap_ids))])

        oid = None
        for _ in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
            if removed_trap in counters_keys:
                oid = counters_keys[removed_trap]
                break
            else:
                time.sleep(1)

        assert oid, 'Add trap {}, but trap counter is not created'.format(removed_trap)
        self.wait_for_id_list(meta_data['group_name'], removed_trap, oid)
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], 'disable')

    def test_remove_trap_group(self, dvs):
        """Remove trap group and verify that all related trap counters are removed

        Args:
            dvs (object): virtual switch object
        """
        self.setup_dbs(dvs)
        meta_data = counter_group_meta['trap_flow_counter']
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'])

        removed_group = None
        trap_ids = None
        copp_groups = self.app_db.db_connection.keys('COPP_TABLE:*')
        for copp_group in copp_groups:
            trap_ids = self.app_db.db_connection.hget(copp_group, 'trap_ids')
            if trap_ids and trap_ids.strip():
                removed_group = copp_group.split(':')[1]
                break

        if not removed_group:
            pytest.skip('There is not copp group with at least 1 traps, skip rest of the test')

        trap_ids = [x.strip() for x in trap_ids.split(',')]
        for _ in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
            found = True
            for trap_id in trap_ids:
                if trap_id not in counters_keys:
                    found = False
                    break
            if found:
                break
            else:
                time.sleep(1)

        assert found, 'Not all trap id found in name map'
        for trap_id in trap_ids:
            self.wait_for_id_list(meta_data['group_name'], trap_id, counters_keys[trap_id])

        app_copp_table = swsscommon.ProducerStateTable(self.app_db.db_connection, 'COPP_TABLE')
        app_copp_table._del(removed_group)

        for trap_id in trap_ids:
            self.wait_for_id_list_remove(meta_data['group_name'], trap_id, counters_keys[trap_id])

        counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        for trap_id in trap_ids:
            assert trap_id not in counters_keys

        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], 'disable')

    def test_update_route_pattern(self, dvs):
        self.setup_dbs(dvs)
        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '30'
            }
        )
        self.create_l3_intf("Ethernet0", "")
        self.create_l3_intf("Ethernet4", "")
        self.add_ip_address("Ethernet0", "10.0.0.0/31")
        self.add_ip_address("Ethernet4", "10.0.0.2/31")
        self.set_admin_status("Ethernet0", "up")
        self.set_admin_status("Ethernet4", "up")
        # set ip address and default route
        dvs.servers[0].runcmd("ip address add 10.0.0.1/31 dev eth0")
        dvs.servers[0].runcmd("ip route add default via 10.0.0.0")
        dvs.servers[1].runcmd("ip address add 10.0.0.3/31 dev eth0")
        dvs.servers[1].runcmd("ip route add default via 10.0.0.2")
        dvs.servers[0].runcmd("ping -c 1 10.0.0.3")

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 1.1.1.0/24 10.0.0.1\"")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 2.2.2.0/24 10.0.0.3\"")

        meta_data = counter_group_meta['route_flow_counter']
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'])
        self.wait_for_table(meta_data['name_map'])
        self.wait_for_table(ROUTE_TO_PATTERN_MAP)
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.1.0/24')
        self.wait_for_id_list(meta_data['group_name'], '1.1.1.0/24', counter_oid)
        assert not self.counters_db.db_connection.hget(meta_data['name_map'], '2.2.2.0/24')
        assert not self.counters_db.db_connection.hget(ROUTE_TO_PATTERN_MAP, '2.2.2.0/24')

        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16')
        self.wait_for_id_list_remove(meta_data['group_name'], '1.1.1.0/24', counter_oid)
        self.wait_for_table_empty(meta_data['name_map'])
        self.wait_for_table_empty(ROUTE_TO_PATTERN_MAP)
        assert not self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.1.0/24')
        assert not self.counters_db.db_connection.hget(ROUTE_TO_PATTERN_MAP, '1.1.1.0/24')

        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '2.2.0.0/16',
            {
                'max_match_count': '30'
            }
        )
        self.wait_for_table(meta_data['name_map'])
        self.wait_for_table(ROUTE_TO_PATTERN_MAP)
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], '2.2.2.0/24')
        self.wait_for_id_list(meta_data['group_name'], '2.2.2.0/24', counter_oid)

        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], 'disable')
        self.wait_for_id_list_remove(meta_data['group_name'], '2.2.2.0/24', counter_oid)
        self.wait_for_table_empty(meta_data['name_map'])
        self.wait_for_table_empty(ROUTE_TO_PATTERN_MAP)

        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '2.2.0.0/16')
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} 10.0.0.1\"".format('1.1.1.0/24'))
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} 10.0.0.3\"".format('2.2.2.0/24'))

        # remove ip address
        self.remove_ip_address("Ethernet0", "10.0.0.0/31")
        self.remove_ip_address("Ethernet4", "10.0.0.2/31")

        # remove l3 interface
        self.remove_l3_intf("Ethernet0")
        self.remove_l3_intf("Ethernet4")

        self.set_admin_status("Ethernet0", "down")
        self.set_admin_status("Ethernet4", "down")

        # remove ip address and default route
        dvs.servers[0].runcmd("ip route del default dev eth0")
        dvs.servers[0].runcmd("ip address del 10.0.0.1/31 dev eth0")

        dvs.servers[1].runcmd("ip route del default dev eth0")
        dvs.servers[1].runcmd("ip address del 10.0.0.3/31 dev eth0")

    def test_add_remove_route_flow_counter(self, dvs):
        self.setup_dbs(dvs)
        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '30'
            }
        )
        meta_data = counter_group_meta['route_flow_counter']
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], check_name_map=False)

        self.create_l3_intf("Ethernet0", "")
        self.add_ip_address("Ethernet0", "10.0.0.0/31")
        self.set_admin_status("Ethernet0", "up")
        dvs.servers[0].runcmd("ip address add 10.0.0.1/31 dev eth0")
        dvs.servers[0].runcmd("ip route add default via 10.0.0.0")
        dvs.servers[0].runcmd("ping -c 1 10.0.0.1")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 1.1.1.0/24 10.0.0.1\"")

        self.wait_for_table(meta_data['name_map'])
        self.wait_for_table(ROUTE_TO_PATTERN_MAP)
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.1.0/24')
        self.wait_for_id_list(meta_data['group_name'], '1.1.1.0/24', counter_oid)

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} 10.0.0.1\"".format('1.1.1.0/24'))
        self.wait_for_id_list_remove(meta_data['group_name'], '1.1.1.0/24', counter_oid)
        self.wait_for_table_empty(meta_data['name_map'])
        self.wait_for_table_empty(ROUTE_TO_PATTERN_MAP)

        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16')
        self.set_flex_counter_group_status(meta_data['key'], meta_data['group_name'], 'disable')

        # remove ip address
        self.remove_ip_address("Ethernet0", "10.0.0.0/31")

        # remove l3 interface
        self.remove_l3_intf("Ethernet0")

        self.set_admin_status("Ethernet0", "down")

        # remove ip address and default route
        dvs.servers[0].runcmd("ip route del default dev eth0")
        dvs.servers[0].runcmd("ip address del 10.0.0.1/31 dev eth0")

    def test_router_flow_counter_max_match_count(self, dvs):
        self.setup_dbs(dvs)
        self.config_db.create_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '1'
            }
        )
        meta_data = counter_group_meta['route_flow_counter']
        self.set_flex_counter_group_status(meta_data['key'], meta_data['name_map'], check_name_map=False)
        self.create_l3_intf("Ethernet0", "")
        self.create_l3_intf("Ethernet4", "")
        self.add_ip_address("Ethernet0", "10.0.0.0/31")
        self.add_ip_address("Ethernet4", "10.0.0.2/31")
        self.set_admin_status("Ethernet0", "up")
        self.set_admin_status("Ethernet4", "up")
        # set ip address and default route
        dvs.servers[0].runcmd("ip address add 10.0.0.1/31 dev eth0")
        dvs.servers[0].runcmd("ip route add default via 10.0.0.0")
        dvs.servers[1].runcmd("ip address add 10.0.0.3/31 dev eth0")
        dvs.servers[1].runcmd("ip route add default via 10.0.0.2")
        dvs.servers[0].runcmd("ping -c 1 10.0.0.3")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 1.1.1.0/24 10.0.0.1\"")
        dvs.runcmd("vtysh -c \"configure terminal\" -c \"ip route 1.1.2.0/24 10.0.0.3\"")

        self.wait_for_table(meta_data['name_map'])
        self.wait_for_table(ROUTE_TO_PATTERN_MAP)
        counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.1.0/24')
        self.wait_for_id_list(meta_data['group_name'], '1.1.1.0/24', counter_oid)
        assert not self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.2.0/24')
        self.config_db.update_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '2'
            }
        )
        for _ in range(NUMBER_OF_RETRIES):
            counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], '1.1.2.0/24')
            if not counter_oid:
                time.sleep(1)
            else:
                break
        assert counter_oid
        self.wait_for_id_list(meta_data['group_name'], '1.1.2.0/24', counter_oid)

        self.config_db.update_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16',
            {
                'max_match_count': '1'
            }
        )

        for _ in range(NUMBER_OF_RETRIES):
            counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
            if len(counters_keys) == 1:
                break
            else:
                time.sleep(1)

        assert len(counters_keys) == 1

        to_remove = '1.1.2.0/24' if '1.1.2.0/24' in counters_keys else '1.1.1.0/24'
        to_remove_nexthop = '10.0.0.3' if '1.1.2.0/24' in counters_keys else '10.0.0.1'
        to_bound = '1.1.2.0/24' if '1.1.1.0/24' == to_remove else '1.1.1.0/24'
        to_bound_nexthop = '10.0.0.1' if '1.1.2.0/24' in counters_keys else '10.0.0.3'

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} {}\"".format(to_remove, to_remove_nexthop))
        for _ in range(NUMBER_OF_RETRIES):
            counter_oid = self.counters_db.db_connection.hget(meta_data['name_map'], to_bound)
            if not counter_oid:
                time.sleep(1)
            else:
                break
        assert counter_oid
        self.wait_for_id_list(meta_data['group_name'], to_bound, counter_oid)
        counters_keys = self.counters_db.db_connection.hgetall(meta_data['name_map'])
        assert to_remove not in counters_keys
        assert to_bound in counters_keys
        counters_keys = self.counters_db.db_connection.hgetall(ROUTE_TO_PATTERN_MAP)
        assert to_remove not in counters_keys
        assert to_bound in counters_keys

        dvs.runcmd("vtysh -c \"configure terminal\" -c \"no ip route {} {}\"".format(to_bound, to_bound_nexthop))

        # remove ip address
        self.remove_ip_address("Ethernet0", "10.0.0.0/31")
        self.remove_ip_address("Ethernet4", "10.0.0.2/31")

        # remove l3 interface
        self.remove_l3_intf("Ethernet0")
        self.remove_l3_intf("Ethernet4")

        self.set_admin_status("Ethernet0", "down")
        self.set_admin_status("Ethernet4", "down")

        # remove ip address and default route
        dvs.servers[0].runcmd("ip route del default dev eth0")
        dvs.servers[0].runcmd("ip address del 10.0.0.1/31 dev eth0")

        dvs.servers[1].runcmd("ip route del default dev eth0")
        dvs.servers[1].runcmd("ip address del 10.0.0.3/31 dev eth0")
        self.config_db.delete_entry('FLOW_COUNTER_ROUTE_PATTERN', '1.1.0.0/16')

    def create_l3_intf(self, interface, vrf_name):
        if len(vrf_name) == 0:
            self.config_db.create_entry("INTERFACE", interface, {"NULL": "NULL"})
        else:
            self.config_db.create_entry("INTERFACE", interface, {"vrf_name": vrf_name})

    def remove_l3_intf(self, interface):
        self.config_db.delete_entry("INTERFACE", interface)

    def add_ip_address(self, interface, ip):
        self.config_db.create_entry("INTERFACE", interface + "|" + ip, {"NULL": "NULL"})

    def remove_ip_address(self, interface, ip):
        self.config_db.delete_entry("INTERFACE", interface + "|" + ip)

    def set_admin_status(self, interface, status):
        self.config_db.update_entry("PORT", interface, {"admin_status": status})
            
    def test_add_remove_ports(self, dvs):
        self.setup_dbs(dvs)
        
        # set flex counter
        counter_key = counter_group_meta['queue_counter']['key']
        counter_stat = counter_group_meta['queue_counter']['group_name']
        counter_map = counter_group_meta['queue_counter']['name_map']
        self.set_flex_counter_group_status(counter_key, counter_map)

        # receive port info
        fvs = self.config_db.get_entry("PORT", PORT)
        assert len(fvs) > 0
        
        # save all the oids of the pg drop counters            
        oid_list = []
        counters_queue_map = self.counters_db.get_entry("COUNTERS_QUEUE_NAME_MAP", "")
        for key, oid in counters_queue_map.items():
            if PORT in key:
                oid_list.append(oid)
                fields = self.flex_db.get_entry("FLEX_COUNTER_TABLE", counter_stat + ":%s" % oid)
                assert len(fields) == 1
        oid_list_len = len(oid_list)

        # get port oid
        port_oid = self.counters_db.get_entry(PORT_MAP, "")[PORT]

        # remove port and verify that it was removed properly
        self.dvs_port.remove_port(PORT)
        dvs.get_asic_db().wait_for_deleted_entry("ASIC_STATE:SAI_OBJECT_TYPE_PORT", port_oid)
        
        # verify counters were removed from flex counter table
        for oid in oid_list:
            fields = self.flex_db.get_entry("FLEX_COUNTER_TABLE", counter_stat + ":%s" % oid)
            assert len(fields) == 0
        
        # verify that port counter maps were removed from counters db
        counters_queue_map = self.counters_db.get_entry("COUNTERS_QUEUE_NAME_MAP", "")
        for key in counters_queue_map.keys():
            if PORT in key:
                assert False
        
        # add port and wait until the port is added on asic db
        num_of_keys_without_port = len(dvs.get_asic_db().get_keys("ASIC_STATE:SAI_OBJECT_TYPE_PORT"))
        
        self.config_db.create_entry("PORT", PORT, fvs)
        
        dvs.get_asic_db().wait_for_n_keys("ASIC_STATE:SAI_OBJECT_TYPE_PORT", num_of_keys_without_port + 1)
        dvs.get_counters_db().wait_for_fields("COUNTERS_QUEUE_NAME_MAP", "", ["%s:0"%(PORT)])
        
        # verify queue counters were added
        oid_list = []
        counters_queue_map = self.counters_db.get_entry("COUNTERS_QUEUE_NAME_MAP", "")

        for key, oid in counters_queue_map.items():
            if PORT in key:
                oid_list.append(oid)
                fields = self.flex_db.get_entry("FLEX_COUNTER_TABLE", counter_stat + ":%s" % oid)
                assert len(fields) == 1
        # the number of the oids needs to be the same as the original number of oids (before removing a port and adding)
        assert oid_list_len == len(oid_list)
