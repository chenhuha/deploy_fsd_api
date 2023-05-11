import json

from common import types
from deploy.node_base import Node
from flask_restful import Resource


class UpgradeStatus(Resource, Node):
    def __init__(self):
        super().__init__() 
        self.process_list = self.get_process_list()
        self.now_list = self.get_now_list()

    def get(self):
        data = self.data_format()
        return types.DataModel().model(code=0, data=data)

    def data_format(self):
        data = {
            "processList": self.process_list,
            "nowList": self.now_list,
            "isEnd": self.get_is_end(),
            "uuId": ""
        }

        return data

    def get_now_list(self):
        try:
            with open('/tmp/upgrade_now_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception as e:
            self._logger.error('open file /tmp/upgrade_now_status faild: %s', e)
            data = []

        return data

    def get_process_list(self):
        try:
            with open('/tmp/upgrade_process_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception as e:
            self._logger.error('open file /tmp/upgrade_process_status: %s', e)
            data = []

        return data

    def get_is_end(self):
        is_end = False
        if len(self.process_list) !=0 and len(self.process_list) == len(self.now_list):
            is_end = True
        
        for process in self.now_list:
            if process['result'] == False:
                is_end = True

        return is_end
