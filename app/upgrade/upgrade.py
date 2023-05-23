import subprocess
import logging
import os
import time

from flask_restful import reqparse, Resource
from models.upgrade_status import UpgradeStatusModel
from models.upgrade_history import UpgradeHistoryModel
from common import constants, utils, types
from flask import current_app
from threading import Thread


class Upgrade(Resource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.file_name = self.get_upgrade_from_request()['filename']
        self.new_version = self.get_upgrade_from_request()['new_version']
        self.version = utils.get_version()
        self.script_path = current_app.config['SCRIPT_PATH']
        self.global_path = os.path.join(
            current_app.config['ETC_EXAMPLE_PATH'], 'global_vars.yaml')
        self.upgrade_history_model = UpgradeHistoryModel()
        self.upgrade_status_model = UpgradeStatusModel()

    def post(self):
        self.upgrade_status_table_init()

        thread = Thread(target=self.start_upgrade, args=(
            current_app._get_current_object(), self.file_name))
        thread.start()

        return types.DataModel().model(code=0, data="")

    def get_upgrade_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename', required=True, type=str, location='json',
                            help='The filename field does not exist')
        parser.add_argument('new_version', required=True, type=str, location='json',
                            help='The new_version field does not exist')
        return parser.parse_args()

    def start_upgrade(self, app, filename):
        with app.app_context():
            self.unzip_upgade_package(filename)
            self.upgrade_script(filename)

    def unzip_upgade_package(self, filename):
        file_path = os.path.join(
            current_app.config['UPGRADE_SAVE_PATH'], filename)

        cmd = constants.COMMAND_TAR_UNZIP % (
            file_path, current_app.config['UPGRADE_SAVE_PATH'])

        code, result, err = utils.execute(cmd)
        if code != 0:
            self._logger.error(
                f'unzip file {file_path} Field, Because: {err}')
            self.upgrade_status_model.add_upgrade_now_status(
                'unzip_upgrade_package',
                'Failed to unzip upgrade package'
                'false', 0, '解压升级包')
            self.upgrade_history_model.add_upgrade_history(
                self.version, self.new_version, 'false',
                'Failed to unzip the upgrade package',
                int(time.time() * 1000))
            raise

        self._logger.info(
            f"Execute command to unzip package '{cmd}', result:{result}")
        self.upgrade_status_model.add_upgrade_now_status(
            'unzip_upgrade_package', '',
            'true', 0, '解压升级包')
        self.upgrade_history_model.add_upgrade_history(
            self.version, self.new_version, 'true',
            '', int(time.time() * 1000))

    def upgrade_script(self, filename):
        upgrade_file = os.path.splitext(os.path.splitext(filename)[0])[0]
        upgrade_path = os.path.join(
            current_app.config['UPGRADE_SAVE_PATH'], upgrade_file)
        cmd = ['sh', os.path.join(
            upgrade_path + '/kly-deploy-api/scripts', 'upgrade.sh'), upgrade_path]

        try:
            results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            thread = Thread(target=self._shell_return_listen, args=(
                current_app._get_current_object(), results, upgrade_path))
            thread.start()
            self._logger.info(f"Execute command '{cmd}', result:{results}")
        except Exception as e:
            self._logger.error(
                f"Execute command to Upgrade is faild ,Because: {e}")
            self._update_history_upgrade_file(
                result="false", message="Failed to execute the upgrade program")

    def _shell_return_listen(self, app, subprocess_1, upgrade_path):
        with app.app_context():
            subprocess_1.wait()
            status = self.upgrade_status_model.get_upgrade_last_status()
            if status:
                upgrade_message = status[0]
                upgrade_result = status[1]
            else:
                upgrade_message = '升级失败！'
                upgrade_result = 'false'

            self._update_history_upgrade_file(
                upgrade_message, upgrade_result, upgrade_path)

    def _update_history_upgrade_file(self, message, result, upgrade_path=''):
        try:
            self.upgrade_history_model.update_upgrade_history(
                result, message, int(time.time() * 1000), upgrade_path)

            if result == 'true':
                with open('/etc/klcloud-release', 'w') as f:
                    f.write(self.new_version)
        except Exception as e:
            self._logger.error(
                f"Faild update /etc/klcloud-release ,Because: {e}")

    def upgrade_status_table_init(self):
        self.upgrade_status_model.create_upgrade_status_table()
        cmd = f"sh {self.script_path}/upgrade_data_init.sh"
        try:
            _, result, _ = utils.execute(cmd)
        except Exception as e:
            self._logger.error(
                f"Failed to execute upgrade_data_init script: {e}")
            return

        self._logger.info(
            'upgrade_data_init command: %s, result: %s', cmd, result)
