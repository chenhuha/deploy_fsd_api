import ast
import logging

from flask import current_app
from flask_restful import reqparse, Resource
from common import constants, types, utils


class Deploy(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_nodes_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('nodes', required=True, location='json',
                            type=list, help='The nodes field does not exist')
        return parser.parse_args()['nodes']


class NodeCheck(Resource, Deploy):
    def post(self):
        self._generate_ssh_key()
        nodes = self.get_nodes_from_request()

        data = []
        for node in nodes:
            result = self._check_node(node['nodeIP'])
            data.append({'nodeIP': node['nodeIP'], 'result': result})

        return types.DataModel().model(code=0, data=data)

    def _generate_ssh_key(self):
        utils.execute(constants.COMMAND_DELETE_SSH_KEYGEN)
        utils.execute(constants.COMMAND_CREATE_SSH_KEYGEN)

    def _check_node(self, node_ip):
        cmd = constants.COMMAND_CHECK_NODE % (current_app.config['NODE_PASS'], node_ip)
        code, result, _ = utils.execute(cmd)
        self._logger.info('node check command: %s, result: %s', cmd, result)
        return result.rstrip() == constants.COMMAND_CHECK_NODE_SUCCESS and code == 0


class NodeSecret(Resource, Deploy):
    def post(self):
        nodes = self.get_nodes_from_request()
        data = [{'nodeIP': node['nodeIP'], 'result': True}
                for node in nodes if self.node_secret(node)]
        return {'code': 0, 'data': data}

    def node_secret(self, node):
        cmd = constants.COMMAND_SSH_COPY_ID % (
            current_app.config['NODE_PASS'], node['nodeIP'])
        code, result, err = utils.execute(cmd)
        self._logger.info('node secret command: %s, result: %s', cmd, result)
        if constants.COMMAND_SSH_COPY_ID_SUCCESS in result and code == 0:
            return True
        if constants.COMMAND_SSH_COPY_ID_EXIST in err and code == 0:
            return True
        return False


class NodeLoad(Resource, Deploy):
    def post(self):
        nodes = self.get_nodes_from_request()
        data = []
        for node in nodes:
            node_data = self.execute_device_script(node['nodeIP'])
            node_data['nodeType'] = node['nodeType']
            data.append(node_data)

        return types.DataModel().model(code=0, data=data)

    def execute_device_script(self, node_ip):
        cmd = f"sh {current_app.config['DEPLOY_HOME']}device.sh {node_ip}"
        _, result, _ = utils.execute(cmd)
        self._logger.info('node load command: %s, result: %s', cmd, result)
        result_dict = self.format_device_data(result)
        return result_dict

    def format_device_data(self, result):
        result_dict = ast.literal_eval(result)

        # Process network data
        for network in result_dict['networks']:
            network['bond'] = network.pop('isbond') != 'ether'
        result_dict['cards'] = result_dict.pop('networks')

        # Process storage data
        hdds = [storage for storage in result_dict['storages'] if storage['ishdd'] == '1']
        ssds = [storage for storage in result_dict['storages'] if storage['ishdd'] != '1']
        for storage in hdds + ssds:
            storage['purpose'] = 'SYSTEM' if storage['issystem'] == '1' else None
            storage.pop('ishdd')
            storage.pop('issystem')
        
        result_dict['hdds'] = hdds
        result_dict['ssds'] = ssds
        result_dict.pop('storages')

        return result_dict

class NetCheck(Resource, Deploy):
    def post(self):
        nodes = self.get_nodes_from_request()
        
        data = []
        for node in nodes:
            pass
            
        return types.DataModel().model(code=0, data=data)


class DeployCount(Deploy):
    def get_nodes_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cephCopyNumDefault', required=True, location='json',
                            type=int, help='The cephCopyNumDefault field does not exist')
        parser.add_argument('nodes', required=True, location='json',
                            type=list, help='The nodes field does not exist')
        parser.add_argument('serviceType', required=True, location='json',
                            type=list, help='The serviceType field does not exist')
        parser.add_argument('storages', location='json',
                            type=list, help='The storages field does not exist')
        return parser.parse_args()

#通用pg计算
class ReckRecommendConfigCommon(Resource, DeployCount):
    def __init__(self):
        self.voi_storage = {}
        self.sys_storage = {}
        self.ceph_data_storage = []
        self.ceph_cache_storage = []

    def post(self):
        nodes_info = self.get_nodes_from_request()
        print (nodes_info)
        ceph_copy_num_default = nodes_info["cephCopyNumDefault"]
        service_type = nodes_info["serviceType"]
        nodes = nodes_info["nodes"]
        storage_list = nodes_info["storages"]
        self.disk_classification(storage_list)
        if len(nodes) == 1 and len(self.ceph_data_storage) == 1:
            ceph_copy_num_default = 1

        if len(service_type) == 1 and service_type[0] == "VOI":
            only_voi_storage = self.common_voi_storage_count()
            print(only_voi_storage)
            return types.DataModel().model(code=0, data=self.build_data({},{},storageSizeMax=only_voi_storage))
        else:
            pg_all = len(nodes) * len(self.ceph_data_storage) * 100
            data = self.common_ceph_storage_data(service_type,ceph_copy_num_default,pg_all)
            return types.DataModel().model(code=0, data=data)

    # 磁盘类型分类，VOI只支持一个盘
    def disk_classification(self,storage_list):
        for storage in storage_list:
            if storage['purpose'] == 'VOIDATA':
                self.voi_storage = storage
            if storage['purpose'] == 'SYSTEM':
                self.sys_storage = storage
            if storage['purpose'] == 'DATA':
                self.ceph_data_storage.append(storage)
            if storage['purpose'] == 'CACHE':
                self.ceph_cache_storage.append(storage)

    # voi 没有data盘时，使用系统盘-100G
    def common_voi_storage_count(self):
        if not self.voi_storage:
            sys_storage_num = utils.storagetypeformat(self.sys_storage['size'])
            return str(sys_storage_num - 100) + 'GB'
        else:
            return str(utils.storagetypeformat(self.voi_storage['size'])) + 'GB'
    
    def common_ceph_storage_data(self,service_type,ceph_copy_num_default,pg_all):
        image_pgp = 0.1
        volume_pgp = 0.45
        cephfs_pgp = 0.45
        if len(service_type) == 1 and service_type[0] == "VDI":
            volume_pgp = 0.8
            cephfs_pgp = 0.1
        images_pool = utils.getNearPower(int(pg_all * image_pgp / ceph_copy_num_default))
        volume_pool = utils.getNearPower(int(pg_all * volume_pgp / ceph_copy_num_default))
        cephfs_pool = utils.getNearPower(int(pg_all * cephfs_pgp / ceph_copy_num_default))
        ceph_max_size = str(round(self.common_ceph_storage_size() * 0.8, 2)) + 'GB'
        return {
            "commonCustomCeph":{
                "cephCopyNumDefault": ceph_copy_num_default
            },
            "commonCustomPool": {
                "cephfsPoolPgNum": cephfs_pool,
                "cephfsPoolPgpNum" : cephfs_pool,
                "imagePoolPgNum": images_pool,
                "imagePoolPgpNum": images_pool,
                "volumePoolPgNum": volume_pool,
                "volumePoolPgpNum": volume_pool
            },
            "storageSizeMax": ceph_max_size
        }

    def common_ceph_storage_size(self):
        size = 0 
        for storage in self.ceph_data_storage:
            size += utils.storagetypeformat(storage['size'])
        return size

    def build_data(self,commonCustomCeph,commonCustomPool,storageSizeMax):
        return {'commonCustomCeph':commonCustomCeph, 'commonCustomPool':commonCustomPool, 'storageSizeMax':storageSizeMax}

#个性化pg计算
class ShowRecommendConfig(ReckRecommendConfigCommon):
    def post(self):
        nodes_info = self.get_nodes_from_request()
        print (nodes_info)
        ceph_copy_num_default = nodes_info["cephCopyNumDefault"]
        service_type = nodes_info["serviceType"]
        nodes = nodes_info["nodes"]
        for node in nodes:
            self.disk_classification(node['storages'])
        if len(nodes) == 1 and len(self.ceph_data_storage) == 1:
            ceph_copy_num_default = 1

        if len(service_type) == 1 and service_type[0] == "VOI":
            only_voi_storage = self.common_voi_storage_count()
            print(only_voi_storage)
            return types.DataModel().model(code=0, data=self.build_data({},{},storageSizeMax=only_voi_storage))
        else:
            pg_all = len(self.ceph_data_storage) * 100
            data = self.common_ceph_storage_data(service_type,ceph_copy_num_default,pg_all)
            return types.DataModel().model(code=0, data=data)

