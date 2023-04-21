import os
import json,yaml
import subprocess
import time

from common import types
from deploy.preview import Preview
from flask import current_app
from uuid import uuid1
from threading import Thread
from deploy.status import Status
from deploy.node_base import Node


class DeployScript(Preview, Node):
    def post(self):
        preview_info = self.get_preview_from_request()
        config_file = self.file_conversion(preview_info)
        for config in config_file:
            with open(config['shellName'], 'w', encoding='UTF-8') as f:
                f.write(
                    current_app.config['ETC_EXAMPLE_PATH'] + '/' + config['shellContent'])
        self.control_deploy(preview_info)
        # thread = Thread(target=self.control_deploy, args=(preview_info,current_app._get_current_object()))
        # thread.start()
        return types.DataModel().model(code=0, data="")

    def control_deploy(self, previews):
        # time.sleep(3)
        if not os.path.exists(current_app.config['DEPLOY_HOME'] + '/historyDeploy.yml'):
            deploy_type = "first"
        else:
            deploy_type = "retry"
        ceph_flag = previews['common']['commonFixed']['cephServiceFlag']
        deploy_key = previews['key']
        deploy_uuid = str(uuid1())
        results = types.DataModel().history_model(
            paramsJson=json.dumps(previews),
            uuid = deploy_uuid,
            startTime= int(time.time() * 1000)
            )
        self._write_history_file(results)
        cmd = ['sh', current_app.config['SCRIPT_PATH'] + '/setup.sh',
            deploy_key, deploy_type, str(ceph_flag), str(deploy_uuid)]
        self._logger.info('deploy command: %s', cmd)
        results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        thread = Thread(target=self._shell_return_listen, args=(current_app._get_current_object(),results,previews,deploy_uuid,int(time.time() * 1000)))
        thread.start()

    def _shell_return_listen(self, app, subprocess_1, previews,deploy_uuid,start_time):
        with app.app_context():
            subprocess_1.wait()
            status_results = Status.get_now_list(self)
            end_results = status_results[-1]
            results = types.DataModel().history_model(
                log=str(subprocess_1.stdout.read(), encoding='utf-8'),
                paramsJson=json.dumps(previews),
                uuid = deploy_uuid,
                startTime= start_time,
                message=end_results['message'],
                result=end_results['result']
                )
            self._write_history_file(results)

    def _write_history_file(self, result):
        results_yaml = yaml.dump(result,sort_keys=False,allow_unicode=True)
        with open(current_app.config['DEPLOY_HOME'] + '/historyDeploy.yml', 'w', encoding='UTF-8') as f:
            f.write(results_yaml)

