import os
import yaml

from common import types
from flask import current_app
from flask_restful import Resource

class DeployHistory(Resource):
    def __init__(self):
       self.deploy_home = current_app.config['DEPLOY_HOME']
    
    def get(self):
        data = self.get_deploy_history()
    
        return types.DataModel().model(code=0, data=data)
    
    def delete(self):
        data = self.del_deploy_history()
    
        return types.DataModel().model(code=0, data=data)

    def get_deploy_history(self):
        history_file = self.deploy_home + '/historyDeploy.yml'

        if not os.path.isfile(history_file):
            return None

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = yaml.load(f,Loader=yaml.FullLoader)
        except Exception as e:
            self._logger.error('open file historyDeploy.yml: %s', e)
            data = []

        return data
    
    def del_deploy_history(self):
        history_file = self.deploy_home + '/historyDeploy.yml'

        if os.path.isfile(history_file):
            os.remove(history_file)

        return None
