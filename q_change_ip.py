"""
cron: 0 0 * * *
new Env('更新动态IP');
"""

import requests
import base64
import hashlib
import time
import logging
import json
from datetime import datetime, timedelta

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

def login_ikuai(username, password):
    # 登录爱快路由器
    url = ikuai_address+'/Action/login'
    md5_password = hashlib.md5(password.encode(encoding='UTF-8')).hexdigest()
    base64_password = base64.b64encode(f"salt_11{password}".encode()).decode('utf-8')
    payload = {
        "username": username,
        "passwd": md5_password,
        "pass": base64_password,
        "remember_password": None
    }
    response = session.post(url, json=payload,verify=False)
    data = response.json()
    if data.get("Result") == 10000:
        logging.info("登录爱快路由器成功")
    else:
        logging.error("登录爱快路由器失败: "+data.get("ErrMsg"))
        exit()

def get_ip_addr_list():
    # 获取vlan_data信息
    url = ikuai_address+'/Action/call'
    payload = {
	    "func_name": "wan",
	    "action": "show",
	    "param": {
		    "TYPE": "vlan_data,vlan_total",
		    "ORDER_BY": "vlan_name",
		    "ORDER": "asc",
		    "vlan_internet": 2,
		    "interface": "wan1",
		    "limit": "0,20"
	    }
    }
    headers = {'Accept': 'application/json'}
    response = session.post(url, json=payload, headers=headers, verify=False)
    data = response.json()
    vlan_data = data.get("Data").get("vlan_data")
    if vlan_data:
        ikuai_addr_list = {}
        for item in vlan_data:
            vlan_comment = item.get("comment")+master_domain
            ikuai_addr_list[vlan_comment] = item.get("pppoe_ip_addr")
        return ikuai_addr_list
    else:
        logging.error("获取IP信息失败: "+data.get("ErrMsg"))
        return False

def login_adguardhome(name, password):
    # 登录AdGuard Home获取凭证
    url = adguard_address+'/control/login'
    payload = {
        "name": name,
        "password": password
    }
    headers = {
        'Accept': 'application/json'
    }
    response = session.post(url, json=payload, headers=headers)
    if response.status_code ==200:
        logging.info("登录AdGuard Home成功")
    else:
        logging.error("登录AdGuard Home失败："+response.text)
        exit()

# 获取AdGuard Home的DNS重写列表
def get_rules_list():
    url = adguard_address+'/control/rewrite/list'
    headers = {
        'Accept': 'application/json'
    }
    response = session.get(url, headers=headers)
    data = response.json()
    if data:
        logging.info("获取AdGuard Home DNS重写列表成功")
        logging.info(data)
        return data
    else:
        logging.error("获取AdGuard Home DNS重写列表失败")
        exit()

def update_adguard_home(rule,ip_addr_ikuai):
    # 更新AdGuard Home的自定义规则列表
    url = adguard_address+'/control/rewrite/update'
    payload = {
	    "target": rule,
	    "update": {
		    "answer": ip_addr_ikuai,
		    "domain": rule.get("domain")
	    }
    }
    headers = {
        'Accept': 'application/json'
    }
    response = session.put(url, json=payload, headers=headers)
    if response.status_code == 200:
        logging.info("更新AdGuard Home DNS重写成功")
    else:
        logging.error("更新AdGuard Home DNS重写失败")


def get_timestamp_of_today():
    # 获取当前日期
    current_date = datetime.now().date()
    # 构建目标时间
    target_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23, minutes=59, seconds=30)
    # 转换为时间戳并返回
    return target_time.timestamp()

def main():
    # 获取规则列表
    rest = time.time()
    start = time.time()
    end = get_timestamp_of_today()
    rules_list = get_rules_list()
    while start < end:
        start = time.time()
        if start - rest >= 60:
            rest = time.time()
            ip_addr_list = get_ip_addr_list()
            # 检查AdGuard Home中自定义规则列表是否需要更新
            for rule in rules_list:
                rule_domain = rule.get("domain")
                ip_addr_ad = rule.get("answer")
                ip_addr_ikuai = ip_addr_list.get(rule_domain)
                if ip_addr_ad != ip_addr_ikuai :
                    logging.info(f"{rule_domain} 旧: {ip_addr_ad} --> 新: {ip_addr_ikuai}")
                    update_adguard_home(rule,ip_addr_ikuai)
                    rule["answer"]=ip_addr_ikuai
        time.sleep(1)

if __name__ == '__main__':
    with open("/ql/data/config/device_tracker.json","r") as file:
        change_ip = json.load(file)
    
    master_domain = change_ip["ikuai_config"]["domain"]
    ikuai_address = change_ip["ikuai_config"]["address"]
    ikuai_username = change_ip["ikuai_config"]["username"]
    ikuai_password = change_ip["ikuai_config"]["password"]
    adguard_address = change_ip["adguard_config"]["address"]
    adguard_username = change_ip["adguard_config"]["username"]
    adguard_password = change_ip["adguard_config"]["password"]
    requests.packages.urllib3.disable_warnings()
    session = requests.session()
    # 登录爱快路由器
    login_ikuai(ikuai_username, ikuai_password)
    # 登录AdGuard Home
    login_adguardhome(adguard_username, adguard_password)
    main()
