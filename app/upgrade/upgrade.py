from flask_restful import reqparse, Resource
from flask import jsonify
import os
import tarfile
from flask import current_app
from threading import Thread

class Upgrade(Resource):

    def _get_upgrade_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename', required=True, type=str, location='json',
                            help='The filename field does not exist')
        return parser.parse_args()

    def post(self):
        file_name = self._get_upgrade_from_request()['filename']
        path = os.path.join(current_app.config['UPGRADE_SAVE_PATH'], file_name)
        thread = Thread(target=self.decompression, args=(path))
        thread.start()

    def decompression(self,file_path):
        try:
            with tarfile.open(file_path) as tar:
                tar.extractall(current_app.config['UPGRADE_SAVE_PATH'])
                tar.close()
            data = self._data_build(True)
        except Exception as e:
            self._logger.error(f'Decompression file {file_path} Field, Because: {e}')
            data = self._data_build(False)
        
        try:
            with open('/tmp/upgrade_now_status' , 'w') as f:
                f.write(jsonify([data]))
        except Exception as e:
            self._logger.error(f'Open file /tmp/upgrade_now_status is Feild, because: {e}')
    
    def _data_build(self,ok):
        return {
            "en": "unzip_upgrade_package",
            "message": "成功" if ok else "失败" ,
            "result": ok,
            "sort": 0,
            "zh": "解压升级包成功" if ok else "解压升级包失败"
        }
