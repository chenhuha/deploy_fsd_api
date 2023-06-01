import yaml
import logging

from flask import current_app
from flask_restful import reqparse, Resource
from common import types, utils
from jinja2 import Template


class DeployPreview(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_preview_from_request(self):
        parser = reqparse.RequestParser()
        parser.add_argument('common', required=True, location='json',
                            type=dict, help='The common field does not exist')
        parser.add_argument('key', required=True, location='json',
                            type=str, help='The key field does not exist')
        parser.add_argument('nodes', required=True, location='json',
                            type=list, help='The nodes field does not exist')
        parser.add_argument('serviceType', required=True, location='json',
                            type=list, help='The serviceType field does not exist')
        parser.add_argument('deployType', required=True, location='json',
                            type=str, help='The deployType field does not exist')
        parser.add_argument('voiDeployType', location='json',
                            type=str, help='The voiDeployType field does not exist')
        return parser.parse_args()


class Preview(Resource, DeployPreview):
    def post(self):
        preview_info = self.get_preview_from_request()
        config_file = self.file_conversion(preview_info)

        return types.DataModel().model(code=0, data=config_file)

    def get(self):
        file_list = ["ceph-globals.yaml", "global_vars.yaml", "hosts"]
        global_vars_data = []
        for file in file_list:
            with open(current_app.config['ETC_EXAMPLE_PATH'] + file, 'r') as f:
                global_vars_data.append({'shellName': file,
                                         'shellContent': f.read()})

        return types.DataModel().model(code=0, data=global_vars_data)

    def file_conversion(self, previews):
        # 生成 global_vars.yaml 文件预览
        commonFixed = previews['common']['commonFixed']
        commonCustom = previews['common']['commonCustom']
        global_var_data = utils.yaml_to_dict(current_app.config['TEMPLATE_PATH'] + '/global_vars.yaml')
        global_var_data['external_vip_address'] = commonFixed['apiVip']
        global_var_data['internal_vip_address'] = f"169.168.{commonFixed['apiVip'].split('.', 2)[-1]}"
        global_var_data['voi_storage_num'] = commonFixed.get('voiResourceSize', 0)
        global_var_data['vdi_storage_num'] = commonFixed.get('blockStorageSize', 0)
        global_var_data['cloud_disk_num'] = commonFixed.get('shareDiskSize', 0)
        global_var_data['net_disk_num'] = commonFixed.get('netDiskSize', 0)
        global_var_data['enable_ceph'] = commonFixed.get('cephServiceFlag', False)
        global_var_data['enable_local'] = commonFixed.get('localServiceFlag', False)
        global_var_data['only_deploy_voi'] = False

        service_type = previews['serviceType']
        if len(service_type) == 1 and service_type[0] == 'VOI':
            fsd_deploy_mode = 'voi'
            global_var_data['only_deploy_voi'] = True
            global_var_data['voi_data_device'] = self.get_voi_data_device(previews)
        elif len(service_type) == 1 and service_type[0] == 'VDI':
            fsd_deploy_mode = 'vdi'
        else:
            fsd_deploy_mode = 'all'
        
        global_var_data['fsd_deploy_mode'] = fsd_deploy_mode 

        if previews['deployType'] == "COMM":
            global_var_data['deploy_comm'] = True
            global_var_data['deploy_edu'] = False
        elif previews['deployType'] == "EASYEDU":
            global_var_data['deploy_comm'] = False
            global_var_data['deploy_edu'] = True
    
        global_var = yaml.dump(global_var_data, sort_keys=False, width=1200)
        global_var_dict = {'shellName': 'global_vars.yaml', 'shellContent': global_var}

        # 生成 hosts 文件预览
        host_vars = {
            'nodeIP': "",
            'nodeName': "",
            'managementCard': "",
            'storagePublicCard': "",
            'storageClusterCard': "",
            'nicInfo': [],
            'flatManagementList': [],
            'vlanManagementDict': {},
            'cephVolumeData': [],
            'cephVolumeCacheData': [],
            'localVolumeData': [],
            'nodeType': []
        }
        nodes_info = []

        for node in previews['nodes']:
            host_vars1 = host_vars | {
                'nodeIP': node['nodeIP'],
                'nodeName': node['nodeName'],
            }
            card_info = self._netcard_classify_build(node['networkCards'])
            storage_info = self._storage_classify_build(node['storages'])

            host_vars1 |= {
                'managementCard': card_info['management'],
                'storagePublicCard': card_info['storagePublic'],
                'storageClusterCard': card_info['storageCluster'],
                'nicInfo': card_info['nic'],
                'flatManagementList': card_info['flat_cards'],
                'vlanManagementDict': card_info['vlan_cards'],
                'cephVolumeData': storage_info['ceph_volume_data'],
                'cephVolumeCacheData': storage_info['ceph_volume_cache_data'],
                'localVolumeData': storage_info['local_volume_data'],
                'nodeType': node['nodeType'],
            }

            nodes_info.append(host_vars1)

        host_file_print = self.host_conversion({'nodes': nodes_info})
        host_var_dict = {'shellName': 'hosts', 'shellContent': host_file_print}

        if commonFixed.get('cephServiceFlag', False):
            ceph_global_var_data = utils.yaml_to_dict(current_app.config['TEMPLATE_PATH'] + '/ceph-globals.yaml')
            ceph_global_var_data['ceph_public_network'] = commonFixed['cephPublic']
            ceph_global_var_data['ceph_cluster_network'] = commonFixed['cephCluster']
            ceph_global_var_data['osd_pool_default_size'] = commonCustom['commonCustomCeph']['cephCopyNumDefault']
            commonCustomPool = commonCustom['commonCustomPool']
            ceph_global_var_data['images_pool_pg_num'] = commonCustomPool['imagePoolPgNum']
            ceph_global_var_data['images_pool_pgp_num'] = commonCustomPool['imagePoolPgpNum']
            ceph_global_var_data['volumes_poll_pg_num'] = commonCustomPool['volumePoolPgNum']
            ceph_global_var_data['volumes_poll_pgp_num'] = commonCustomPool['volumePoolPgpNum']
            ceph_global_var_data['cephfs_pool_default_pg_num'] = commonCustomPool['cephfsPoolPgNum']
            ceph_global_var_data['cephfs_pool_default_pgp_num'] = commonCustomPool['cephfsPoolPgpNum']
            ceph_global_var_data['ceph_aio'] = len(previews['nodes']) == 1
            ceph_global_var_data['bcache'] = self._bcache_bool(previews['nodes'])
            ceph_global_var = yaml.dump(ceph_global_var_data, sort_keys=False)
            ceph_global_var_dict = {'shellName': 'ceph-globals.yaml', 'shellContent': ceph_global_var}

            return [global_var_dict, ceph_global_var_dict, host_var_dict]

        return [global_var_dict, host_var_dict]

    def host_conversion(self, nodes):
        host_template_path = current_app.config['TEMPLATE_PATH'] + '/hosts.j2'
        with open(host_template_path, 'r', encoding='UTF-8') as f:
            data = f.read()
        return Template(data).render(nodes)

    def _bcache_bool(self, nodes):
        bcache = False
        for node in nodes:
            for storage in node['storages']:
                if storage['purpose'] == 'CACHE':
                    bcache = True
                    break
        return bcache

    def _netcard_classify_build(self, cards):
        card_info = {
            'management': "",
            'flat_cards': [],
            'vlan_cards': {},
            'storageCluster': "",
            'storagePublic': "",
            'nic': []
        }

        for card in cards:
            name = card['name']
            purpose = card['purpose']
            bond = card['bond']
            slaves = card['slaves']
            external_ids = card.get('externalIds')

            if 'EXTRANET' in purpose:
                card_info['flat_cards'].append(name)
                if external_ids:
                    card_info['vlan_cards'][name] = external_ids

            if 'MANAGEMENT' in purpose:
                card_info['management'] = name

            if 'STORAGECLUSTER' in purpose:
                card_info['storageCluster'] = name

            if 'STORAGEPUBLIC' in purpose:
                card_info['storagePublic'] = name

            role = 0

            if 'EXTRANET' in purpose:
                role += 4

            if 'MANAGEMENT' in purpose:
                role += 8

            if 'STORAGECLUSTER' in purpose:
                role += 2

            if 'STORAGEPUBLIC' in purpose:
                role += 1

            if bond:
                nic = f"{name}:null:{str(bin(role)[2:].zfill(4))}:{slaves}" if slaves else f"{name}:null:{str(bin(role)[2:].zfill(4))}"
            else:
                nic = f"{name}:null:{str(bin(role)[2:].zfill(4))}"

            if role != 0:
                card_info['nic'].append(nic)

        return card_info

    def _storage_classify_build(self, storages):
        storage_data = {
            'ceph_volume_data': [],
            'ceph_volume_cache_data': [],
            'local_volume_data': []
        }

        for storage in storages:
            purpose = storage['purpose']
            disk_name = '/dev/' + storage['name']

            if purpose == 'CEPH_CACHE':
                cache2data = [f'/dev/{item}' for item in storage['cache2data']]
                storage_data['ceph_volume_cache_data'].append({'cache': disk_name, 'data': ' '.join(cache2data)})
            elif purpose == 'CEPH_DATA':
                storage_data['ceph_volume_data'].append(disk_name)
            elif purpose == 'LOCAL_DATA':
                storage_data['local_volume_data'].append(disk_name)

        return storage_data

    def get_voi_data_device(self, previews):
        for node in previews['nodes']:
            for storage in node['storages']:
                if storage['purpose'] == 'VOIDATA':
                    return '/dev/' + storage['name']
        return ""
