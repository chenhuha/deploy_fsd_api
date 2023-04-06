
from flask import Flask
from flask_restful import Api, Resource
from service import deploy

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

# get version
class Version(Resource):
    def get(self):
        return {'version': 'v1.0.0'}


# Actually setup the Api resource routing here
api.add_resource(Version, '/')
api.add_resource(deploy.NodeCheck, '/api/deploy/node/check')
api.add_resource(deploy.NodeSecret, '/api/deploy/node/secret')
api.add_resource(deploy.NodeLoad, '/api/deploy/node/load')
api.add_resource(deploy.NetCheck, '/api/deploy/node/netCheck')
api.add_resource(deploy.ReckRecommendConfigCommon, '/api/deploy/node/reckRecommendConfigCommon')
api.add_resource(deploy.ShowRecommendConfig, '/api/deploy/node/showRecommendConfig')

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=2236)
