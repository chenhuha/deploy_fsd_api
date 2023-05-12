import json,yaml
import os
import shutil
from deploy.net_check import NetCheck,NetCheckCommon
from common import types
from flask import current_app



class ExtendNetCheck(NetCheck):
    def __init__(self):
        super().__init__()
        self.nodes = self.get_nodes_from_request() + self.get_node_load_card_info()
        self.node_list = self.get_info_with_from(self.nodes)

    def post(self):
        data = self.multiple_nodes_data()
        # 保存数据到本地
        node_info_file = os.path.join(
            self.deploy_home, "deploy_node_info.xlsx")
        if os.path.isfile(node_info_file):
            os.remove(node_info_file)
        node_info_file = os.path.join(
            self.deploy_home, "deploy_node_info.xlsx")
        source_file = os.path.join(self.template_path, "deployExcel.xlsx")
        try:
            shutil.copyfile(source_file, node_info_file)
            self.write_data_to_excel(node_info_file, data)
        except Exception as e:
            self._logger.error('write data to excel error, %s', e)
        
        return types.DataModel().model(code=0, data=data)

    def get_node_load_card_info(self):
        try:
            cards_list = []
            card_data = {
                "cards":[],
                "nodeIP": "",
                "nodeName": ""
                }
            with open(os.path.join(current_app.config['DEPLOY_HOME'], 'historyDeploy.yml'), 'r') as f:
                datas = yaml.load(f ,Loader=yaml.FullLoader)
            datas_json = json.loads(datas['paramsJson'])
            for node in datas_json['nodes']:
                card_data['cards'] = node['networkCards']
                card_data['nodeIP'] = node['nodeIP']
                card_data['nodeName'] = node['nodeName']
                cards_list.append(card_data)
            return cards_list
        except Exception as e:
            self._logger.error(f"Failed to load json ans build cards list file: {e}")
            raise


class ExtendNetCheckCommon(ExtendNetCheck,NetCheckCommon):
    def __init__(self):
        nodes = self.get_nodes_from_request()
        cards = self.get_cards_from_request()
        extend_nodes = self.get_deploy_cards()
        extend_nodes.extend(self.uniform_format_with_nodes(nodes, cards))
        self.nodes = extend_nodes
        super().__init__()

    def get_deploy_cards(self):
        try:
            node_card_list = []
            node_card_data = {
                "cards": [],
                "nodeIP": "",
                "nodeName": ""
            }
            with open(os.path.join(current_app.config['DEPLOY_HOME'], 'historyDeploy.yml'), 'r') as f:
                datas = yaml.load(f ,Loader=yaml.FullLoader)
            datas_json = json.loads(datas['paramsJson'])
            for node in datas_json['nodes']:
                node_card_data['cards'] = node['networkCards']
                node_card_data['nodeIP'] = node['nodeIP']
                node_card_data['nodeName'] = node['nodeName']
                node_card_list.append(node_card_data)
            return node_card_list
        except Exception as e:
            self._logger.error(f"Get Deploy History file or Get NETCARD in file is filed, Because: {e}")
            raise
