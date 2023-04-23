import os
import json

from common import types
from flask import current_app
from flask_restful import Resource

class UpgradeHistory(Resource):
    def __init__(self):
       self.deploy_home = current_app.config['DEPLOY_HOME']
    
    def get(self):
        data = self.get_upgrade_history()
    
        return types.DataModel().model(code=0, data=data)
    
    def delete(self):
        data = self.del_deploy_history()
    
        return types.DataModel().model(code=0, data=data)

    def get_upgrade_history(self):
        history_file = self.deploy_home + '/historyUpgrade.yml'

        if not os.path.isfile(history_file):
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            data = content['history_data']
        except Exception as e:
            self._logger.error('open file historyUpgrade.yml: %s', e)
            data = []

        return data
    
    def del_deploy_history(self):
        history_file = self.deploy_home + '/historyUpgrade.yml'

        if os.path.isfile(history_file):
            os.remove(history_file)

        return None
