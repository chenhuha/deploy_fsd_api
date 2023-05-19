#!/usr/bin/bash
#set -x

sqlite3 /root/deploy/kly-deploy.db <<EOF
DELETE FROM upgrade_process_status;
DELETE FROM upgrade_now_status;
INSERT INTO upgrade_process_status(en, message, result, sort, zh) VALUES ("unzip_upgrade_package", "", "true", 0, "解压升级包");
INSERT INTO upgrade_process_status(en, message, result, sort, zh) VALUES ("backup_data", "", "true", 1, "备份数据库");
INSERT INTO upgrade_process_status(en, message, result, sort, zh) VALUES ("deploy_upgrade_program", "", "true", 2, "执行升级程序");
INSERT INTO upgrade_process_status(en, message, result, sort, zh) VALUES ("check_service_status", "", "true", 3, "检测环境状态");
EOF
