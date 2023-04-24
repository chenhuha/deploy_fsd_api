from jinja2 import Template

import subprocess, re

import yaml, json

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

# 单位换算
def storagetypeformat(init_value, reduced_unit='G'):
    """ 单位换算
    :param init_value: 将要换算的原始数字及单位,e.g: 1.2T.
    :param reduced_unit: 将要换算的单位,e.g: G.
    """
    init_num = re.match(r'\d+\.*\d*', init_value)
    init_unit = re.search(r'[A-z]+', init_value).group()
    if not init_num:
        raise ValueError("Error in passing parameters: The number in the "
                         "passed argumentis empty{},\n"
                         "Please use:e.g: 1.2T,10TB".format(init_value))
    symbols_list = ['B', 'K', 'M', 'G', 'T', 'P', 'E',
                    'Bib', 'Kib', 'Mib', 'Gib', 'Tib', 'Pib', 'Eib',
                    'Kb', 'Mb', 'Gb', 'Tb', 'Pb', 'Eb',
                    'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    reduced_num = float(init_num.group())
    if init_unit.capitalize() not in symbols_list or \
            reduced_unit.capitalize() not in symbols_list:
        raise ValueError("This unit is ERROR. Confirm that the unit "
                         "is one of the following:{}".format(symbols_list))
    for serial, symbols in enumerate(symbols_list):
        if init_unit.capitalize()[0] == symbols:
            init_serial = serial
        if reduced_unit.capitalize()[0] == symbols:
            reduced_serial = serial
    power = abs(reduced_serial - init_serial)
    if init_serial < reduced_serial:
        reduced_num = float(reduced_num) / (1024 ** power)
    elif init_serial > reduced_serial:
        reduced_num = float(reduced_num) * (1024 ** power)
    return round(reduced_num, 2)

def yaml_to_dict(yamlPath):
    with open(yamlPath, encoding='UTF-8') as f:
        datas = yaml.load(f ,Loader=yaml.FullLoader)
    return datas

def get_version():
    with open('/etc/klcloud-release', 'r') as f:
        version = f.read()
    return version