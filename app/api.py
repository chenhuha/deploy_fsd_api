import logging
import os

from deploy.deploy_export import DeployExport
from deploy.deploy_history import DeployHistory
from deploy.deploy_log import DeployLog
from deploy.deploy_script import DeployScript
from deploy.net_check import NetCheck, NetCheckCommon
from deploy.node_check import NodeCheck
from deploy.node_load import NodeLoad
from deploy.node_secret import NodeSecret
from deploy.preview import Preview
from deploy.recommend_config import ReckRecommendConfigCommon, ShowRecommendConfig
from deploy.status import Status
from upgrade.upload import Upload
from upgrade.upgrade_history import UpgradeHistory
from upgrade.status import UpgradeStatus
from upgrade.upgrade import Upgrade
from flask import Flask
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_cors import CORS

app = Flask(__name__)
api = Api(app)
app.config.from_object('config')
CORS(app, supports_credentials=True)

# Configuration logger
logfile_dir = app.config['LOG_PATH']

if not os.path.isdir(logfile_dir):
    os.mkdir(logfile_dir)

log_format = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
logging.basicConfig(filename='/var/log/deploy/klc-deploy-api.log',
                    level=logging.DEBUG, format=log_format)

# get version
class Version(Resource):
    def get(self):
        return {'version': 'v1.0.0'}


# Actually setup the Api resource routing here
api.add_resource(Version, '/')

# Deploy api register
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
api.add_resource(DeployHistory, '/api/deploy/history')
api.add_resource(DeployExport, '/api/deploy/export')
api.add_resource(DeployLog, '/api/deploy/download')

# Upload api register
api.add_resource(Upload, '/api/upgrade/upload')
api.add_resource(Upgrade, '/api/upgrade')
api.add_resource(UpgradeHistory, '/api/upgrade/history')
api.add_resource(UpgradeStatus, '/api/upgrade/status')

# Extension api register


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1236)
