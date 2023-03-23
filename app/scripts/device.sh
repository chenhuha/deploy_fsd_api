#!/usr/bin/bash
#set -x

#输入参数
host_ip=$1

#临时变量
ansible_json=""
result_json='{"framework":"","cpuNum":"","projectName":"","projectVersion":"","nodeName":"","extendIP":"","networks":[],"storages":[],"physics":[]}'

#0.检测参数
function check_param() {
  if [ ! -n "$host_ip" ]; then
    echo "缺少必要参数，例如: bash device.sh.sh [host_ip]"
    exit
  fi
}
# 获取带外ip  ipmitool lan print | grep 'IP Address'| awk '{print $NF}' | awk 'END  {print}'
function getExtendIP() {
  extendIP=`ssh "$host_ip" "ipmitool lan print" | grep 'IP Address' | awk '{print $NF}' | awk 'END {print}'`
  result_json=`echo $result_json | jq --arg v "$extendIP" '.extendIP=$v'`
}

#1.获得ansible_json
function get_json() {
  ansible_json=`ansible -i "$host_ip," all -m setup | sed 1c\{`
}

#2.获得节点信息
function get_node_info() {
  framework=`echo $ansible_json | jq ".ansible_facts.ansible_architecture" | xargs`
  cpuNum=`echo $ansible_json | jq ".ansible_facts.ansible_processor_vcpus" | xargs`
  projectName=`echo $ansible_json | jq ".ansible_facts.ansible_product_name" | xargs`
  projectVersion=`echo $ansible_json | jq ".ansible_facts.ansible_product_version" | xargs`
  nodeName=`echo $ansible_json | jq ".ansible_facts.ansible_hostname" | xargs`
  result_json=`echo $result_json | jq --arg v "$framework" '.framework=$v'`
  result_json=`echo $result_json | jq --arg v "$cpuNum" '.cpuNum=$v'`
  result_json=`echo $result_json | jq --arg v "$projectName" '.projectName=$v'`
  result_json=`echo $result_json | jq --arg v "$projectVersion" '.projectVersion=$v'`
  result_json=`echo $result_json | jq --arg v "$nodeName" '.nodeName=$v'`
}

#3.获得网卡信息
function get_network_info() {
  bonds=`ssh "$host_ip" "ls -l /sys/class/net/" | grep 'bond' | grep -0v "bonding_masters" | awk '{print $NF}' | awk -F/ '{print $NF}'`
  physics=`ssh "$host_ip" "ls -l /sys/class/net/" | egrep -v 'virtual|total' | awk '{print $NF}' | awk -F/ '{print $NF}' | grep -v "bonding_masters" | grep -vw "0"`
  #echo $bonds
  #echo $physics
  physics_array=(${physics})
  bonds_array=(${bonds})
  for bond in ${bonds_array[@]}; do
    bond_of_physicses=`echo $ansible_json | jq ".ansible_facts.ansible_$bond.slaves[]"`
    #echo $bond_of_physicses
    bond_of_physicses_array=(${bond_of_physicses})
    for bond_of_physics in ${bond_of_physicses_array[@]}; do
       bond_of_physics_format=`echo $bond_of_physics | xargs`
       for i in ${!physics_array[@]}; do
         if [ "${physics_array[$i]}" = "$bond_of_physics_format" ]; then
           unset physics_array[$i]
         fi
       done
    done
  done
  all_array=(${physics_array[@]} ${bonds_array[*]})
  jj=0
  for j in ${!all_array[@]}; do
    active=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.active" | xargs`
    if [ "$active" = "true" ]; then
      temp_json='{"name":"","isbond":"","speed":"","mac":"","mode":"","mtu":"","pciid":"","slaves":"","ip":""}'
      isbond=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.type" | xargs`
      speed=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.speed" | xargs`
      mac=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.macaddress" | xargs`
      mode=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.mode" | xargs`
      mtu=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.mtu" | xargs`
      pciid=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.pciid" | xargs`
      slaves=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.slaves" | xargs`
      ip=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.ipv4.address" | xargs`
      ip_secondaries=`echo $ansible_json | jq ".ansible_facts.ansible_${all_array[$j]}.ipv4_secondaries[].address" | xargs`
      all_ip="$ip $ip_secondaries"
      temp_json=`echo $temp_json | jq --arg v "${all_array[$j]}" '.name=$v'`
      temp_json=`echo $temp_json | jq --arg v "$isbond" '.isbond=$v'`
      temp_json=`echo $temp_json | jq --arg v "$speed" '.speed=$v'`
      temp_json=`echo $temp_json | jq --arg v "$mac" '.mac=$v'`
      temp_json=`echo $temp_json | jq --arg v "$mode" '.mode=$v'`
      temp_json=`echo $temp_json | jq --arg v "$mtu" '.mtu=$v'`
      temp_json=`echo $temp_json | jq --arg v "$pciid" '.pciid=$v'`
      temp_json=`echo $temp_json | jq --arg v "$slaves" '.slaves=$v'`
      temp_json=`echo $temp_json | jq --arg v "$ip" '.ip=$v'`
      result_json=`echo $result_json | jq --arg index "$jj" --argjson json "$temp_json" '.networks[$index|tonumber]=$json'`
      ((jj++))
    fi
  done
  kk=0
  physics_array2=(${physics})
  for k in ${!physics_array2[@]}; do
    active=`echo $ansible_json | jq ".ansible_facts.ansible_${physics_array2[$k]}.active" | xargs`
    if [ "$active" = "true" ]; then
      result_json=`echo $result_json | jq --arg index "$kk" --arg v "${physics_array2[$k]}" '.physics[$index|tonumber]=$v'`
      ((kk++))
    fi
  done
}

#4.获得存储信息
function get_storage_info() {
  temp_json='{"name":"","size":"","model":"","partition":"","ishdd":"","issystem":""}'
  storages=`ssh "$host_ip" "lsblk -d" | grep "disk" | grep -v "rbd" | awk '{print $1}'`
  system_disk=`bash /root/kly-deploy/DeployFSD/scripts $host_ip`
  #echo $storages
  storages_array=(${storages})
  for i in ${!storages_array[@]}; do
    size=`echo $ansible_json | jq ".ansible_facts.ansible_devices.${storages_array[$i]}.size" | xargs`
    model=`echo $ansible_json | jq ".ansible_facts.ansible_devices.${storages_array[$i]}.model" | xargs`
    partition=`echo $ansible_json | jq -c ".ansible_facts.ansible_devices.${storages_array[$i]}.partitions" | jq 'keys' | xargs`
    ishdd=`echo $ansible_json | jq ".ansible_facts.ansible_devices.${storages_array[$i]}.rotational" | xargs`
    temp_json=`echo $temp_json | jq --arg v "${storages_array[$i]}" '.name=$v'`
    temp_json=`echo $temp_json | jq --arg v "$size" '.size=$v'`
    temp_json=`echo $temp_json | jq --arg v "$model" '.model=$v'`
    temp_json=`echo $temp_json | jq --arg v "$partition" '.partition=$v'`
    temp_json=`echo $temp_json | jq --arg v "$ishdd" '.ishdd=$v'`
    if [ "${storages_array[$i]}" = "$system_disk" ]; then
      temp_json=`echo $temp_json | jq --arg v "1" '.issystem=$v'`
    else
      temp_json=`echo $temp_json | jq --arg v "0" '.issystem=$v'`
    fi
    result_json=`echo $result_json | jq --arg index "$i" --argjson json "$temp_json" '.storages[$index|tonumber]=$json'`
  done
  echo $result_json
}

#5.输出设备信息
function print_info() {
  echo "device is $result_json"
}

#Main function
check_param
getExtendIP
get_json
get_node_info
get_network_info
get_storage_info
#print_info