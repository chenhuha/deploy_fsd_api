import json

from models.load_info import LoadInfoModel
from deploy.node_load import NodeLoad
from common import types


class ExtendNodeLoad(NodeLoad):
    def __init__(self) -> None:
        super().__init__()
        self.model = LoadInfoModel()

    def post(self):
        data = self.get_device_info()

        if len(data) > 1:
            # 使用 lambda 表达式查找 data 中每个字典的 nodeIP 在 self.nodes 中的位置
            def lookup(node): return self.nodes.index(
                next(item for item in self.nodes if item["nodeIP"] == node["nodeIP"]))
            # 根据 lookup 函数对 data 进行排序
            data.sort(key=lookup)

        deploy_load_json = self.get_deploy_node_load_info()
        deploy_load_json.extend(data)
        self.model.add_load_info_with_id(2, json.dumps(deploy_load_json))

        return types.DataModel().model(code=0, data=data)

    def get_deploy_node_load_info(self):
        return (
            json.loads(info[0])
            if (info := self.model.get_load_info_with_id(1))
            else []
        )
