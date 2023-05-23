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
from upgrade.version import CurrentVersion
from upgrade.upload import Upload
from upgrade.upgrade import Upgrade
from upgrade.upgrade_history import UpgradeHistory
from upgrade.status import UpgradeStatus
from upgrade.upgrade import Upgrade
from extension.load import ExtendNodeLoad
from extension.net_chek import ExtendNetCheck, ExtendNetCheckCommon
from extension.recommend_config import ExtendReckRecommendConfigCommon, ExtendShowRecommendConfig
from extension.preview import ExtendPreview
from extension.extension import Extension
from extension.extend_history import ExtendHistory
from extension.status import ExtendStatus

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
logging.basicConfig(filename=logfile_dir + '/klc-deploy-api.log',
                    level=logging.DEBUG, format=log_format)

# get version
class Version(Resource):
    def get(self):
        return {'version': 'v1.0.0'}


# Actually setup the Api resource routing here
api.add_resource(Version, '/')

# Deploy api register
api.add_resource(NodeCheck, '/api/deploy/node/check', '/api/extend/node/check')
api.add_resource(NodeSecret, '/api/deploy/node/secret',
                 '/api/extend/node/secret')
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
api.add_resource(DeployExport, '/api/deploy/export', '/api/extend/export')
api.add_resource(DeployLog, '/api/deploy/download', '/api/extend/download')

# Upload api register
api.add_resource(CurrentVersion, '/api/upgrade/current/version')
api.add_resource(Upload, '/api/upgrade/upload')
api.add_resource(Upgrade, '/api/upgrade')
api.add_resource(UpgradeHistory, '/api/upgrade/history')
api.add_resource(UpgradeStatus, '/api/upgrade/status')

# Extension api register
api.add_resource(ExtendNodeLoad, '/api/extend/node/load')
api.add_resource(ExtendNetCheck, '/api/extend/node/netCheck')
api.add_resource(ExtendReckRecommendConfigCommon,
                 '/api/extend/node/reckRecommendConfigCommon')
api.add_resource(ExtendShowRecommendConfig,
                 '/api/extend/node/showRecommendConfig')
api.add_resource(ExtendNetCheckCommon, '/api/extend/node/netCheck/common')
api.add_resource(ExtendPreview, '/api/extend/preview')
api.add_resource(Extension, '/api/extend')
api.add_resource(ExtendHistory, '/api/extend/history')
api.add_resource(ExtendStatus, '/api/extend/status')


if __name__ == '__main__':
    port = app.config['PORT']
    app.run(host='0.0.0.0', port=port)
