import json
import threading

from common import types, utils
from deploy.node_base import Node
from flask import current_app
from flask_restful import Resource


class NodeLoad(Resource, Node):
    def __init__(self) -> None:
        super().__init__()
        self.nodes = self.get_nodes_from_request()
        self.deploy_home = current_app.config['DEPLOY_HOME']

    def post(self):
        data = self.get_device_info()

        return types.DataModel().model(code=0, data=data)
    
    def get_device_info(self):
        threads = []
        data = []
        done_event = threading.Event()

        for node in self.nodes:
            thread = threading.Thread(target=self.execute_device_script, args=(node, data, done_event))
            thread.start()
            threads.append(thread)

        done_event.wait()  # 等待所有线程完成

        return data

    def execute_device_script(self, node, data, done_event):
        cmd = f"sh {self.deploy_home}/device.sh {node['nodeIP']}"
        try:
            _, result, _ = utils.execute(cmd)
        except Exception as e:
            self._logger.error(f"Failed to execute device script: {e}")
            return

        self._logger.info('node load command: %s, result: %s', cmd, result)
        node_data = self.format_device_data(result)
        node_data['nodeType'] = node['nodeType']
        node_data['nodeIP'] = node['nodeIP']

        with threading.Lock():
            data.append(node_data)

        if len(data) == len(self.nodes):
            done_event.set()  # 信号所有线程已完成

    def format_device_data(self, result):
        result_dict = {}
        try:
            result_dict = json.loads(result)
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse JSON: {e}")
            return {}

        # Process network data
        for network in result_dict['networks']:
            network['bond'] = network.pop('isbond') != 'ether'
            network['purpose'] = []
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
