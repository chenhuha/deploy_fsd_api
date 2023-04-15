import ast

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
