import logging
import os

from deploy.deploy_script import DeployScript
from deploy.net_check import NetCheck, NetCheckCommon
from deploy.node_check import NodeCheck
from deploy.node_load import NodeLoad
from deploy.node_secret import NodeSecret
from deploy.preview import Preview
from deploy.recommend_config import ReckRecommendConfigCommon, ShowRecommendConfig
from deploy.status import Status
from flask import Flask
from flask_restful import Api, Resource


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

# get version
class Version(Resource):
    def get(self):
        return {'version': 'v1.0.0'}


# Actually setup the Api resource routing here
api.add_resource(Version, '/')
api.add_resource(NodeCheck, '/api/deploy/node/check')
api.add_resource(NodeSecret, '/api/deploy/node/secret')
api.add_resource(NodeLoad, '/api/deploy/node/load')
api.add_resource(NetCheck, '/api/deploy/node/netCheck')
api.add_resource(ReckRecommendConfigCommon,
                 '/api/deploy/node/reckRecommendConfigCommon')
api.add_resource(ShowRecommendConfig,
                 '/api/deploy/node/showRecommendConfig')
api.add_resource(NetCheckCommon, '/api/deploy/node/netCheck/common')
api.add_resource(Preview, '/api/deploy/preview')
api.add_resource(DeployScript, '/api/deploy')
api.add_resource(Status, '/api/deploy/status')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2236)
