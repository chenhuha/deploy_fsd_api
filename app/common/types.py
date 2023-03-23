from flask import jsonify
import time


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
