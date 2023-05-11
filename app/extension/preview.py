import yaml, os, json

from flask import current_app
from common import types

from deploy.preview import Preview

class ExtendPreview(Preview):
    def post(self):
        preview_info = self.get_preview_from_request()
        history_deploy_preview = self.get_deploy_preview_data()
        total_preview = self.build_extend_request(history_deploy_preview ,preview_info)
        config_file = self.file_conversion(total_preview)
        return types.DataModel().model(code=0, data=config_file)

    def get(self):
        file_list = ["ceph-globals.yaml", "global_vars.yaml", "hosts"]
        global_vars_data = []
        for file in file_list:
            with open(current_app.config['ETC_EXAMPLE_PATH'] + file, 'r') as f:
                global_vars_data.append({'shellName': file,
                                         'shellContent': f.read()})
        return types.DataModel().model(code=0, data=global_vars_data)

    def get_deploy_preview_data(self):
        try:
            with open(os.path.join(current_app.config['DEPLOY_HOME'], 'historyDeploy.yml'), 'r') as f:
                datas = yaml.load(f ,Loader=yaml.FullLoader)
            return json.loads(datas['paramsJson'])
        except Exception as e:
            self._logger.error(f"Get Deploy History file or Get paramsJson in file is filed, Because: {e}")
            raise

    def build_extend_request(self, deploy_preview, extend_preview):
        try:
            deploy_common_preview = deploy_preview['common']['commonFixed']
            extend_common_preview = extend_preview['common']['commonFixed']
            deploy_common_preview['blockStorageSize'] += extend_common_preview['blockStorageSize']
            deploy_common_preview['shareDiskSize'] += extend_common_preview['shareDiskSize']
            deploy_common_preview['voiResourceSize'] += extend_common_preview['voiResourceSize']
            deploy_preview['nodes'].extend(extend_preview['nodes'])
            return deploy_preview
        except Exception as e :
            self._logger.error(f"Build total request of historyDeploy and this interface request is failed, Because: {e}")
            raise