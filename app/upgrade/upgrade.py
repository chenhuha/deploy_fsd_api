from flask_restful import reqparse, Resource
from common import constants, utils, types
import json
import logging
import os
import yaml
import time
from flask import current_app
from threading import Thread


class Upgrade(Resource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
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
        thread = Thread(target=self.start_upgrade, args=(
            current_app._get_current_object(), file_name))
        thread.start()
        return types.DataModel().model(code=0, data="")

    def start_upgrade(self, app, file_name):
        with app.app_context():
            self.decompression(file_name)
            self.mysql_dump()
            self.upgrade_script(file_name)

    def decompression(self, file_name):
        file_path = os.path.join(
            current_app.config['UPGRADE_SAVE_PATH'], file_name)
        try:
            cmd = constants.COMMAND_TAR_UNZIP % (
                file_path, current_app.config['UPGRADE_SAVE_PATH'])
            _, result, _ = utils.execute(cmd)
            self._logger.info(
                f"Execute command to decompression zip package '{cmd}', result:{result}")
            data = self._data_build(True, "unzip_upgrade_package", "解压升级包")
        except Exception as e:
            self._logger.error(
                f'Decompression file {file_path} Field, Because: {e}')
            data = self._data_build(False, "unzip_upgrade_package", "解压升级包")
        self._write_upgrade_file([data], True)

    def mysql_dump(self):
        try:
            with open(self.global_path, 'r') as f:
                config_text = f.read()
            configs = yaml.load(config_text,Loader=yaml.FullLoader)
            mariadb_root_password = configs['mariadb_root_password']
            cmd = constants.COMMAND_MYSQL_DUMP % ('root', mariadb_root_password, '127.0.0.1', os.path.join(
                current_app.config['UPGRADE_SAVE_PATH'], 'upgrade_bak_{}_{}.sql'.format(self.version, time.strftime('%Y-%m-%d', time.localtime(time.time())))))
            self._logger.info(f"Execute command '{cmd}'")
            _, result, _ = utils.execute(cmd)
            data = self._data_build(True, 'dump_mysql_data', '备份数据库')
        except Exception as e:
            data = self._data_build(False, 'dump_mysql_data', '备份数据库')
            self._logger.error(
                f"Execute command to dump mysql is faild,Because: {e}")
        self._write_upgrade_file(data)

    def _write_upgrade_file(self, data, first=False):
        try:
            if first:
                print(data)
                with open('/tmp/upgrade_now_status', 'w') as f:
                    f.write(json.dumps(data))
                return
            else:
                with open('/tmp/upgrade_now_status', 'r+') as f:
                    old_data = f.read()
                    new_data = json.loads(old_data)
                    new_data.append(data)
                    f.write(json.dumps(new_data))
        except Exception as e:
            self._logger.error(
                f'Update file /tmp/upgrade_now_status is Feild, because: {e}')

    def upgrade_script(self, filename):
        try:
            cmd = f"sh {os.path.join(current_app.config['SCRIPT_PATH'], 'upgrade.sh')} \
                { os.path.join(current_app.config['UPGRADE_SAVE_PATH'], os.path.splitext(os.path.splitext(filename)[0])[0]) } {self.version}"
            _, result, _ = utils.execute(cmd)
            self._logger.info(f"Execute command '{cmd}', result:{result}")
        except Exception as e:
            self._logger.error(
                f"Execute command to Upgrade is faild ,Because: {e}")

    def _data_build(self, ok, en, zh):
        return {
            "en": en,
            "message": "成功" if ok else "失败",
            "result": ok,
            "sort": 0,
            "zh": f"{zh}成功" if ok else f"{zh}失败"
        }
