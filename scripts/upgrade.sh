#!/usr/bin/bash
#set -x

upgrade_path=$1

deploy_path=/root/deploy
deploy_etc_example_path=${deploy_path}/kly-deploy/etc_example
upgrade_etc_example_path=${upgrade_path}/kly-deploy/etc_example
upgrade_ansible_path=${upgrade_path}/kly-deploy/ansible
ceph_ansible_path=${deploy_path}/kly-deploy/ceph-ansible


# 检测参数
function check_param() {
  if  [[ ! -n "$upgrade_path" ]]; then
    echo "缺少必要参数，例如: bash upgrade.sh [upgrade_path, /opt/upgrade_resource_v2.1.0]"
    exit 1
  fi
}

# Deployment Platform upgrade
function deploy_platform_upgrade() {
  mv ${deploy_path}/kly-deploy-api ${deploy_path}/kly-deploy-api_$(date +%s)
  cp -r ${upgrade_path}/kly-deploy-api ${deploy_path}/kly-deploy-api
  if [ -d "${deploy_path}/kly-deploy-api" ]; then
    systemctl daemon-reload && systemctl restart kly-deploy-api
    status=$(systemctl is-active kly-deploy-api)
    if [[ ! "$status" == "active" ]]; then
       process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
       exit 1
    fi
  else
    process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
    exit 1
  fi
}


# Deploying front-end upgrade
function deploy_front_upgrade(){
  mv /var/www/html /var/www/html_$(date +%s)
  cp -r ${upgrade_path}/html /var/www/
  if [ -d "${upgrade_path}/html" ]; then
    systemctl restart httpd
    status=$(systemctl is-active httpd)
    if [[ ! "$status" == "active" ]]; then
       process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
       exit 1
    fi
  else
    process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
    exit 1
  fi
}

# Service upgrade
function deploy_upgrade_program() { 
  # 服务升级
  ansible-playbook -i ${deploy_etc_example_path}/hosts -e @${deploy_etc_example_path}/ceph-globals.yaml -e @${deploy_etc_example_path}/global_vars.yaml -e @${upgrade_etc_example_path}/upgrade-globals.yaml ${upgrade_ansible_path}/95-upgrade.yaml> /var/log/deploy/upgrade.log 2>&1
  if [ "$(grep 'failed=' /var/log/deploy/upgrade.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
    process "deploy_upgrade_program" "" true 2 "deploy_upgrade_program"
  else
    process "deploy_upgrade_program" "执行升级程序失败" false 2 "deploy_upgrade_program"
    exit 1
  fi
}

function check_service_status() {
  ports=(9000 9001 9002 9003 9010 9090 9093)

  for port in "${ports[@]}"
  do
    if ! netstat -an | grep -w "$port" >/dev/null
    then
      process "check_service_status" "Port $port is not in use" false 3 "check_service_status"
      exit 1
    fi
  done
  process "check_service_status" "" true 3 "check_service_status"
}

# 上报所有流程
function all_process() {
  json="{\"en\":\"unzip_upgrade_package\",\"message\":\"\",\"result\":true,\"sort\":0,\"zh\":\"解压升级包\"} 
        {\"en\":\"backup_data\",\"message\":\"\",\"result\":true,\"sort\":1,\"zh\":\"备份数据库\"}
        {\"en\":\"deploy_upgrade_program\",\"message\":\"\",\"result\":true,\"sort\":2,\"zh\":\"执行升级程序\"}
        {\"en\":\"check_service_status\",\"message\":\"\",\"result\":true,\"sort\":3,\"zh\":\"检测环境状态\"}"
  json_list=$(echo "${json}" | jq -s '.')
  echo $json_list > /tmp/upgrade_process_status
  echo ""
}

# 上报中间流程
function process() {
  json="{\"en\":\"$1\",\"message\":\"$2\",\"result\":$3,\"sort\":$4,\"zh\":\"$5\"}"
  json_array+=("$json")
  json_list=$(echo "${json_array[@]}" | jq -s '.')
  echo "$json_list" > /dev/null
  echo "$json_list" > /tmp/upgrade_now_status
  echo ""
}

check_param
all_process
process "unzip_upgrade_package" "" true 0 "解压升级包成功"
process "backup_data" "" true 1 "备份数据库成功"

deploy_upgrade_program
check_service_status
