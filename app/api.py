
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource

from common import constants, types, utils

import logging
import os

app = Flask(__name__)
api = Api(app)

# Configuration logger
logfile_dir = '/var/log/deploy/'

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
            code, result, _ = utils.execute(
                constants.COMMAND_CHECK_NODE % ('Troila12#$', node['nodeIP']))

            data.append({'nodeIP': node['nodeIP'], 'result': result.rstrip() == constants.COMMAND_CHECK_NODE_SUCCESS and code ==0 })

        return types.DataModel().model(code=0, data=data)


# Actually setup the Api resource routing here
api.add_resource(Version, '/')
api.add_resource(NodeCheck, '/api/deploy/node/check')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1235, debug=True)
