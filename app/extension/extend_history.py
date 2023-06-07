from models.extend_history import ExtendHistoryModel
from common import types
from flask_restful import Resource

class ExtendHistory(Resource):
    def __init__(self):
       self.extend_history_model = ExtendHistoryModel()
    
    def get(self):
        data = self.get_extend_history()
    
        return types.DataModel().model(code=0, data=data)
    
    def get_extend_history(self):
        return (
            types.DataModel().history_extend_model(
                history_data[1],
                history_data[2],
                history_data[3],
                history_data[4].lower() == 'true' if history_data[5] != '' else '',
                history_data[5],
                history_data[6],
            )
            if (history_data := self.extend_history_model.get_extend_history())
            else []
        )
