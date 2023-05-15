import json

from models.load_info import LoadInfoModel
from deploy.node_load import NodeLoad
from common import types


class ExtendNodeLoad(NodeLoad):
    def post(self):
        data = self.get_device_info()

        if len(data) > 1:
            # 使用 lambda 表达式查找 data 中每个字典的 nodeIP 在 self.nodes 中的位置
            lookup = lambda node: self.nodes.index(next(item for item in self.nodes if item["nodeIP"] == node["nodeIP"]))
            # 根据 lookup 函数对 data 进行排序
            data.sort(key=lookup)
        
        deploy_load_json = self.get_deploy_node_load_info()
        deploy_load_json.extend(data)
        self._write_load_info(deploy_load_json)
        
        return types.DataModel().model(code=0, data=data)

    def get_deploy_node_load_info(self):
        model = LoadInfoModel()
        info = model.get_load_info()
        if info:
            data  = json.loads(info[0])
        else:
            data = []
        return data
