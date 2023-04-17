from flask import jsonify
import time,json


class DataModel:
    def model(self, code, data, message="", path=""):
        return jsonify({
            'timestamp': int(time.time() * 1000),
            'state': 200,
            'code': code,
            'message': message,
            'path': path,
            'data': data
        })
    def history_model(self, paramsJson, log,result,startTime, message="" ,key="deploy:klcloud-fsd", id=1, uuid=""):    
        return {
            'paramsJson': paramsJson,
            'log': log,
            'message': message,
            'uuid': uuid,
            'result': result,
            'startTime': startTime,
            'id': id,
            'endtime': int(time.time() * 1000),
            'key': key
        }