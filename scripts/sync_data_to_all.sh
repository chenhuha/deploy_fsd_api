#!/usr/bin/bash

ip=$1
deploy_home=$2
template_path=$3
ansible_log=$4

function syncData(){
  echo ${ip}--starting--copy-----------------------
  ssh root@${ip} "[ -d ${deploy_home} ] && echo folder ${deploy_home} is exits || mkdir -p ${deploy_home}"
  `scp ${deploy_home}/historyDeploy.yml  root@${ip}:${deploy_home}/historyDeploy.yml`
  echo file is copy to ${ip} ok ${path1}/historyDeploy.yml
  `scp ${deploy_home}/deployDTO.yml  root@${ip}:${deploy_home}/deployDTO.yml`
  echo file is copy to ${ip} ok ${path1}/deployDTO.yml
  `scp ${deploy_home}/netCheckResult.yml  root@${ip}:${deploy_home}/netCheckResult.yml`
  echo file is copy to ${ip} ok ${path1}/netCheckResult.yml

  ssh root@${ip} "[ -d ${template_path} ] && echo folder ${template_path} is exits || mkdir -p ${template_path}"
  `scp ${template_path}/global_vars.yaml root@${ip}:${template_path}/global_vars.yaml`
  echo file is copy to ${ip} ok ${template_path}/global_vars.yaml
  `scp ${template_path}/ceph-globals.yaml root@${ip}:${template_path}/ceph-globals.yaml`
  echo file is copy to ${ip} ok ${template_path}/ceph-globals.yaml
  `scp ${template_path}/hosts root@${ip}:${template_path}/hosts`
  echo file is copy to ${ip} ok ${template_path}/hosts
  `scp ${template_path}/net-check-multinode root@${ip}:${template_path}/net-check-multinode`
  echo file is copy to ${ip} ok ${template_path}/net-check-multinode

  ssh root@${ip} "[ -d ${ansible_log} ] && echo folder ${ansible_log} is exits || mkdir -p ${ansible_log}"
  `scp ${ansible_log}/deploy.log root@${ip}:${ansible_log}/deploy.log`
  echo file is copy to ${ip} ok ${ansible_log}/deploy.log
  echo ${ip}--end--copy-----------------------------
}

syncData
