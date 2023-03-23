from jinja2 import Template

import subprocess

# 替换 yaml 文件中的值
def render_config(filename, data_dirt):
    with open(filename, 'r') as file:
        config = file.read()
    rendered_config = Template(config).render(data_dirt)
    return rendered_config

# 取最接近的2的幂次结果
def getNearPower(target):
    powers = [2, 4, 8, 16, 32, 64, 128, 256, 512,
              1024, 2048, 4096, 8192, 16384, 32768, 65536]
    index = abs(target - powers[0])
    result = powers[0]
    for i in powers:
        abs_diff = abs(target - i)
        if abs_diff <= index:
            index = abs_diff
            result = i
    return result

# 执行 shell 命令
def execute(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    exit_code = process.returncode
    return exit_code, output.decode('utf-8'), error.decode('utf-8')
