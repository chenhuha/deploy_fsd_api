
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource

from common import constants, types, utils

import ast
import logging
import os

app = Flask(__name__)
api = Api(app)
app.config.from_object('config')

# Configuration logger
logfile_dir = app.config['LOG_PATH']

if not os.path.isdir(logfile_dir):
    os.mkdir(logfile_dir)

log_format = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
logging.basicConfig(filename='/var/log/deploy/deploy_fsd.log',
                    level=logging.DEBUG, format=log_format)


class Version(Resource):
    def get(self):
        return {'version': 'v1.0.0'}


class NodeCheck(Resource):
    def post(self):
        # 删除旧的免密证书，生成新的免密证书
        utils.execute(constants.COMMAND_DELETE_SSH_KEYGEN)
        utils.execute(constants.COMMAND_CREATE_SSH_KEYGEN)

        parser = reqparse.RequestParser()
        parser.add_argument('nodes', location='json', type=list)
        nodes = parser.parse_args()['nodes']

        data = []
        for node in nodes:
            cmd = constants.COMMAND_CHECK_NODE % (
                app.config['NODE_PASS'], node['nodeIP'])
            code, result, _ = utils.execute(cmd)
            logging.info('node check:command: %s, result: %s', cmd, result)
            data.append({'nodeIP': node['nodeIP'], 'result': result.rstrip() == constants.COMMAND_CHECK_NODE_SUCCESS and code == 0})

        return types.DataModel().model(code=0, data=data)


class NodeSecret(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nodes', location='json', type=list)
        nodes = parser.parse_args()['nodes']

        data = [{'nodeIP': node['nodeIP'], 'result': True} for node in nodes if self.node_secret(node)]
        return {'code': 0, 'data': data}

    def node_secret(self, node):
        cmd = constants.COMMAND_SSH_COPY_ID % (app.config['NODE_PASS'], node['nodeIP'])
        code, result, err = utils.execute(cmd)
        logging.info('node secret:command: %s, result: %s', cmd, result)
        if constants.COMMAND_SSH_COPY_ID_SUCCESS in result and code == 0:
            return True
        if constants.COMMAND_SSH_COPY_ID_EXIST in err and code == 0:
            return True
        return False


class NodeLoad(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nodes', location='json', type=list)
        nodes = parser.parse_args()['nodes']
        data = [self.execute_device_script(node['nodeIP']) for node in nodes]
        return types.DataModel().model(code=0, data=data)

    def execute_device_script(self, node_ip):
        cmd = f"sh {app.config['DEPLOY_HOME']}device.sh {node_ip}"
        _, result, _ = utils.execute(cmd)
        logging.info('node load:command: %s, result: %s', cmd, result)
        return ast.literal_eval(result)


# Actually setup the Api resource routing here
api.add_resource(Version, '/')
api.add_resource(NodeCheck, '/api/deploy/node/check')
api.add_resource(NodeSecret, '/api/deploy/node/secret')
api.add_resource(NodeLoad, '/api/deploy/node/load')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2236)
