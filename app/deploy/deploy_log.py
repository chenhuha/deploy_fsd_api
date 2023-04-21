import os

from flask import current_app
from flask import Response
from flask_restful import Resource


class DeployLog(Resource):
    def __init__(self):
        super().__init__()
        self.deploy_home = current_app.config['DEPLOY_HOME']
    
    def get(self):
        file_path = "/var/log/deploy.log"

        if not os.path.isfile(file_path):
            return {'message': 'The file does not exist'}, 404

        # 将文件以流式发送到客户端
        def generate():
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    yield data

        response = Response(generate(), mimetype='application/octet-stream')
        response.headers.set('Content-Disposition', 'attachment', filename='deploy.log')
        response.headers.set('Content-Type', 'application/octet-stream')
        response.headers.set('Content-Length', os.path.getsize(file_path))
        response.headers.set('Cache-Control', 'no-cache')

        return response
