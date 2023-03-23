
# 检验节点 命令 
COMMAND_CHECK_NODE = 'sshpass -p %s ssh root@%s -o StrictHostKeyChecking=no "echo 123"'

# 免密 命令 
COMMAND_SSH_COPY_ID = 'sshpass -p {password} ssh-copy-id root@{ip} -o StrictHostKeyChecking=no'

# 创建免密证书 命令
COMMAND_CREATE_SSH_KEYGEN = 'ssh-keygen -t rsa -N '' -P '' -f /root/.ssh/id_rsa'

# 删除免密证书 命令
COMMAND_DELETE_SSH_KEYGEN = 'rm -f /root/.ssh/id_rs*'

# 检验节点 命令 结果
COMMAND_CHECK_NODE_SUCCESS = '123'

# 免密 命令 结果
COMMAND_SSH_COPY_ID_SUCCESS = 'Number of key(s) added: 1'

# 免密 命令 结果
COMMAND_SSH_COPY_ID_EXIST = 'All keys were skipped because they already exist on the remote system.'
