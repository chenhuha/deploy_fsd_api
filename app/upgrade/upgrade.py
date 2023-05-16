import subprocess
import logging
import os
import yaml
import time

from flask_restful import reqparse, Resource
from models.upgrade_status import UpgradeStatusModel
from models.upgrade_history import UpgradeHistoryModel
from common import constants, utils, types
from flask import current_app
from threading import Thread
from upgrade.status import UpgradeStatus as Status


class Upgrade(Resource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.global_path = os.path.join(
            current_app.config['ETC_EXAMPLE_PATH'], 'global_vars.yaml')
        self.version = utils.get_version()

        self.upgrade_history_model = UpgradeHistoryModel()
        self.upgrade_status_model = UpgradeStatusModel()

    def _get_upgrade_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename', required=True, type=str, location='json',
                            help='The filename field does not exist')

        return parser.parse_args()

    def post(self):
        file_name = self._get_upgrade_from_request()['filename']
        
        self.upgrade_status_model.create_upgrade_status_table()
        data = self._data_build('unzip_upgrade_package', '', '-', 0, '解压升级包')
        self._write_upgrade_file(data)

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
        cmd = constants.COMMAND_TAR_UNZIP % (
            file_path, current_app.config['UPGRADE_SAVE_PATH'])
        code, result, err = utils.execute(cmd)
        if code != 0:
            self._logger.error(
                f'Decompression file {file_path} Field, Because: {err}')
            data = self._data_build(
                'unzip_upgrade_package', 'Failed to decompress the upgrade package', False, 0, '解压升级包')
            self._write_upgrade_file(data)
            record = types.DataModel().history_upgarde_model(
                new_version, int(time.time() * 1000), self.version, False, 'Failed to decompress the upgrade package')
            self._write_history_upgrade_file(record)
            raise
        self._logger.info(
            f"Execute command to decompression zip package '{cmd}', result:{result}")

        data = self._data_build('unzip_upgrade_package', '', True, 0, '解压升级包')
        self._write_upgrade_file(data)
        record = types.DataModel().history_upgarde_model(
            new_version, int(time.time() * 1000), self.version, '', '-')
        self._write_history_upgrade_file(record)

    def mysql_dump(self):
        with open(self.global_path, 'r') as f:
            config_text = f.read()
        configs = yaml.load(config_text, Loader=yaml.FullLoader)
        mariadb_root_password = configs['mariadb_root_password']
        cmd = constants.COMMAND_MYSQL_DUMP % ('root', mariadb_root_password, '127.0.0.1', os.path.join(
            current_app.config['UPGRADE_SAVE_PATH'], 'upgrade_bak_{}_{}.sql'.format(self.version, time.strftime('%Y-%m-%d', time.localtime(time.time())))))
        self._logger.info(f"Execute command '{cmd}'")
        code, result, err = utils.execute(cmd)
        if code != 0:
            data = self._data_build(
                'dump_mysql_data', 'Database backup failure', False, 1, '备份数据库')
            self._logger.error(
                f"Execute command to dump mysql is faild,Because: {e}")
            self._write_upgrade_file(data)
            self._update_history_upgrade_file(
                result="false", message="Database backup failure")
            raise
        data = self._data_build('dump_mysql_data', '', True, 1, '备份数据库')
        self._write_upgrade_file(data)

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
                result="false", message="Description Failed to execute the upgrade program")

    def _shell_return_listen(self, app, subprocess_1):
        with app.app_context():
            subprocess_1.wait()
            status = self.upgrade_status_model.get_upgrade_last_status()
            if status:
                upgrade_message = status[0]
                upgrade_result = status[1]
            else:
                upgrade_message = '升级失败！'
                upgrade_result = 'false'
            self._update_history_upgrade_file(upgrade_message, upgrade_result)

    def _write_history_upgrade_file(self, record):
        self.upgrade_history_model.add_upgrade_history(
            record['version'], 
            record['new_version'], 
            record['result'], 
            record['message'], 
            record['endtime'])

    def _update_history_upgrade_file(self, message, result):
        try:
            self.upgrade_history_model.update_upgrade_history(
                result, message, int(time.time() * 1000))
            if result:
                version = self.upgrade_history_model.get_upgrade_version()
                with open('/etc/klcloud-release', 'w') as f:
                    f.write(version[0])
        except Exception as e:
            self._logger.error(
                f"Faild update /etc/klcloud-release ,Because: {e}")

    def _write_upgrade_file(self, data):
        self.upgrade_status_model.add_upgrade_now_status(
            data['en'], data['message'], data['result'], data['sort'], data['zh'])

    def _data_build(self, en, message, result, sort, zh):
        return {
            "en": en,
            "message": message,
            "result": result,
            "sort": sort,
            "zh": zh
        }
