from common import constants, types, utils
from deploy.node_base import Node
from flask import current_app
from flask_restful import Resource


class NodeSecret(Resource, Node):
    def post(self):
        nodes = self.get_nodes_from_request()
        datas = []
        for node in nodes:
            result = self.node_secret(node)
            data = {'nodeIP': node['nodeIP'], 'result': result}
            datas.append(data)   
       
        return types.DataModel().model(code=0, data=datas)

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
