#!/usr/bin/bash

set -e

node_address=$1
node_info=`ansible -i "$node_address," all -m setup|sed 1c\{`
root_device=""
index=0
while [ "$root_device" == "" ]
do
    mount_dir=$(echo $node_info|jq ".ansible_facts.ansible_mounts[$index].mount")
    if [ $mount_dir == '"/"' ]; then
        root_device=`echo $node_info|jq ".ansible_facts.ansible_mounts[$index].device"`
    fi
    index=`expr $index + 1`
    if [ $index -gt 200 ]; then
        echo "没有找到根目录： '/' 的挂载设备"
        exit 10
    fi
done
root_device=$(echo $root_device|awk -F'/' '{print $NF}'|awk -F'"' '{print $1}')

sys_disk=""
index=0
for disk in `ssh $node_address "lsblk -d"|grep -v "rbd"|grep "disk"|awk '{print $1}'`
do
    res=`echo "$root_device"|grep "$disk"|wc -l`
    if [ $res -eq 1 ]; then
        sys_disk=$disk
        break
    fi
    part=`echo $node_info|jq ".ansible_facts.ansible_devices.$disk.partitions"`
    if [ "$part" != "{}" ]; then
        while [ "$sys_disk" == "" ]
        do
            num=`echo $part|jq ".$disk$index.holders"|wc -l`
            if [ $num -gt 1 ]; then
                for holder in `echo $part|jq ".$disk$index.holders"`
                do
                    striped_holder=`echo $holder|awk -F'"' '{print $2}'`
                    if [ "$striped_holder" == "$root_device" ]; then
                        sys_disk=$disk
                        break
                    fi
                done
            fi
            index=`expr $index + 1`
            if [ $index -gt 5 ]; then
                break
            fi
        done
        if [ "$sys_disk" != "" ]; then
            break
        fi
    fi
done
echo $sys_disk