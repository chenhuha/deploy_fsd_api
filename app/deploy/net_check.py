import json
import os
import shutil
import paramiko
import openpyxl

from common import types
from deploy.node_base import Node
from flask_restful import reqparse, Resource


class NetCheck(Resource, Node):
    def post(self):
        data = {}
        nodes = self.get_nodes_from_request()

        if len(nodes) == 1:
            data = self.single_node_data(nodes)
        else:
            data = self.multiple_nodes_data(nodes)

        node_info_file = os.path.join(self.deploy_home, "deploy_node_info.xlsx") 
        if not os.path.isfile(node_info_file):
            source_file = os.path.join(self.template_path, "deployExcel.xlsx")
            shutil.copyfile(source_file, node_info_file)
        self.write_data_to_excel(node_info_file, data)

        return types.DataModel().model(code=0, data=data)
    
    # 单节点 
    def single_node_data(self, nodes):
        node_list = self.get_info_with_from(nodes)
        result = {}
        for node in node_list:
            result = {
                'sourceIp': node['management_ip'],
                'sourceHostname': node['hostname'],
                'destIp': node['management_ip'],
                'destHostname': node['hostname'],
                'speed': node['management_speed'],
                'realSpeed': '-',
                'mtu': node['management_mtu'],
                'plr': '-',
                'status': 0
            }

        api_result = [result]

        return self.combine_results(api_result, [], [])

    # 多节点
    def multiple_nodes_data(self, nodes):
        node_list = self.get_info_with_from(nodes)
        api_result = []
        ceph_cluster_result = []
        ceph_public_result = []

        def output_format(current_node, node, node_ip, port, type):
            try:
                output = self.iperf3_client(
                    current_node['management_ip'], node_ip, port)
                return self.output_format_different_node(output, node_list)
            except Exception as e:
                self._logger.error('get iperf3_client output failed, %s', e)
                return self.output_format_null_node(current_node, node, type)

        # execute iperf3 client and collect results
        for i, current_node in enumerate(node_list):
            for j, node in enumerate(node_list):
                if i == j:
                    api_result.append(
                        self.output_format_same_node(node, 'management'))
                    ceph_cluster_result.append(
                        self.output_format_same_node(node, 'storage_cluster'))
                    ceph_public_result.append(
                        self.output_format_same_node(node, 'storage_public'))
                else:
                    # prepare iperf3 server
                    for port in [5201, 5202, 5203]:
                        self.iperf3_server(node['management_ip'], port)

                    api_result.append(output_format(
                        current_node, node, node['management_ip'], 5201, 'management'))
                    ceph_cluster_result.append(output_format(
                        current_node, node, node['storage_cluster_ip'], 5202, 'storage_cluster'))
                    ceph_public_result.append(output_format(
                        current_node, node, node['storage_public_ip'], 5203, 'storage_public'))

        return self.combine_results(api_result, ceph_cluster_result, ceph_public_result)

    # 处理前端传来的数据
    def get_info_with_from(self, nodes):
        node_list = []

        for node in nodes:
            node_info = {}
            for card in node['cards']:
                if 'MANAGEMENT' in card['purpose']:
                    node_info['management_ip'] = card['ip']
                    node_info['management_speed'] = card['speed']
                    node_info['management_mtu'] = card['mtu']
    
                if 'STORAGECLUSTER' in card['purpose']:
                    node_info['storage_cluster_ip'] = card['ip']
                    node_info['storage_cluster_speed'] = card['speed']
                    node_info['storage_cluster_mtu'] = card['mtu']
   
                if 'STORAGEPUBLIC' in card['purpose']:
                    node_info['storage_public_ip'] = card['ip']
                    node_info['storage_public_speed'] = card['speed']
                    node_info['storage_public_mtu'] = card['mtu']
     
                node_info['hostname'] = node['nodeName']
            node_list.append(node_info)

        return node_list

    def iperf3_server(self, host_ip, port):
        cmd = f'iperf3 -s -J -1 -p {port}'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username=self.username,
                        password=self.password)
            ssh.exec_command(cmd)

    def iperf3_client(self, host_ip, server, port):
        cmd = f'iperf3 -c {server} -p {port} -t 3 -i 1 --get-server-output -J'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_ip, username=self.username,
                        password=self.password)
            _, stdout, _ = ssh.exec_command(cmd)
            data = stdout.read().decode()
        return data

    # 处理相同节点的数据
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
            'destIp': dest_ip,
            'destHostname': dest_hostname,
            'speed': speed,
            'realSpeed': real_speed,
            'mtu': mtu,
            'packetLossRate': packet_loss_rate,
            'status': status
        }

        return result

    # 处理 iperf 返回的数据
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
        status = self._get_status(
            speed, real_speed, plr, local_host, node_list)

        result = {
            'sourceIp': local_host,
            'sourceHostname': source_hostname,
            'destIp': remote_host,
            'destHostname': dest_hostname,
            'speed': speed,
            'realSpeed': real_speed,
            'mtu': mtu,
            'plr': plr,
            'status': status
        }

        return result
    
    def output_format_null_node(self, current_node, node, card_purpose):
        source_ip = current_node[f"{card_purpose}_ip"]
        source_hostname = current_node["hostname"]
        dest_ip = node[f"{card_purpose}_ip"]
        dest_hostname = node["hostname"]
        speed = node[f"{card_purpose}_speed"]
        real_speed = 0
        mtu = node[f"{card_purpose}_mtu"]
        packet_loss_rate = '100%'
        status = 1

        result = {
            'sourceIp': source_ip,
            'sourceHostname': source_hostname,
            'destIp': dest_ip,
            'destHostname': dest_hostname,
            'speed': speed,
            'realSpeed': real_speed,
            'mtu': mtu,
            'packetLossRate': packet_loss_rate,
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
            self._logger.info(
                'The real-time bandwidth is less than 50% of the standard')
            return 2

        return 0

    # 数据持久化
    def write_data_to_excel(self, filepath, data):
        workbook = openpyxl.load_workbook(filepath)
        worksheet = workbook.active
        start_num = 3
        
        status_map = {0: '正常', 1: '异常', 2: '警告'}
        card_name_map = {'apiResult': '管理网',
                        'cephPublicResult': '存储公网',
                        'cephClusterResult': '存储集群网'}
        for card_name, card_data in data.items():
            card_title = card_name_map.get(card_name, card_name)
            for item in card_data:
                worksheet.cell(row=start_num, column=1, value=card_title)
                worksheet.cell(row=start_num, column=2, value=item['sourceIp'])
                worksheet.cell(row=start_num, column=3, value=item['destIp'])
                worksheet.cell(row=start_num, column=4, value=status_map.get(item['status'], ''))
                worksheet.cell(row=start_num, column=5, value=str(item))
                start_num += 1
        workbook.save(filepath)


class NetCheckCommon(NetCheck):
    def post(self):
        data = {}
        nodes = self.get_nodes_from_request()
        cards = self.get_cards_from_request()
        nodes = self.uniform_format_with_nodes(nodes, cards)

        if len(nodes) == 1:
            data = self.single_node_data(nodes)
        else:
            data = self.multiple_nodes_data(nodes)

        node_info_file = os.path.join(self.deploy_home, "deploy_node_info.xlsx")
        
        if not os.path.isfile(node_info_file):
            source_file = os.path.join(self.template_path, "deployExcel.xlsx")
            shutil.copyfile(source_file, node_info_file)
        self.write_data_to_excel(node_info_file, data)
        
        return types.DataModel().model(code=0, data=data)

    def get_cards_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cards', required=True, location='json',
                            type=list, help='The cards field does not exist')

        return parser.parse_args()['cards']

    def uniform_format_with_nodes(self, nodes, cards):
        for node in nodes:
            node_cards = []
            for card in cards:
                if 'MANAGEMENT' in card['purpose']:
                    card['ip'] = node['nodeIP']
                elif 'STORAGEPUBLIC' in card['purpose'] or 'STORAGECLUSTER' in card['purpose']:
                    card['ip'] = self.get_remote_ip_address(
                        node['nodeIP'], card['name'])
                node_cards.append(card.copy())
            node['cards'] = node_cards

        return nodes

    def get_remote_ip_address(self, remote_host, interface_name):
        cmd = "ifconfig %s | grep 'inet ' | awk '{print $2}'" % interface_name
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(remote_host, username=self.username,
                        password=self.password)
            _, stdout, _ = ssh.exec_command(cmd)
            output = stdout.read().decode()

        return output.replace('\n', '')
