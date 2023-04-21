import logging

from flask import current_app
from flask_restful import reqparse


class Node(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.username = current_app.config['NODE_USER']
        self.password = current_app.config['NODE_PASS']
        self.deploy_home = current_app.config['DEPLOY_HOME']

    def get_nodes_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nodes', required=True, location='json',
                            type=list, help='The nodes field does not exist')
        return parser.parse_args()['nodes']
