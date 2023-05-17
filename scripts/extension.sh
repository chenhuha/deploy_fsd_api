#!/usr/bin/bash
#set -x

#输入参数
deploy_ceph_flag=$1
upgrade_path=$2

deploy_path=/root/deploy
etc_example_path=${deploy_path}/kly-deploy/etc_example
ansible_path=${deploy_path}/kly-deploy/ansible
ceph_ansible_path=${deploy_path}/kly-deploy/ceph-ansible
upgrade_etc_example_path=${upgrade_path}/kly-deploy/etc_example
#0.检测参数
function check_param() {
  if  [ ! -n "$deploy_ceph_flag" ]; then
    echo "缺少必要参数，例如: bash extension.sh [deploy_ceph_flag, True|False]"
    exit 1
  fi
}

#1.执行部署
function deploy() {
    #发送webhook
    webhook_all_process
    #准备部署环境
    ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/global_vars.yaml ${ansible_path}/94-internal_ip.yaml > /var/log/deploy/deploy.log 2>&1
    if ! [ "$(grep 'failed=' /var/log/deploy/deploy.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
      webhook_process "ready_environment" "准备部署环境失败" "false" 1 "准备部署环境"
      exit 1
    fi
    ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/ceph-globals.yaml -e @${etc_example_path}/global_vars.yaml ${ansible_path}/91-prepare.yaml >> /var/log/deploy/deploy.log 2>&1
    if [ "$(grep 'failed=' /var/log/deploy/deploy.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
      webhook_process "ready_environment" "成功" "true" 1 "准备部署环境"
    else
      webhook_process "ready_environment" "准备部署环境失败" false 1 "准备部署环境"
      exit 1
    fi

    #部署文件系统
    if [ "$deploy_ceph_flag" = "True" ]; then
      ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/ceph-globals.yaml -e @${etc_example_path}/global_vars.yaml ${ceph_ansible_path}/ceph-deploy.yaml >> /var/log/deploy/deploy.log 2>&1
      if [ "$(grep 'failed=' /var/log/deploy/deploy.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
        webhook_process "deploy_ceph" "成功" "true" 2 "部署文件系统"
      else
        webhook_process "deploy_ceph" "部署文件系统失败" "false" 2 "部署文件系统"
        exit 1
      fi
    else
      webhook_process "deploy_ceph" "成功" "true" 2 "部署文件系统"
    fi

    #部署虚拟化系统
    if [ -n "$upgrade_path" ]; then
      ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/ceph-globals.yaml -e @${etc_example_path}/global_vars.yaml -e @${upgrade_etc_example_path}/upgrade-globals.yaml ${ansible_path}/90-setup.yaml >> /var/log/deploy/deploy.log 2>&1
    else
      ansible-playbook -i ${etc_example_path}/hosts -e @${etc_example_path}/ceph-globals.yaml -e @${etc_example_path}/global_vars.yaml ${ansible_path}/90-setup.yaml >> /var/log/deploy/deploy.log 2>&1
    fi
    
    if [ "$(grep 'failed=' /var/log/deploy/deploy.log | awk '{print $6}' | awk -F '=' '{print $2}' | awk '$1 != 0')" = "" ] ; then
      webhook_process "deploy_trochilus" "成功" "true" 3 "部署虚拟化系统"
    else
      webhook_process "deploy_trochilus" "部署虚拟化系统失败" false 3 "部署虚拟化系统"
      exit 1
    fi
    exit 0
}

function webhook_all_process() {
  #所有流程
sqlite3 /root/deploy/kly-deploy.db <<EOF
    DELETE FROM deploy_process_status;
    DELETE FROM deploy_now_status;
    INSERT INTO deploy_process_status(en, message, result, sort, zh) VALUES ("check_param", "", "true", 0, "检测部署脚本");
    INSERT INTO deploy_process_status(en, message, result, sort, zh) VALUES ("ready_environment", "", "true", 1, "准备部署环境");
    INSERT INTO deploy_process_status(en, message, result, sort, zh) VALUES ("ready_environment", "", "true", 2, "部署文件系统");
    INSERT INTO deploy_process_status(en, message, result, sort, zh) VALUES ("deploy_trochilus", "", "true", 3, "部署虚拟化系统");
EOF

  #补发前1步
  webhook_process "check_param" "成功" true 0 "检测部署脚本"
}

# 上报中间流程
function webhook_process() {
  echo "('$1', '$2', '$3', $4, '$5')"
  sqlite3 /root/deploy/kly-deploy.db "INSERT INTO deploy_now_status(en, message, result, sort, zh) VALUES ('$1', '$2', '$3', $4, '$5');"
}

#Main function
check_param
deploy
