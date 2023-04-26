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
        parser.add_argument('endtime', type=int,
                            location='args', help='search query')
        parser.add_argument('result', type=str,
                            location='args', help='search query')
        args = parser.parse_args()

        page = args['page'] or 1
        size = args['size'] or 10
        sort = args['sort'] or None
        version = args['version'] or None
        new_version = args['new_version'] or None
        endtime = args['endtime'] or None
        result = args['result'] or None

        data = self.data_format(page, size, sort, version,
                                new_version, endtime, result)

        return types.DataModel().model(code=0, data=data)

    def data_format(self, page, size, sort, version, new_version, endtime, result):
        history_data, total = self.get_upgrade_history()
        if version:
            history_data = [
                d for d in history_data if d['version'] == version]
            total = len(history_data)
        if new_version:
            history_data = [
                d for d in history_data if d['new_version'] == new_version]
            total = len(history_data)
        if endtime:
            history_data = [
                d for d in history_data if d['endtime'] == endtime]
            total = len(history_data)
        if result:
            result = result.lower() == 'true'
            history_data = [
                d for d in history_data if d['result'] == result]
            total = len(history_data)
        if sort == 'endtime':
            history_data = sorted(
                history_data, key=lambda x: x['endtime'], reverse=True)

        start_index = (page - 1) * size
        end_index = start_index + size
        history_result = history_data[start_index:end_index]

        data = {
            'total': total,
            'history_data': history_result
        }

        return data

    def delete(self):
        data = self.del_deploy_history()

        return types.DataModel().model(code=0, data=data)

    def get_upgrade_history(self):
        history_file = self.deploy_home + '/historyUpgrade.yml'

        if not os.path.isfile(history_file):
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            data = content
        except Exception as e:
            self._logger.error(f'open file historyUpgrade.yml failed, Because: {e}')
            data = []

        return data, len(data)

    def del_deploy_history(self):
        history_file = self.deploy_home + '/historyUpgrade.yml'

        if os.path.isfile(history_file):
            os.remove(history_file)

        return None
