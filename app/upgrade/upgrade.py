from flask_restful import reqparse, Resource
from flask import jsonify
from common import constants, utils
import os
import yaml
import tarfile
from flask import current_app
from threading import Thread


class Upgrade(Resource):
    def __init__(self):
        self.global_path = os.path.join(
            current_app.config['ETC_EXAMPLE_PATH'], 'global_vars.yaml')
        self.version = utils.get_version()

    def _get_upgrade_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename', required=True, type=str, location='json',
                            help='The filename field does not exist')
        return parser.parse_args()

    def post(self):
        file_name = self._get_upgrade_from_request()['filename']
        thread = Thread(target=self.start_upgrade, args=(file_name))
        thread.start()

    def start_upgrade(self,file_name):
        self.decompression(file_name)
        self.mysql_dump()
        self.upgrade_script(file_name)

    def decompression(self, file_name):
        file_path = os.path.join(current_app.config['UPGRADE_SAVE_PATH'], file_name)
        try:
            with tarfile.open(file_path) as tar:
                tar.extractall(current_app.config['UPGRADE_SAVE_PATH'])
                tar.close()
            data = self._data_build(True)
        except Exception as e:
            self._logger.error(
                f'Decompression file {file_path} Field, Because: {e}')
            data = self._data_build(False)
        self._write_upgrade_file(data)

    def _data_build(self, ok):
        return {
            "en": "unzip_upgrade_package",
            "message": "成功" if ok else "失败",
            "result": ok,
            "sort": 0,
            "zh": "解压升级包成功" if ok else "解压升级包失败"
        }

    def mysql_dump(self):
        try:
            with open(self.global_path, 'r') as f:
                config_text = f.read()
            configs = yaml.load(config_text)
            mariadb_root_password = configs['mariadb_root_password']
            cmd = constants.COMMAND_MYSQL_DUMP % ('root', mariadb_root_password, '127.0.0.1', os.path.join(
                current_app.config['UPGRADE_SAVE_PATH'], 'upgrade_bak_{}.sql'.format(self.version)))
            _, result, _ = utils.execute(cmd)
            self._logger.info(f"Execute command '{cmd}', result:{result}")
            data = self._dump_mysql_data_buid(True)
        except Exception as e:
            data = self._dump_mysql_data_buid(False)
            self._logger.error(
                f"Execute command to dump mysql is faild ,Because: {e}")
        self._write_upgrade_file(data)

    def _dump_mysql_data_buid(self, ok):
        return {
            "en": "dump_mysql_data",
            "message": "成功" if ok else "失败",
            "result": ok,
            "sort": 1,
            "zh": "备份数据库成功" if ok else "备份数据库失败"
        }

    def _write_upgrade_file(self, data):
        try:
            with open('/tmp/upgrade_now_status', 'w') as f:
                f.write(jsonify([data]))
        except Exception as e:
            self._logger.error(
                f'Open file /tmp/upgrade_now_status is Feild, because: {e}')

    def upgrade_script(self,filename):
        try:
            cmd = f"sh {os.path.join(current_app.config['SCRIPT_PATH'], 'upgrade.sh')} {filename.split('.')[0]} {self.version}"
            _, result, _ = utils.execute(cmd)
            self._logger.info(f"Execute command '{cmd}', result:{result}")
        except Exception as e:
            self._logger.error(
                f"Execute command to Upgrade is faild ,Because: {e}")