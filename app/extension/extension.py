import json
import os
import subprocess
import time

from common import types
from deploy.deploy_script import DeployScript
from extension.preview import ExtendPreview
from flask import current_app
from models.upgrade_history import UpgradeHistoryModel
from models.extend_history import ExtendHistoryModel
from threading import Thread


class Extension(DeployScript, ExtendPreview):
    def __init__(self):
        super().__init__()
        self.extend_history_model = ExtendHistoryModel()

    def post(self):
        preview_info = self.assembly_data()
        config_file = self.file_conversion(preview_info)
        
        for config in config_file:
            file_path = os.path.join(
                current_app.config['ETC_EXAMPLE_PATH'], config['shellName'])
            self._config_bak(
                current_app.config['ETC_EXAMPLE_PATH'], config['shellName'])
            with open(file_path, 'w', encoding='UTF-8') as f:
                f.write(config['shellContent'])
        self.control_deploy(preview_info)

        return types.DataModel().model(code=0, data="")

    def control_deploy(self, previews):
        ceph_flag = previews['common']['commonFixed']['cephServiceFlag']
        results = types.DataModel().history_extend_model(
            params_json=json.dumps(previews),
            log='',
            message='',
            result='',
            start_time=int(time.time() * 1000),
            endtime=int(time.time() * 1000)
        )
        
        self._write_history_file(results)
        upgrade_path = self._get_upgrade_path()
        cmd = ['sh', current_app.config['SCRIPT_PATH'] + '/extension.sh', str(ceph_flag), str(upgrade_path)]
        self._logger.info('extension command: %s', cmd)
        results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        thread = Thread(target=self._shell_return_listen, args=(
            current_app._get_current_object(), results, previews, int(time.time() * 1000)))
        thread.start()
    
    def _shell_return_listen(self, app, subprocess_1, previews, start_time):
        with app.app_context():
            subprocess_1.wait()
            status = self.deploy_status_model.get_deploy_last_status()
            if status:
                deploy_message = status[0]
                deploy_result = status[1]
            else:
                deploy_message = 'deploy faild.'
                deploy_result = 'false'
            results = types.DataModel().history_extend_model(
                params_json=json.dumps(previews),
                log=str(subprocess_1.stdout.read(), encoding='utf-8'),
                start_time=start_time,
                endtime=int(time.time() * 1000),
                message=deploy_message,
                result=deploy_result
            )

            self._write_history_file(results)
            if deploy_result.lower() == 'true':
                self.deploy_history_model.update_deploy_history_params(results['paramsJson'])
                self._write_node_info_csv(previews['nodes'])
                self.scp_deploy(previews['nodes'])

    def _get_upgrade_path(self):
        model = UpgradeHistoryModel()
        update_path = model.get_upgrade_path()
        if update_path:
            return update_path[0]
        return ''
    
    def _write_history_file(self, result):
        self.extend_history_model.create_extend_history_table()
        self.extend_history_model.add_extend_history(
            result['paramsJson'], result['log'], result['message'], 
            result['result'], result['startTime'], result['endtime'])
