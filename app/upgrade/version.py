from common import types, utils
from flask_restful import Resource


class CurrentVersion(Resource):
    def get(self):
        version = utils.get_version()
        return types.DataModel().model(code=0, data={"version": version})
