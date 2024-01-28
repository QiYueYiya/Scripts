"""
过期时间为30天，所以定时为每15天获取一次新的Token
需要填写配置文件"Cloud139.json"，格式如下，第一次需要自己抓一次包
{
    "alist_url":"Alist地址，例如http://127.0.0.1:5244",
    "alist_token":"Alist用户名",
    "account": "手机号",
    "authorization": "抓包获取的jwt token，jwt token需包含“Basic ”前缀"
}

cron: 30 7 */15 * *
new Env('和彩云Token续期');
"""

import requests
import logging
import base64
import json
import os
from py_notify import send

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

def get_alist_storage():
    url = alist_url+"/api/admin/storage/list"
    return_data = session.get(url,headers=alist_headers)
    return_data = return_data.json()
    drivers = []
    if return_data.get("code") == 200:
        lists = return_data["data"]["content"]
        for driver in lists:
            if driver["driver"]=="139Yun":
                logging.info("Alist 存储信息获取成功")
                drivers.append(driver)
        return drivers
    else:
        logging.error("Alist 存储信息获取失败：%s",return_data["message"])
    exit()

def set_alist_storage():
    url = alist_url+"/api/admin/storage/update"
    data = driver
    return_data = session.post(url,headers=alist_headers,json=data).json()
    if return_data.get("code") == 200:
        logging.info("Alist 和彩云Token 更新成功")
        send("和彩云Token续期","成功")
    else:
        logging.error("Alist 和彩云Token 更新失败：%s",return_data["message"])

def get_token():
    url = 'https://orches.yun.139.com/orchestration/auth-rebuild/token/v1.0/querySpecToken'
    data = {"account": account, "toSourceId": "001005"}
    return_data = session.post(url, headers = headers, json = data).json()
    if return_data.get('success'):
        token = return_data['data']['token']
        logging.info("和彩云 临时Token 获取成功: %s",token)
        return token
    else:
        logging.error("和彩云 临时Token 获取失败: %s",return_data['message'])
    exit()

def get_jwt_token():
    url = f"https://caiyun.feixin.10086.cn:7071/portal/auth/tyrzLogin.action?ssoToken={token}"
    return_data = session.post(url = url, headers = headers).json()
    if return_data.get('code') == 0:
        long_token = return_data['result']['token']
        part = long_token.split('.')[1]+"=="
        decoded_bytes = base64.b64decode(part)
        decoded_json = json.loads(decoded_bytes.decode('utf-8'))["sub"]
        auth_token = f"pc:{account}:"+json.loads(decoded_json)["token"]
        bytes_to_encode = auth_token.encode("utf-8")
        jwt_token = base64.b64encode(bytes_to_encode).decode("utf-8")
        logging.info("和彩云 JWT_Token 获取成功: %s",jwt_token)
        return jwt_token
    else:
        logging.error("和彩云 JWT_Token 获取失败: %s",return_data['msg'])
    exit()

if __name__=="__main__":
    session = requests.session()
    try:
        alist_conf = os.getenv("alist_conf").split("@")
        alist_url = alist_conf[0]
        alist_token = alist_conf[1]
        alist_headers = {
            "authorization": alist_token
        }
        drivers = get_alist_storage()
        for driver in drivers:
            account = driver["remark"]
            addition = json.loads(driver["addition"])
            authorization = "Basic "+addition["authorization"]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 13; 2304FPN6DC Build/TKQ1.220829.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.40 Mobile Safari/537.36 MCloudApp/10.1.0',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Host': 'caiyun.feixin.10086.cn:7071',
                'authorization': authorization
            }
            token = get_token()
            jwt_token = get_jwt_token()
            addition["authorization"]=  jwt_token
            driver["addition"] = json.dumps(addition)
            set_alist_storage()
    except (KeyError, ValueError) as e:
        logging.error("解析响应数据时发生错误：" + str(e))
        send("和彩云Token续期",str(e))
