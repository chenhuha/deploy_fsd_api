import os
import json
import yaml
import subprocess
import time
from openpyxl import load_workbook
from common import types
from deploy.preview import Preview
from flask import current_app
from uuid import uuid1
from threading import Thread
from deploy.status import Status
from deploy.node_base import Node


class DeployScript(Preview, Node):
    def post(self):
        preview_info = self.get_preview_from_request()
        config_file = self.file_conversion(preview_info)
        for config in config_file:
            with open(current_app.config['ETC_EXAMPLE_PATH'] + config['shellName'], 'w', encoding='UTF-8') as f:
                f.write(config['shellContent'])
        self.control_deploy(preview_info)
        return types.DataModel().model(code=0, data="")

    def control_deploy(self, previews):
        if not os.path.exists(current_app.config['DEPLOY_HOME'] + '/historyDeploy.yml'):
            deploy_type = "first"
        else:
            deploy_type = "retry"
        ceph_flag = previews['common']['commonFixed']['cephServiceFlag']
        deploy_key = previews['key']
        deploy_uuid = str(uuid1())
        results = types.DataModel().history_model(
            paramsJson=json.dumps(previews),
            uuid=deploy_uuid,
            startTime=int(time.time() * 1000)
        )
        self._write_history_file(results)
        cmd = ['sh', current_app.config['SCRIPT_PATH'] + '/setup.sh',
            deploy_key, deploy_type, str(ceph_flag), str(deploy_uuid)]
        self._logger.info('deploy command: %s', cmd)
        results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        thread = Thread(target=self._shell_return_listen, args=(
            current_app._get_current_object(), results, previews, deploy_uuid, int(time.time() * 1000)))
        thread.start()

    def _shell_return_listen(self, app, subprocess_1, previews, deploy_uuid, start_time):
        with app.app_context():
            subprocess_1.wait()
            status_results = Status.get_now_list(self)
            end_results = status_results[-1]
            results = types.DataModel().history_model(
                log=str(subprocess_1.stdout.read(), encoding='utf-8'),
                paramsJson=json.dumps(previews),
                uuid=deploy_uuid,
                startTime=start_time,
                message=end_results['message'],
                result=end_results['result']
            )
            self._write_history_file(results)
            self._write_node_info_csv(previews['nodes'])

    def _write_history_file(self, result):
        results_yaml = yaml.dump(result, sort_keys=False, allow_unicode=True)
        with open(current_app.config['DEPLOY_HOME'] + '/historyDeploy.yml', 'w', encoding='UTF-8') as f:
            f.write(results_yaml)

    def _write_node_info_csv(self, nodes):
        book = load_workbook( current_app.config['DEPLOY_HOME'] + '/deploy_node_info.xlsx')
        template_sheet = book['mould']
        for node in nodes:
            target_sheet = book.copy_worksheet(template_sheet)
            target_sheet.title = node['nodeName']
            target_sheet.cell(row=3, column=1, value=node['nodeName'])
            target_sheet.cell(row=3, column=2, value=node['nodeIP'])
            target_sheet.cell(
                row=3, column=3, value=','.join(node['nodeType']))
            target_sheet.cell(row=3, column=4, value='0.0.0.0')
            net_info = self._net_info(node['networkCards'])
            self._write_info_csv(net_info, target_sheet, 3, 6)
            hdd_info, ssd_info = self._storages_info(node['storages'])
            self._write_info_csv(hdd_info, target_sheet, 3, 16)
            self._write_info_csv(ssd_info, target_sheet, 3, 22)

        book.save(current_app.config['DEPLOY_HOME'] + '/deploy_node_info.xlsx')
        book.close()

    def _write_info_csv(self, infos, sheet, start_row, start_col):
        for row, info in enumerate(infos, start=start_row):
            for col, value in enumerate(info, start=start_col):
                sheet.cell(row=row, column=col, value=value)

    def _net_info(self, cards):
        cards_list = []
        for card in cards:
            purpose = []
            if 'EXTRANET' in card['purpose']:
                purpose.append("业务网")
            if 'MANAGEMENT' in card['purpose']:
                purpose.append("管理网")
            if 'STORAGECLUSTER' in card['purpose']:
                purpose.append("存储集群网")
            if 'STORAGEPUBLIC' in card['purpose']:
                purpose.append("存储公网")
            cards_list.append([card['name'], card.get('ip', 'null'), ','.join(
                purpose), card['bond'], card['speed'], card.get('mode', 'null'), card.get('mtu', 'null'), card.get('pciid', 'null'), card.get('slaves', 'null')
            ])
        return cards_list

    def _storages_info(self, storages):
        hdd_storages_info = []
        ssd_storages_info = []
        storage_load_dict = self._load_storage()
        for storage in storages:
            if storage_load_dict:
                _bool, storgae_info = self._ssd_bool(
                    storage['name'], storage_load_dict)
            else:
                _bool = False
                storgae_info = {}
            if _bool:
                ssd_storages_info.append([
                    storage['name'],
                    self._storage_purpose_convert(storage['purpose']),
                    storage['size'],
                    storgae_info.get('model', 'null'),
                    storgae_info.get('partition', '[]'),
                    str(storage['cache2data'])
                ])
            else:
                hdd_storages_info.append([
                    storage['name'],
                    self._storage_purpose_convert(storage['purpose']),
                    storage['size'],
                    storgae_info.get('model', 'null'),
                    storgae_info.get('partition', '[]')
                ])
        return hdd_storages_info, ssd_storages_info

    def _storage_purpose_convert(self, purpose):
        if purpose == "SYSTEM":
            return "系统盘"
        elif purpose == "DATA":
            return "ceph数据盘"
        elif purpose == "CACHE":
            return "ceph缓存盘"
        elif purpose == "VOIDATA":
            return "VOI数据盘"

    def _ssd_bool(self, name, storage_load_dict):
        for node in storage_load_dict:
            for ssd in node['ssds']:
                if name == ssd.get('name'):
                    return True, ssd
            for hdd in node['hdds']:
                if name == hdd.get('name'):
                    return False, hdd
        return False, {}

    def _load_storage(self):
        try:
            with (open(current_app.config['DEPLOY_HOME'] + '/load.json', 'r')) as f:
                data = f.read()
            return json.loads(data)
        except Exception as e:
            self._logger.error(
                f"Faild open {current_app.config['DEPLOY_HOME'] + '/load.json'} and to json ,Because: {e}")
            return []
