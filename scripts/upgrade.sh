#!/usr/bin/bash
#set -x

upgrade_path=$1
version=$2

deploy_path=/root/deploy
etc_example_path=${deploy_path}/kly-deploy/etc_example
ansible_path=${upgrade_package_path}/upgrade_resource/kly-deploy/ansible
ceph_ansible_path=${deploy_path}/kly-deploy/ceph-ansible


# 检测参数
function check_param() {
  if  [ ! -n "$upgrade_path" || ! -n "$version" ]; then
    echo "缺少必要参数，例如: bash upgrade.sh [upgrade_path, /opt/upgrade_resource_v2.1.0] [version, v2.1.0]"
    exit 1
  fi
}

function deploy_upgrade_program() { 
  # 部署平台升级
  mv ${deploy_path}/kly-deploy-api ${deploy_path}/kly-deploy-api_${version}
  cp -r ${upgrade_path}/kly-deploy-api ${deploy_path}/kly-deploy-api
  if [ -d "${deploy_path}/kly-deploy-api" ]; then
    systemctl daemon-reload && systemctl restart kly-deploy-api
  else
    process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
    exit 1
  fi

  # 服务升级
  ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/ceph-globals.yaml -e @${etc_example_path}/global_vars.yaml ${ansible_path}/95-upgrade.yaml>> /var/log/upgrade.log 2>&1
  if [ "$(grep 'failed=' /var/log/deploy.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
    process "deploy_upgrade_program" "升级程序执行成功" true 2 "执行升级程序"
  else
    process "deploy_upgrade_program" "执行升级程序失败" false 2 "执行升级程序"
    exit 1
  fi
}

function check_service_status() {
  ports=(9000 9001 9002 9003 9010 9012 9019 9020 9090 9093)

  for port in "${ports[@]}"
  do
    if ! netstat -an | grep -w "$port" >/dev/null
    then
      process "check_service_status" "Port $port is not in use" false 3 "检测环境状态失败"
      exit 1
    fi
  done
  process "check_service_status" "检测环境状态成功" true 3 "检测环境状态成功"
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
process "unzip_upgrade_package" "成功" true 0 "解压升级包成功"
process "backup_data" "成功" true 1 "备份数据库成功"
deploy_upgrade_program
check_service_status
