import ast
import logging

from flask import current_app
from flask_restful import reqparse, Resource
from common import constants, types, utils


class Deploy(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

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
        cmd = constants.COMMAND_CHECK_NODE % (current_app.config['NODE_PASS'], node_ip)
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
        hdds = [storage for storage in result_dict['storages'] if storage['ishdd'] == '1']
        ssds = [storage for storage in result_dict['storages'] if storage['ishdd'] != '1']
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
        nodes = self.get_nodes_from_request()
        
        data = []
        for node in nodes:
            pass
            
        return types.DataModel().model(code=0, data=data)
