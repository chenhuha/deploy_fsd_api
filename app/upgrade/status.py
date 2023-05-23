from common import types
from deploy.node_base import Node
from models.upgrade_status import UpgradeStatusModel
from flask_restful import Resource


class UpgradeStatus(Resource, Node):
    def __init__(self):
        super().__init__()
        self.model = UpgradeStatusModel()
        self.process_list = self.get_process_list()
        self.now_list = self.get_now_list()

    def get(self):
        data = self.data_format()
        return types.DataModel().model(code=0, data=data)

    def get_now_list(self):
        try:
            now_staus = self.model.get_upgrade_now_status()
            data = self.status_data_format(now_staus)
        except Exception as e:
            self._logger.error('upgrade_now_status: %s', e)
            data = []

        return data

    def get_process_list(self):
        try:
            process_status = self.model.get_upgrade_process_status()
            data = self.status_data_format(process_status)
        except Exception as e:
            self._logger.error('upgrade_process_status: %s', e)
            data = []

        return data

    def get_is_end(self):
        is_end = False
        if len(self.process_list) != 0 and len(self.process_list) == len(self.now_list):
            is_end = True

        for process in self.now_list:
            if process['result'] == False:
                is_end = True

        return is_end

    def status_data_format(self, datas):
        status_list = []
        for data in datas:
            status = {
                'en': data[1],
                'message': data[2],
                'result': True if data[3] == 'true' else False,
                'sort': data[4],
                'zh': data[5]
            }
            status_list.append(status)
        return status_list

    def data_format(self):
        data = {
            "processList": self.process_list,
            "nowList": self.now_list,
            "isEnd": self.get_is_end(),
            "uuId": ""
        }

        return data
