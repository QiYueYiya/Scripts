import requests
import hashlib
import time
import os
from datetime import datetime

def md5sum(data):
    return hashlib.md5(data.encode('utf-8')).hexdigest().upper()

def form_time(current_timestamp = None):
    tt = int(time.time())
    if current_timestamp:
        tt = current_timestamp
    return datetime.fromtimestamp(tt).strftime('%Y%m%d%H%M')

def get_sign(token = None):
    current_timestamp = int(time.time() * 1000000000)
    formatted_time = form_time(current_timestamp/1000000000)
    if not token:
        token = md5sum(str(current_timestamp))
        print("未传入Token，获取新的Token:"+token)
    passwd = md5sum(password)
    sign_str = md5sum(token + account + passwd +"false"+formatted_time)
    return {
        "token": token,
        "passwd": passwd,
        "sign": sign_str,
        "api_sign": f'{sign_str}:{int(current_timestamp/1000000)}',
    }

def login():
    path = "v2/login"
    info = get_sign()
    headers['api_sign']=path+':'+info["api_sign"]
    params = {
        'token': info["token"],
        'oaid': info["token"],
        'account': account,
        'password': info["passwd"],
        'childDevice': 'false',
        'sign': info["sign"],
    }
    response = requests.get(url+path, params=params, headers=headers)
    if response.status_code==200:
        print(response.json().get("message"))
        with open("china_iplist.txt", "w") as file:
            file.write(info["token"])
        return info["token"]
    else:
        print(response.json().get("message"))
    return False

def day_sign():
    path = "user/v1/daySign"
    current_timestamp = int(time.time() * 1000)
    sign = md5sum(jwttoken+form_time(current_timestamp/1000))
    headers['api_sign']=f'{path}:{sign}:{current_timestamp}'
    params = {
        'token': jwttoken,
        'oaid': jwttoken,
        'vipType': '0',
        'sign': sign,
    }
    response = requests.get(url+path, params=params, headers=headers)
    if response.status_code==200:
        print(response.json().get("message"))
    else:
        print("签到失败："+response.text)

def check(token):
    path = "user/v1/fragmentMeData"
    current_timestamp = int(time.time() * 1000)
    sign = md5sum(token+form_time(current_timestamp/1000))
    headers['api_sign']=f'{path}:{sign}:{current_timestamp}'
    params = {
        "token":token,
        "oaid":token,
        "sign":sign
    }
    response = requests.get(url+path, params=params, headers=headers)
    if response.status_code==200:
        data = response.json()
        if data.get("code")==100:
            return token
        else:
            print("账号过期，重新登录")
            return login()
    else:
        print("检查账号有效性失败，重新登录")
        return login()

if __name__=="__main__":
    user_info = os.getenv("appshare").split("&")
    account = user_info[0]
    password = user_info[1]
    url = "https://appshare.vip/"
    headers = {
        'Cache-Control': 'no-cache, no-store',
        'Host': 'appshare.vip',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': 'okhttp/4.12.0',
    }
    with open("appshare_token.txt", "r") as file:
        last_token = file.read()
    jwttoken = check(last_token)
    if jwttoken:
        day_sign()
    else:
        print("获取用户Token失败")
