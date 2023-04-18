#!/usr/bin/bash
#set -x

upgrade_package_file=$1


function unzip_upgrade_package() {
  if [ -e $upgrade_package_file ]; then
    
    process "unzip_upgrade_package" "成功" true 1 "解压升级包成功"
  else
    process "unzip_upgrade_package" "解压升级包失败" false 1 "解压升级包失败"
    exit 1
  fi
}

# function backup_data() {
#   if []; then

#   else

#   fi
# }

# function deploy_upgrade_program() {
#   if []; then

#   else

#   fi
# }

# 上报所有流程
function all_process() {
  json="{\"en\":\"unzip_upgrade_package\",\"message\":\"\",\"result\":true,\"sort\":0,\"zh\":\"解压升级包\"} 
        {\"en\":\"backup_data\",\"message\":\"\",\"result\":true,\"sort\":1,\"zh\":\"备份数据库\"}
        {\"en\":\"deploy_upgrade_program\",\"message\":\"\",\"result\":true,\"sort\":2,\"zh\":\"执行升级程序\"}
        {\"en\":\"check_env_status\",\"message\":\"\",\"result\":true,\"sort\":3,\"zh\":\"检测环境状态\"}"
  json_list=$(echo "${json}" | jq -s '.')
  echo $json_list > /tmp/upgrade_process_status
  echo ""
}

# 上报中间流程
# json_array=()
function process() {
  json="{\"en\":\"$1\",\"message\":\"$2\",\"result\":$3,\"sort\":$4,\"zh\":\"$5\"}"
  json_array+=("$json")
  json_list=$(echo "${json_array[@]}" | jq -s '.')
  echo "$json_list" > /dev/null
  echo "$json_list" > /tmp/upgrade_now_status
  echo ""
}

all_process
unzip_upgrade_package
