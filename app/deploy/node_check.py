from common import constants, types, utils
from deploy.node_base import Node
import os
from flask import current_app
from flask_restful import Resource


class NodeCheck(Resource, Node):
    def post(self):
        self.generate_ssh_key()
        nodes = self.get_nodes_from_request()

        data = []
        for node in nodes:
            result = self.check_node(node['nodeIP'])
            data.append({'nodeIP': node['nodeIP'], 'result': result})

        return types.DataModel().model(code=0, data=data)

    def generate_ssh_key(self):
        if not os.path.exists('/root/.ssh/id_rsa.pub'):
            utils.execute(constants.COMMAND_DELETE_SSH_KEYGEN)
            utils.execute(constants.COMMAND_CREATE_SSH_KEYGEN)

    def check_node(self, node_ip):
        cmd = constants.COMMAND_CHECK_NODE % (
            current_app.config['NODE_PASS'], node_ip)
        code, result, _ = utils.execute(cmd)
        self._logger.info('node check command: %s, result: %s', cmd, result)
        return result.rstrip() == constants.COMMAND_CHECK_NODE_SUCCESS and code == 0
