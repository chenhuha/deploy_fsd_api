import yaml

from flask import current_app
from flask_restful import reqparse, Resource
from common import types, utils
from jinja2 import Template


class DeployPreview(object):
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
        # global_var.yml文件预览
        commonFixed = previews['common']['commonFixed']
        commonCustom = previews['common']['commonCustom']
        commonCustomPool = commonCustom['commonCustomPool']
        global_var_data = utils.yaml_to_dict(
            current_app.config['TEMPLATE_PATH'] + '/global_vars.yaml')
        global_var_data['external_vip_address'] = commonFixed['apiVip']
        internal_vip_address = '169.168' + '.' + str(int(commonFixed['apiVip'].rsplit(
            '.', 2)[-2])) + '.' + str(int(commonFixed['apiVip'].rsplit('.', 2)[-1]) - 1)
        global_var_data['internal_vip_address'] = internal_vip_address
        global_var_data['voi_storage_num'] = commonFixed['voiResourceSize']
        global_var_data['vdi_storage_num'] = commonFixed['blockStorageSize']
        global_var_data['vdi_storage_num'] = commonFixed['shareDiskSize']
        global_var_data['enable_ceph'] = commonFixed['cephServiceFlag']
        if previews['deployType'] == "COMM":
            global_var_data['deploy_comm'] = True
            global_var_data['deploy_edu'] = False
        elif previews['deployType'] == "EASYEDU":
            global_var_data['deploy_comm'] = False
            global_var_data['deploy_edu'] = True
        if len(previews['serviceType']) == 1 and previews['serviceType'][0] == "VOI":
            global_var_data['only_deploy_voi'] = True
        else:
            global_var_data['only_deploy_voi'] = False
        global_var_data['fsd_voi_version'] == previews['voiDeployType']
        global_var = yaml.dump(global_var_data, sort_keys=False, width=1200)
        global_var_dict = {'shellName': 'global_vars.yaml',
                           'shellContent': global_var}

        # ceph_global_var.yml文件预览
        ceph_global_var_data = utils.yaml_to_dict(
            current_app.config['TEMPLATE_PATH'] + '/ceph-globals.yaml')
        ceph_global_var_data['ceph_public_network'] = commonFixed['cephPublic']
        ceph_global_var_data['ceph_cluster_network'] = commonFixed['cephCluster']
        ceph_global_var_data['osd_pool_default_size'] = commonCustom['commonCustomCeph']['cephCopyNumDefault']
        ceph_global_var_data['images_pool_pg_num'] = commonCustomPool['imagePoolPgNum']
        ceph_global_var_data['images_pool_pgp_num'] = commonCustomPool['imagePoolPgpNum']
        ceph_global_var_data['volumes_poll_pg_num'] = commonCustomPool['volumePoolPgNum']
        ceph_global_var_data['volumes_poll_pgp_num'] = commonCustomPool['volumePoolPgpNum']
        ceph_global_var_data['cephfs_pool_default_pg_num'] = commonCustomPool['cephfsPoolPgNum']
        ceph_global_var_data['cephfs_pool_default_pgp_num'] = commonCustomPool['cephfsPoolPgpNum']
        ceph_global_var_data['ceph_aio'] = self._aio_bool(previews['nodes'])
        ceph_global_var_data['bcache'] = self._bcache_bool(previews['nodes'])
        ceph_global_var = yaml.dump(ceph_global_var_data, sort_keys=False)
        ceph_global_var_dict = {
            'shellName': 'ceph-globals.yaml', 'shellContent': ceph_global_var}

        # host 文件预览
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
            'nodeType': []
        }
        nodes_info = []
        for node in previews['nodes']:
            host_vars1 = host_vars.copy()
            host_vars1['nodeIP'] = node['nodeIP']
            host_vars1['nodeName'] = node['nodeName']
            card_info = self._netcard_classify_build(node['networkCards'])
            host_vars1['managementCard'] = card_info['management']
            host_vars1['storagePublicCard'] = card_info['storagePublic']
            host_vars1['storageClusterCard'] = card_info['storageCluster']
            host_vars1['nicInfo'] = card_info['nic']
            host_vars1['flatManagementList'] = card_info['flat_cards']
            host_vars1['vlanManagementDict'] = card_info['vlan_cards']
            storage_info = self._storage_classify_build(node['storages'])
            host_vars1['cephVolumeData'] = storage_info['ceph_volume_data']
            host_vars1['cephVolumeCacheData'] = storage_info['ceph_volume_ceph_data']
            host_vars1['nodeType'] = node['nodeType']
            nodes_info.append(host_vars1)
        host_file_print = self.host_conversion({'nodes': nodes_info})
        host_var_dict = {'shellName': 'hosts', 'shellContent': host_file_print}

        return [global_var_dict, ceph_global_var_dict, host_var_dict]

    def host_conversion(self, nodes):
        host_template_path = current_app.config['TEMPLATE_PATH'] + '/hosts.j2'
        with open(host_template_path, 'r', encoding='UTF-8') as f:
            data = f.read()
        vars = Template(data).render(nodes)
        return vars

    def _aio_bool(self, nodes):
        aio = False
        if len(nodes) == 1:
            for node in nodes:
                if len(node['storages']) == 1:
                    aio = True
                    break
        return aio

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
        card_nic_dict = {
            'name': "",
            'role': 0,
            'salve': ""
        }
        cards_nic_list = []
        for card in cards:
            card_nic = card_nic_dict.copy()
            card_nic['name'] = card['name']
            if 'EXTRANET' in card['purpose']:
                card_nic['role'] += 4
                if card['flat']:
                    card_info['flat_cards'].append(card['name'])
                if card['vlan']:
                    card_info['vlan_cards'][card['name']] = card['externalIds']
            if 'MANAGEMENT' in card['purpose']:
                card_nic['role'] += 8
                card_info['management'] = card['name']
            if 'STORAGECLUSTER' in card['purpose']:
                card_nic['role'] += 2
                card_info['storageCluster'] = card['name']
            if 'STORAGEPUBLIC' in card['purpose']:
                card_nic['role'] += 1
                card_info['storagePublic'] = card['name']
            if card['bond']:
                card_nic['salve'] = card['slaves']
            cards_nic_list.append(card_nic)
        for cards_nic in cards_nic_list:
            if cards_nic['role'] != 0:
                if cards_nic['salve'] == '':
                    card_info['nic'].append("{}:null:{}".format(
                        cards_nic['name'], str(bin(cards_nic['role'])[2:].zfill(4))))
                else:
                    card_info['nic'].append("{}:null:{}:{}".format(
                        cards_nic['name'], str(bin(cards_nic['role'])[2:].zfill(4)), cards_nic['salve']))

        return card_info

    def _storage_classify_build(self, storages):
        storage_data = {
            'ceph_volume_data': [],
            'ceph_volume_ceph_data': []
        }
        for storage in storages:
            if storage['purpose'] == 'DATA':
                storage_data['ceph_volume_data'].append(
                    '/dev/' + storage['name'])
            elif storage['purpose'] == 'CACHE':
                storage['cache2data'] = [
                    '/dev/' + item for item in storage['cache2data']]
                storage_data['ceph_volume_ceph_data'].append(
                    {'cache': '/dev/' + storage['name'], 'data': ' '.join(storage['cache2data'])})
        return storage_data
