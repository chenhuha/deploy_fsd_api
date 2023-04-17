import json

from common import types
from flask_restful import reqparse, Resource


class Status(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('key', required=True, location='json',
                            type=str, help='The key field does not exist')
        key = parser.parse_args()['key']

        data = self.data_format(key)
        return types.DataModel().model(code=0, data=data)

    def data_format(self, key):
        process_list = self.get_process_list()
        now_list = self.get_now_list()
        is_end = False

        if len(process_list) == len(now_list):
            is_end = True

        data = {
            "processList": process_list,
            "nowList": now_list,
            "isEnd": is_end,
            "key": key,
            "uuId": ""
        }

        return data

    def get_now_list(self):
        try:
            with open('/tmp/deploy_now_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception:
            data = []

        return data

    def get_process_list(self):
        try:
            with open('/tmp/deploy_process_status', 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
        except Exception:
            data = []

        return data
