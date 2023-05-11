import re
import subprocess
from flask_restful import reqparse, Resource
from common import constants, utils, types
import json
import logging
import os
import yaml
import time
from flask import current_app
from threading import Thread
from upgrade.status import UpgradeStatus as Status


class Upgrade(Resource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.global_path = os.path.join(
            current_app.config['ETC_EXAMPLE_PATH'], 'global_vars.yaml')
        self.history_upgrade_path = os.path.join(
            current_app.config['DEPLOY_HOME'], 'historyUpgrade.json')
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
        new_version = utils.get_new_verison(file_name)

        try:
            cmd = constants.COMMAND_TAR_UNZIP % (
                file_path, current_app.config['UPGRADE_SAVE_PATH'])
            _, result, _ = utils.execute(cmd)
            self._logger.info(
                f"Execute command to decompression zip package '{cmd}', result:{result}")
            data = self._data_build(
                'unzip_upgrade_package', '', True, 0, '解压升级包')
            self._write_upgrade_file([data], True)

            record = types.DataModel().history_upgarde_model(
                new_version, self.version, '', '-')
            self._write_history_upgrade_file(record)
        except Exception as e:
            self._logger.error(
                f'Decompression file {file_path} Field, Because: {e}')
            data = self._data_build(
                'unzip_upgrade_package', 'Failed to decompress the upgrade package', False, 0, '解压升级包')
            self._write_upgrade_file([data], True)

            record = types.DataModel().history_upgarde_model(
                new_version, self.version, False, 'Failed to decompress the upgrade package')
            self._write_history_upgrade_file(record)
            raise

    def mysql_dump(self):
        try:
            with open(self.global_path, 'r') as f:
                config_text = f.read()
            configs = yaml.load(config_text, Loader=yaml.FullLoader)
            mariadb_root_password = configs['mariadb_root_password']
            cmd = constants.COMMAND_MYSQL_DUMP % ('root', mariadb_root_password, '127.0.0.1', os.path.join(
                current_app.config['UPGRADE_SAVE_PATH'], 'upgrade_bak_{}_{}.sql'.format(self.version, time.strftime('%Y-%m-%d', time.localtime(time.time())))))
            self._logger.info(f"Execute command '{cmd}'")
            _, result, _ = utils.execute(cmd)
            data = self._data_build('dump_mysql_data', '', True, 1, '备份数据库')
            self._write_upgrade_file(data)
        except Exception as e:
            data = self._data_build(
                'dump_mysql_data', 'Database backup failure', False, 1, '备份数据库')
            self._logger.error(
                f"Execute command to dump mysql is faild,Because: {e}")
            self._write_upgrade_file(data)
            self._update_history_upgrade_file(
                result=False, message="Database backup failure")
            raise

    def upgrade_script(self, filename):
        upgrade_file = os.path.splitext(os.path.splitext(filename)[0])[0]
        upgrade_path = os.path.join(
            current_app.config['UPGRADE_SAVE_PATH'], upgrade_file)
        cmd = ['sh', os.path.join(
            upgrade_path + '/kly-deploy-api/scripts', 'upgrade.sh'), upgrade_path]

        try:
            results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            thread = Thread(target=self._shell_return_listen, args=(
                current_app._get_current_object(), results))
            thread.start()
            self._logger.info(f"Execute command '{cmd}', result:{results}")
        except Exception as e:
            self._logger.error(
                f"Execute command to Upgrade is faild ,Because: {e}")
            self._update_history_upgrade_file(
                result=False, message="Description Failed to execute the upgrade program")

    def _shell_return_listen(self, app, subprocess_1):
        with app.app_context():
            subprocess_1.wait()

            status_results = Status.get_now_list(self)
            end_results = status_results[-1]
            self._update_history_upgrade_file(
                message=end_results['message'], result=end_results['result'])

    def _write_history_upgrade_file(self, record):
        try:
            with open(self.history_upgrade_path, 'r') as f:
                data = json.load(f)
            data.append(record)

            with open(self.history_upgrade_path, 'w', encoding='UTF-8') as f:
                f.write(json.dumps(data))
        except Exception as e:
            self._logger.error(
                f"Faild write {self.history_upgrade_path} ,Because: {e}")

    def _update_history_upgrade_file(self, result, message):
        try:
            with open(self.history_upgrade_path, 'r') as f:
                data = json.load(f)
            data[-1]['result'] = result
            data[-1]['message'] = message

            with open(self.history_upgrade_path, 'w', encoding='UTF-8') as f:
                f.write(json.dumps(data))

            if result:
                with open('/etc/klcloud-release', 'w') as f:
                    f.write(data[-1]['new_version'])
        except Exception as e:
            self._logger.error(
                f"Faild update {self.history_upgrade_path} ,Because: {e}")

    def _write_upgrade_file(self, data, first=False):
        try:
            if first:
                with open('/tmp/upgrade_now_status', 'w') as f:
                    f.write(json.dumps(data))
                return
            else:
                with open('/tmp/upgrade_now_status', 'r') as f:
                    old_data = f.read()
                new_data = json.loads(old_data)
                new_data.append(data)
                with open('/tmp/upgrade_now_status', 'w') as f:
                    f.write(json.dumps(new_data))
        except Exception as e:
            self._logger.error(
                f'Update file /tmp/upgrade_now_status is Feild, because: {e}')

    def _data_build(self, en, message, result, sort, zh):
        return {
            "en": en,
            "message": message,
            "result": result,
            "sort": sort,
            "zh": zh
        }
