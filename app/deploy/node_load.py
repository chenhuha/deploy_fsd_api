import json

from common import types, utils
from deploy.node_base import Node
from flask import current_app
from flask_restful import Resource


class NodeLoad(Resource, Node):
    def post(self):
        nodes = self.get_nodes_from_request()
        data = []
        for node in nodes:
            node_data = self.execute_device_script(node['nodeIP'])
            node_data['nodeType'] = node['nodeType']
            node_data['nodeIP'] = node['nodeIP']
            data.append(node_data)

        return types.DataModel().model(code=0, data=data)

    def execute_device_script(self, node_ip):
        cmd = f"sh {current_app.config['DEPLOY_HOME']}device.sh {node_ip}"
        try:
            _, result, _ = utils.execute(cmd)
        except Exception as e:
            self._logger.error(f"Failed to execute device script: {e}")
            return {}

        self._logger.info('node load command: %s, result: %s', cmd, result)
        return self.format_device_data(result)

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
