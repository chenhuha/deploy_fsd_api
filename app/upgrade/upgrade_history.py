import os
import json

from common import types
from deploy.node_base import Node
from flask import current_app
from flask_restful import reqparse, Resource


class UpgradeHistory(Resource, Node):
    def __init__(self):
        super().__init__()
        self.deploy_home = current_app.config['DEPLOY_HOME']

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            'page', type=int, location='args', help='page number')
        parser.add_argument(
            'size', type=int, location='args', help='items per page')
        parser.add_argument(
            'sort', type=str, location='args', help='sort order')
        parser.add_argument('version', type=str,
                            location='args', help='search query')
        parser.add_argument('new_version', type=str,
                            location='args', help='search query')
        parser.add_argument('start_time', type=int,
                            location='args', help='start time')
        parser.add_argument('end_time', type=int,
                            location='args', help='end time')
        parser.add_argument('result', type=str,
                            location='args', help='search query')
        args = parser.parse_args()

        page = args.get('page', 1)
        size = args.get('size', 10)
        sort = args.get('sort')
        version = args.get('version')
        new_version = args.get('new_version')
        start_time = args.get('start_time')
        end_time = args.get('end_time')
        result = args.get('result')
        history_data = self.get_upgrade_history()
        data = self.filter_and_paginate_history_data(
            history_data=history_data,
            page=page or 1,
            size=size or 10,
            version=version,
            new_version=new_version,
            start_time=start_time,
            end_time=end_time,
            result=result,
            sort=sort)

        return types.DataModel().model(code=0, data=data)

    def delete(self):
        data = self.del_deploy_history()

        return types.DataModel().model(code=0, data=data)

    def filter_and_paginate_history_data(self, history_data, page, size, version, new_version, start_time, end_time, result, sort):
        # 过滤数据
        if version:
            history_data = [d for d in history_data if d['version'] == version]
        if new_version:
            history_data = [d for d in history_data if d['new_version'] == new_version]
        if start_time and end_time:
            history_data = [d for d in history_data if d['endtime'] >= start_time and d['endtime'] <= end_time]
        if result is not None:
            result = result.lower() == 'true'
            history_data = [d for d in history_data if d['result'] == result]

        # 排序数据
        if sort == 'endtime':
            history_data = sorted(history_data, key=lambda x: x['endtime'], reverse=True)

        # 分页数据
        start_index = (page - 1) * size
        end_index = start_index + size
        history_result = history_data[start_index:end_index]

        # 格式化数据
        total = len(history_data)
        data = {
            'total': total,
            'history_data': history_result
        }

        return data

    def get_upgrade_history(self):
        history_file = self.deploy_home + '/historyUpgrade.json'

        if not os.path.isfile(history_file):
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            data = content
        except Exception as e:
            self._logger.error(
                f'open file historyUpgrade.json failed, Because: {e}')
            data = []

        return data

    def del_deploy_history(self):
        history_file = self.deploy_home + '/historyUpgrade.json'

        if os.path.isfile(history_file):
            os.remove(history_file)

        return None
