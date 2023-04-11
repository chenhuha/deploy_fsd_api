import ast
import json
import logging
import paramiko


from flask import current_app
from flask_restful import reqparse, Resource
from common import constants, types, utils


class Deploy(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.username = current_app.config['NODE_USER']
        self.password = current_app.config['NODE_PASS']

    def get_nodes_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nodes', required=True, location='json',
                            type=list, help='The nodes field does not exist')
        return parser.parse_args()['nodes']


class NodeCheck(Resource, Deploy):
    def post(self):
        self._generate_ssh_key()
        nodes = self.get_nodes_from_request()

        data = []
        for node in nodes:
            result = self._check_node(node['nodeIP'])
            data.append({'nodeIP': node['nodeIP'], 'result': result})

        return types.DataModel().model(code=0, data=data)

    def _generate_ssh_key(self):
        utils.execute(constants.COMMAND_DELETE_SSH_KEYGEN)
        utils.execute(constants.COMMAND_CREATE_SSH_KEYGEN)

    def _check_node(self, node_ip):
        cmd = constants.COMMAND_CHECK_NODE % (
            current_app.config['NODE_PASS'], node_ip)
        code, result, _ = utils.execute(cmd)
        self._logger.info('node check command: %s, result: %s', cmd, result)
        return result.rstrip() == constants.COMMAND_CHECK_NODE_SUCCESS and code == 0


class NodeSecret(Resource, Deploy):
    def post(self):
        nodes = self.get_nodes_from_request()
        data = [{'nodeIP': node['nodeIP'], 'result': True}
                for node in nodes if self.node_secret(node)]
        return {'code': 0, 'data': data}

    def node_secret(self, node):
        cmd = constants.COMMAND_SSH_COPY_ID % (
            current_app.config['NODE_PASS'], node['nodeIP'])
        code, result, err = utils.execute(cmd)
        self._logger.info('node secret command: %s, result: %s', cmd, result)
        if constants.COMMAND_SSH_COPY_ID_SUCCESS in result and code == 0:
            return True
        if constants.COMMAND_SSH_COPY_ID_EXIST in err and code == 0:
            return True
        return False


class NodeLoad(Resource, Deploy):
    def post(self):
        nodes = self.get_nodes_from_request()
        data = []
        for node in nodes:
            node_data = self.execute_device_script(node['nodeIP'])
            node_data['nodeType'] = node['nodeType']
            data.append(node_data)

        return types.DataModel().model(code=0, data=data)

    def execute_device_script(self, node_ip):
        cmd = f"sh {current_app.config['DEPLOY_HOME']}device.sh {node_ip}"
        _, result, _ = utils.execute(cmd)
        self._logger.info('node load command: %s, result: %s', cmd, result)
        result_dict = self.format_device_data(result)
        return result_dict

    def format_device_data(self, result):
        result_dict = ast.literal_eval(result)

        # Process network data
        for network in result_dict['networks']:
            network['bond'] = network.pop('isbond') != 'ether'
        result_dict['cards'] = result_dict.pop('networks')

        # Process storage data
        hdds = [storage for storage in result_dict['storages']
                if storage['ishdd'] == '1']
        ssds = [storage for storage in result_dict['storages']
                if storage['ishdd'] != '1']
        for storage in hdds + ssds:
            storage['purpose'] = 'SYSTEM' if storage['issystem'] == '1' else None
            storage.pop('ishdd')
            storage.pop('issystem')

        result_dict['hdds'] = hdds
        result_dict['ssds'] = ssds
        result_dict.pop('storages')

        return result_dict


class NetCheck(Resource, Deploy):
    def post(self):
        data = {}
        nodes = self.get_nodes_from_request()

        if len(nodes) == 1:
            data = self.single_node_data(nodes)
        else:
            data = self.multiple_nodes_data(nodes)

        return types.DataModel().model(code=0, data=data)

    def single_node_data(self, nodes, cards=[]):
        node_list, _ = self.get_info_with_from(nodes, cards)
        result = {}
        for node in node_list:
            result = {
                'sourceIp': node['management_ip'],
                'sourceHostname': node['hostname'],
                'destIP': node['management_ip'],
                'destHostname': node['hostname'],
                'speed': node['management_speed'],
                'realSpeed': '-',
                'mtu': node['management_mtu'],
                'plr': '-',
                'status': 0
            }
        
        api_result = [result]

        return self.combine_results(api_result, [], [])


    def multiple_nodes_data(self, nodes, cards=[]):
        node_list, ip_list = self.get_info_with_from(nodes, cards)
        all_node_output = []

        for i, current_node in enumerate(node_list):
            node_output = []
            for j, node in enumerate(node_list):
                if i == j:
                    node_output += [self.output_format_same_node(node, conn_type) for conn_type in [
                        'management', 'storage_cluster', 'storage_public']]
                    continue

                self.iperf3_server(node['management_ip'], 5201)
                self.iperf3_server(node['management_ip'], 5202)
                self.iperf3_server(node['management_ip'], 5203)

                result = self.iperf3_client(
                    current_node['management_ip'], node['management_ip'], 5201)
                node_output.append(self.output_format_different_node(result, node_list))

                result = self.iperf3_client(
                    current_node['management_ip'], node['storage_cluster_ip'], 5202)
                node_output.append(self.output_format_different_node(result, node_list))

                result = self.iperf3_client(
                    current_node['management_ip'], node['storage_public_ip'], 5203)
                node_output.append(self.output_format_different_node(result, node_list))

            all_node_output.append(node_output)

        api_result = [result for nodes in all_node_output
                    for result in nodes if result['sourceIp'] in ip_list['management_ip_list']]
        ceph_cluster_result = [result for nodes in all_node_output
                            for result in nodes if result['sourceIp'] in ip_list['storage_cluster_ip_list']]
        ceph_public_result = [result for nodes in all_node_output
                            for result in nodes if result['sourceIp'] in ip_list['storage_public_ip_list']]

        return self.combine_results(api_result, ceph_cluster_result, ceph_public_result)

    def get_info_with_from(self, nodes):
        node_list = []
        management_ip_list = []
        storage_cluster_ip_list = []
        storage_public_ip_list = []

        for node in nodes:
            node_info = {}
            for card in node['cards']:
                if 'MANAGEMENT' in card['purpose']:
                    node_info['management_ip'] = card['ip']
                    node_info['management_speed'] = card['speed']
                    node_info['management_mtu'] = card['mtu']
                    management_ip_list.append(card['ip'])
                if 'STORAGECLUSTER' in card['purpose']:
                    node_info['storage_cluster_ip'] = card['ip']
                    node_info['storage_cluster_speed'] = card['speed']
                    node_info['storage_cluster_mtu'] = card['mtu']
                    storage_cluster_ip_list.append(card['ip'])
                if 'STORAGEPUBLIC' in card['purpose']:
                    node_info['storage_public_ip'] = card['ip']
                    node_info['storage_public_speed'] = card['speed']
                    node_info['storage_public_mtu'] = card['mtu']
                    storage_public_ip_list.append(card['ip'])
                node_info['hostname'] = node['nodeName']

            node_list.append(node_info)

        ip_list = {
            'management_ip_list':  management_ip_list,
            'storage_cluster_ip_list': storage_cluster_ip_list,
            'storage_public_ip_list': storage_public_ip_list
        }

        return node_list, ip_list

    def iperf3_server(self, host_ip, port):
        cmd = f'iperf3 -s -J -1 -p {port}'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username=self.username,
                        password=self.password)
            ssh.exec_command(cmd)

    def iperf3_client(self, host_ip,   server, port):
        cmd = f'iperf3 -c {server} -p {port} -t 3 -i 1 --get-server-output -J'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username=self.username,
                        password=self.password)
            _, stdout, _ = ssh.exec_command(cmd)
            data = stdout.read().decode()
        return data 

    def output_format_same_node(self, node, card_purpose):
        source_ip = node[f"{card_purpose}_ip"]
        source_hostname = node["hostname"]
        dest_ip = source_ip
        dest_hostname = source_hostname
        speed = node[f"{card_purpose}_speed"]
        real_speed = int(speed) / 8
        mtu = node[f"{card_purpose}_mtu"]
        packet_loss_rate = '0%'
        status = self._get_status(speed, real_speed, packet_loss_rate)
        
        result = {
            'sourceIp': source_ip,
            'sourceHostname': source_hostname,
            'destIP': dest_ip,
            'destHostname': dest_hostname,
            'speed': speed,
            'realSpeed': real_speed,
            'mtu': mtu,
            'packetLossRate': packet_loss_rate,
            'status': status
        }
       
        return result

    def output_format_different_node(self, result, node_list):
        json_data = json.loads(result)
  
        local_host = json_data['start']['connected'][0]['local_host']
        remote_host = json_data['start']['connected'][0]['remote_host']
        bits_per_second = json_data['end']['sum_received']['bits_per_second']

        source_hostname = self._get_hostname(local_host, node_list)
        dest_hostname = self._get_hostname(remote_host, node_list)
        speed = self._get_speed(local_host, node_list)
        real_speed = self._get_realSpeed(bits_per_second)
        mtu = self._get_mtu(local_host, node_list)
        plr = self._get_packet_loss_rate(local_host, remote_host)
        status = self._get_status(speed, real_speed, plr, local_host, node_list)

        result = {
            'sourceIp': local_host,
            'sourceHostname': source_hostname,
            'destIP': remote_host,
            'destHostname': dest_hostname,
            'speed': speed,
            'realSpeed': real_speed,
            'mtu': mtu,
            'plr': plr,
            'status': status
        }

        return result

    def combine_results(self, api_result, ceph_cluster_result, ceph_public_result):   
        return {
            'apiResult': api_result,
            'cephClusterResult': ceph_cluster_result,
            'cephPublicResult': ceph_public_result
        }

    def _get_packet_loss_rate(self, local_host, remote_host):
        cmd = f'ping -c 20 -i 0.1 -W 1 -q {remote_host}'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(local_host, username=self.username,
                        password=self.password)
            _, stdout, _ = ssh.exec_command(cmd)
            output = stdout.read().decode()
            packet_loss = output.split(',')[-2].strip().split()[0]

        return packet_loss

    def _get_hostname(self, node_ip, node_list):
        for node in node_list:
            for key in ['management_ip', 'storage_cluster_ip', 'storage_public_ip']:
                if node[key] == node_ip:
                    return node['hostname']
        return None

    def _get_realSpeed(self, bits_per_second):
        return round(bits_per_second / 1000000 / 8, 2)

    def _get_speed(self, node_ip, node_list):
        for node in node_list:
            for key in ['management_ip', 'storage_cluster_ip', 'storage_public_ip']:
                if node[key] == node_ip:
                    return node[key.replace('ip', 'speed')]
        return None

    def _get_mtu(self, node_ip, node_list):
        for node in node_list:
            for key in ['management_ip', 'storage_cluster_ip', 'storage_public_ip']:
                if node[key] == node_ip:
                    return node[key.replace('ip', 'mtu')]
        return None

    def _get_status(self, speed, real_speed, plr, node_ip='', node_list=[]):
        if plr != '0%':
            self._logger.info('plr not is 0%')
            return 1
        
        for node in node_list:
            if node['management_ip'] == node_ip:
                if int(node['management_speed']) < 1000:
                    self._logger.info(
                        'The speed of the management network card is less than 1000')
                    return 2
            if node['storage_cluster_ip'] == node_ip:
                if int(node['storage_cluster_speed']) < 10000:
                    self._logger.info(
                        'The speed of the storage cluster network card is less than 10000')
                    return 2
            if node['storage_public_ip'] == node_ip:
                if int(node['storage_public_speed']) < 10000:
                    self._logger.info(
                        'The speed of the storage public network card is less than 10000')
                    return 2
       
        if int(real_speed) < int(speed) / 8 * 0.5:
            self._logger.info('The real-time bandwidth is less than 50% of the standard')
            return 2

        return 0     


class NetCheckCommon(NetCheck):
    def post(self):
        data = {}
        nodes = self.get_nodes_from_request()
        cards = self.get_cards_from_request()

        if len(nodes) == 1:
            data = self.single_node_data(nodes, cards)
        else:
            data = self.multiple_nodes_data(nodes, cards)

        return types.DataModel().model(code=0, data=data)
    
    def get_cards_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cards', required=True, location='json',
                            type=list, help='The cards field does not exist')
        
        return parser.parse_args()['cards']
    
    def get_info_with_from(self, nodes, cards):
        node_list = []
        management_ip_list = []
        storage_cluster_ip_list = []
        storage_public_ip_list = []

        for node in nodes:
            node_info = {}
            node_info['management_ip'] = node['nodeIP']
            node_info['hostname'] = node['nodeName']

            for card in cards:
                if 'MANAGEMENT' in card['purpose']:
                    node_info['management_speed'] = card['speed']
                    node_info['management_mtu'] = card['mtu']
                    management_ip_list.append(node_info['management_ip'])
                if 'STORAGEPUBLIC' in card['purpose']:
                    node_info['storage_public_ip'] = self.get_remote_ip_address(
                        node_info['management_ip'], card['name'])
                    node_info['storage_public_speed'] = card['speed']
                    node_info['storage_public_mtu'] = card['mtu']
                    storage_public_ip_list.append(node_info['storage_public_ip'])
                if 'STORAGECLUSTER' in card['purpose']:
                    node_info['storage_cluster_ip'] = self.get_remote_ip_address(
                        node_info['management_ip'], card['name'])
                    node_info['storage_cluster_speed'] = card['speed']
                    node_info['storage_cluster_mtu'] = card['mtu']
                    storage_cluster_ip_list.append(node_info['storage_cluster_ip'])

            node_list.append(node_info)

        ip_list = {
            'management_ip_list':  management_ip_list,
            'storage_cluster_ip_list': storage_cluster_ip_list,
            'storage_public_ip_list': storage_public_ip_list
        }

        return node_list,ip_list
    
    def get_remote_ip_address(self, remote_host, interface_name):
        cmd = "ifconfig %s | grep 'inet ' | awk '{print $2}'" % interface_name
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(remote_host, username=self.username,
                        password=self.password)
            _, stdout, _ = ssh.exec_command(cmd)
            output = stdout.read().decode()
            
        return output.replace('\n', '')
