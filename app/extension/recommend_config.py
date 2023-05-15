import os,yaml,json
from flask import current_app
from common import types, utils
from deploy.recommend_config import ReckRecommendConfigCommon
from models.deploy_history import DeployHistoryModel


class ExtendReckRecommendConfigCommon(ReckRecommendConfigCommon):
    def __init__(self):
        super().__init__()
        self.deploy_history_model = DeployHistoryModel()

    def post(self):
        nodes_info = self.get_nodes_from_request()
        ceph_copy_num_default = nodes_info["cephCopyNumDefault"]
        service_type = nodes_info["serviceType"]
        nodes = nodes_info["nodes"]
        storage_list = nodes_info["storages"]
        self.disk_classification(storage_list)
        extend_pg_all = len(nodes) * len(self.ceph_data_storage) * 100
        all_pgs = self.get_deploy_history_pgs() + extend_pg_all
        data = self.common_ceph_storage_data(len(nodes),
                                                service_type, ceph_copy_num_default, all_pgs)
        return types.DataModel().model(code=0, data=data)

    def get_deploy_history_pgs(self):
        try:
            history_data = self.deploy_history_model.get_deploy_history()
            datas_json = json.loads(history_data[1])
            ceph_datas_num = 0
            for node in datas_json['nodes']:
                for storage in node['storages']:
                    if storage['purpose'] == 'DATA':
                        ceph_datas_num += 1
            pgs = ceph_datas_num * 100
            return pgs
        except Exception as e:
            self._logger.error(f"Get Deploy History file or Get storages in file is filed, Because: {e}")
            raise

# 个性化pg计算
class ExtendShowRecommendConfig(ExtendReckRecommendConfigCommon):
    def post(self):
        nodes_info = self.get_nodes_from_request()
        ceph_copy_num_default = nodes_info["cephCopyNumDefault"]
        service_type = nodes_info["serviceType"]
        nodes = nodes_info["nodes"]
        for node in nodes:
            self.disk_classification(node['storages'])

        extend_pg_all = len(self.ceph_data_storage) * 100
        all_pgs = self.get_deploy_history_pgs() + extend_pg_all
        data = self.common_ceph_storage_data(1,
                                                service_type, ceph_copy_num_default, all_pgs)
        return types.DataModel().model(code=0, data=data)
