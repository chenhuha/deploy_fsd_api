from common import types, utils
from deploy.node_base import Node
from flask_restful import reqparse, Resource


class DeployCount(Node):
    def get_nodes_from_request(self):
        parser = reqparse.RequestParser()
        fields = [
            ('cephCopyNumDefault', int, True, 'The cephCopyNumDefault field does not exist'),
            ('cephServiceFlag', bool, True, 'The cephServiceFlag field does not exist'),
            ('localServiceFlag', bool, True, 'The localServiceFlag field does not exist'),
            ('nodes', list, True, 'The nodes field does not exist'),
            ('serviceType', list, True, 'The serviceType field does not exist'),
            ('storages', list, False, 'The storages field does not exist')
        ]
        
        for field, field_type, required, error_msg in fields:
            parser.add_argument(field, required=required, location='json', type=field_type, help=error_msg)

        return parser.parse_args()



# 通用pg计算
class ReckRecommendConfigCommon(Resource, DeployCount):
    def __init__(self):
        self.ceph_cache_storage = []
        self.ceph_data_storage = []
        self.local_storage = []
        self.sys_storage = None
        self.voi_storage = None

    def post(self):
        nodes_info = self.get_nodes_from_request()
        ceph_copy_num_default = nodes_info['cephCopyNumDefault']
        ceph_service_flag = nodes_info['cephServiceFlag']
        local_service_flag = nodes_info['localServiceFlag']

        service_type = nodes_info['serviceType']
        nodes = nodes_info['nodes']
        storage_list = nodes_info.get('storages', [])
        self.classify_disks(storage_list)

        if self.should_calculate_only_voi(service_type):
            data = {'storageSizeMax': self.calculate_only_voi_storage()}
            return types.DataModel().model(code=0, data=data)

        data = {} 
        if ceph_service_flag:
            if len(nodes) == 1 and len(self.ceph_data_storage) == 1:
                ceph_copy_num_default = 1
            pg_all = len(nodes) * len(self.ceph_data_storage) * 100
            data = self.calculate_ceph_storage(
                len(nodes), service_type, ceph_copy_num_default, pg_all)

        if local_service_flag:
            data['localSizeMax'] = self.calculate_local_storage(len(nodes))

        return types.DataModel().model(code=0, data=data)

    def classify_disks(self, storage_list):
        for storage in storage_list:
            purpose = storage['purpose']
            if purpose == 'CEPH_CACHE':
                self.ceph_cache_storage.append(storage)
            elif purpose == 'CEPH_DATA':
                self.ceph_data_storage.append(storage)
            elif purpose == 'LOCAL_DATA':
                self.local_storage.append(storage)
            elif purpose == 'SYSTEM':
                self.sys_storage = storage
            elif purpose == 'VOIDATA':
                self.voi_storage = storage

    def should_calculate_only_voi(self, service_type):
        return len(service_type) == 1 and service_type[0] == "VOI"

    def calculate_only_voi_storage(self):
        if self.voi_storage:
            return str(utils.storage_type_format(self.voi_storage['size'])) + 'GB'
        sys_storage_size = utils.storage_type_format(self.sys_storage['size'])
        return f'{str(sys_storage_size - 100)}GB'

    def calculate_ceph_storage(self, node_num, service_type, ceph_copy_num_default, pg_all):
        volume_pgp = 0.45
        cephfs_pgp = 0.45

        if len(service_type) == 1 and service_type[0] == "VDI":
            volume_pgp = 0.8
            cephfs_pgp = 0.1

        image_pgp = 0.1
        images_pool = utils.get_near_power(
            int(pg_all * image_pgp / ceph_copy_num_default))
        volume_pool = utils.get_near_power(
            int(pg_all * volume_pgp / ceph_copy_num_default))
        cephfs_pool = utils.get_near_power(
            int(pg_all * cephfs_pgp / ceph_copy_num_default))
        ceph_data_sum = sum(utils.storage_type_format(
            storage['size']) for storage in self.ceph_data_storage)
        ceph_max_size = f'{str(round(ceph_data_sum * 0.8 * node_num / ceph_copy_num_default, 2) )}GB'

        return {
            "commonCustomCeph": {
                "cephCopyNumDefault": ceph_copy_num_default
            },
            "commonCustomPool": {
                "cephfsPoolPgNum": cephfs_pool,
                "cephfsPoolPgpNum": cephfs_pool,
                "imagePoolPgNum": images_pool,
                "imagePoolPgpNum": images_pool,
                "volumePoolPgNum": volume_pool,
                "volumePoolPgpNum": volume_pool
            },
            "storageSizeMax": ceph_max_size
        }

    def calculate_local_storage(self, node_num):
        if self.local_storage:
            local_data_sum = sum(utils.storage_type_format(
                storage['size']) for storage in self.local_storage)
            return f'{str(local_data_sum * node_num)}GB'
        
        sys_storage_size = utils.storage_type_format(self.sys_storage['size'])
        return f'{str(round(sys_storage_size - 200, 2))}GB'

# 个性化pg计算
class ShowRecommendConfig(ReckRecommendConfigCommon):
    def post(self):
        nodes_info = self.get_nodes_from_request()
        ceph_copy_num_default = nodes_info["cephCopyNumDefault"]
        ceph_service_flag = nodes_info['cephServiceFlag']
        local_service_flag = nodes_info['localServiceFlag']
        service_type = nodes_info["serviceType"]
        nodes = nodes_info["nodes"]
        for node in nodes:
            self.classify_disks(node['storages'])

        if self.should_calculate_only_voi(service_type):
            data = {'storageSizeMax': self.calculate_only_voi_storage()}
            return types.DataModel().model(code=0, data=data)

        data = {} 
        if ceph_service_flag:
            if len(nodes) == 1 and len(self.ceph_data_storage) == 1:
                ceph_copy_num_default = 1
            pg_all = len(nodes) * len(self.ceph_data_storage) * 100
            data = self.calculate_ceph_storage(
                len(nodes), service_type, ceph_copy_num_default, pg_all)

        if local_service_flag:
            data['localSizeMax'] = self.calculate_local_storage(1)

        return types.DataModel().model(code=0, data=data)
