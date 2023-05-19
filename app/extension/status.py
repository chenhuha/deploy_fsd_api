from common import types
from deploy.status import Status


class ExtendStatus(Status):
    def post(self):
        data = self.data_format('hello world')
        return types.DataModel().model(code=0, data=data)
