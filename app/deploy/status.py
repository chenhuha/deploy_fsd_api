import json

from common import types
from deploy.node_base import Node
from flask_restful import reqparse, Resource


class Status(Resource, Node):
    def __init__(self):
        super().__init__()
        self.process_list = self.get_process_list()
        self.now_list = self.get_now_list()

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('key', required=True, location='json',
                            type=str, help='The key field does not exist')
        key = parser.parse_args()['key']

        data = self.data_format(key)
        return types.DataModel().model(code=0, data=data)

    def data_format(self, key):
        
        data = {
            "processList": self.process_list,
            "nowList": self.now_list,
            "isEnd": self.get_is_end(),
            "key": key,
            "uuId": ""
        }

        return data

    def get_now_list(self):
        try:
            with open('/tmp/deploy_now_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception as e:
            self._logger.error('open file /tmp/deploy_now_status faild: %s', e)
            data = []

        return data

    def get_process_list(self):
        try:
            with open('/tmp/deploy_process_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception as e:
            self._logger.error('open file /tmp/deploy_process_status: %s', e)
            data = []

        return data

    def get_is_end(self):
        is_end = False
        if len(self.process_list) > 0 and len(self.process_list) == len(self.now_list):
            is_end = True
        
        for process in self.now_list:
            if process['result'] == False:
                is_end = True

        return is_end
