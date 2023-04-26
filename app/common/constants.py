
# 检验节点 命令 
COMMAND_CHECK_NODE = 'sshpass -p %s ssh root@%s -o StrictHostKeyChecking=no "echo 123"'

# 免密 命令 
COMMAND_SSH_COPY_ID = 'sshpass -p %s ssh-copy-id -o StrictHostKeyChecking=no root@%s'

# 创建免密证书 命令
COMMAND_CREATE_SSH_KEYGEN = 'ssh-keygen -t rsa -b 4096 -N "" -f /root/.ssh/id_rsa'

# 删除免密证书 命令
COMMAND_DELETE_SSH_KEYGEN = 'rm -f /root/.ssh/id_rs*'

# 检验节点 命令 结果
COMMAND_CHECK_NODE_SUCCESS = '123'

# 免密 命令 结果
COMMAND_SSH_COPY_ID_SUCCESS = 'Number of key(s) added: 1'

# 免密 命令 结果
COMMAND_SSH_COPY_ID_EXIST = 'All keys were skipped because they already exist on the remote system.'


# ansible 前置环境部署
COMMAND_ANSIBLE_PREPER_DEPLOY = 'ansible -i %s -e @%s -e @%s %s'

# scp命令
COMMAND_SCP_FILE = 'sshpass -p %s scp -o StrictHostKeyChecking=no -r %s %s@%s:%s'

# 数据库备份命令
COMMAND_MYSQL_DUMP = 'docker exec mariadb mysqldump -u%s -p%s -h %s --all-databases --single-transaction > %s'

# tar解压命令
COMMAND_TAR_UNZIP = 'tar zxf %s -C %s'