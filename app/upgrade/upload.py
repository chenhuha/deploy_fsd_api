
import logging
import os
import shutil

from flask_restful import reqparse, Resource
from flask import current_app
from common import types
from werkzeug.utils import secure_filename


class Upload(Resource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.ALLOWED_EXTENSIONS = 'gz'

    def _get_upload_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('file', required=True, type=reqparse.FileStorage, location='files',
                            help='The file field does not exist')
        return parser.parse_args()

    def post(self):
        file = self._get_upload_from_request()['file']
        if file and self._allowed_file(file.filename):
            self.ensure_upgrade_dir_exists()
            try:
                filename = secure_filename(file.filename)
                file.save(os.path.join(
                    current_app.config['UPGRADE_SAVE_PATH'], filename))
                return types.DataModel().model(code=0, data="", message="上传成功")
            except Exception as e:
                self._logger.error(
                    f'Failed to upload file {secure_filename(file.filename)}, Because: {e}')
                return types.DataModel().model(code=10304, data="", message="上传失败")
        else:
            return types.DataModel().model(code=10704, data="", message="文件名错误")

    def _allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == self.ALLOWED_EXTENSIONS

    def ensure_upgrade_dir_exists(self):
        upgrade_dir = "/opt/kly-upgrade/"

        try:
            if os.path.exists(upgrade_dir):
                shutil.rmtree(upgrade_dir)
            else:
                os.makedirs(upgrade_dir)
        except OSError as e:
            self._logger.error(f'Failed operation {upgrade_dir}, Because: {e}')
