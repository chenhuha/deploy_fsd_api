from models.deploy_history import DeployHistoryModel
from common import types
from flask_restful import Resource

class DeployHistory(Resource):
    def __init__(self):
       self.deploy_history_model = DeployHistoryModel()
    
    def get(self):
        data = self.get_deploy_history()
    
        return types.DataModel().model(code=0, data=data)
    
    def delete(self):
        data = self.deploy_history_model.del_deploy_history()
    
        return types.DataModel().model(code=0, data=data)

    def get_deploy_history(self):
        history_data = self.deploy_history_model.get_deploy_history()
        if history_data:
            results = types.DataModel().history_deploy_model(
                paramsJson=history_data[1],
                log=history_data[2],
                message=history_data[3],
                result=bool(history_data[5].lower() == 'true') if history_data[5] != '' else '',
                startTime=history_data[6],
                endtime=history_data[7]
            )
        else:
            results = []
            
        return results
