from flask_restful import reqparse, Resource
import os
from flask import current_app
from common import types
from werkzeug.utils import secure_filename

class Upgrade(Resource):
    
    def _get_upload_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename', required=True, type=str, location='json',
                            help='The filename field does not exist')
        return parser.parse_args()

    def post(self):
        os.path.join()