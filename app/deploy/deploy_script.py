import os
import subprocess

from common import types
from deploy.preview import Preview
from flask import current_app
from uuid import uuid5


class DeployScript(Preview):
    def post(self):
        preview_info = self.get_preview_from_request()
        config_file = self.file_conversion(preview_info)
        for config in config_file:
            with open(config['shellName'], 'w', encoding='UTF-8') as f:
                f.write(
                    current_app.config['ETC_EXAMPLE_PATH'] + '/' + config['shellContent'])
        self.control_deploy(preview_info)
        return types.DataModel().model(code=0, data="")

    def control_deploy(self, previews):
        if not os.path.exists(current_app.config['TEMPLATE_PATH'] + '/historyDeploy.yml'):
            deploy_type = "first"
        else:
            deploy_type = "retry"
        ceph_flag = previews['common']['commonFixed']['cephServiceFlag']
        deploy_key = previews['key']
        deploy_uuid = uuid5.uuid1()
        cmd = ['sh', current_app.config['SCRIPT_PATH'] + '/setup.sh',
               deploy_key, deploy_type, str(ceph_flag), str(deploy_uuid)]
        subprocess.Popen(cmd)
