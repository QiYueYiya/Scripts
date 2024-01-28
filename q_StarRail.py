"""
cron: 0,30 * * * *
new Env('星穹铁道');
"""

import requests
import time
import logging
import json
import qrcode
import random
import datetime
from hashlib import md5
from py_notify import send

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

def DS1():
    lettersAndNumbers = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    # 将要使用的salt，此为2.50.1版本的K2 salt。
    salt = "A4lPYtN0KGRVwE5M5Fm0DqQiC5VVMVM3"
    t = int(time.time())
    r = "".join(random.choices(lettersAndNumbers, k=6))
    main = f"salt={salt}&t={t}&r={r}"
    ds = md5(main.encode(encoding='UTF-8')).hexdigest()
    return f"{t},{r},{ds}" # 最终结果。

def DS2(get_query):
    # 将要使用的salt，此为4X salt
    salt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
    # body和query一般涉及到POST这种过程，所以这里另外定了一个变量body
    body = ''
    # 另外定了一个变量query，这两两变量又一般涉及到GET这种过程，所以这里另外定了一个变量query
    query = "&".join(sorted(get_query.split("&")))
    t = int(time.time())
    # 使用替代的方法
    r = random.randint(100001, 200000)
    main = f"salt={salt}&t={t}&r={r}&b={body}&q={query}"
    ds = md5(main.encode(encoding='UTF-8')).hexdigest()
    return f"{t},{r},{ds}"

def create_qrcode(link):
    qr = qrcode.QRCode()
    qr.add_data(link)
    #invert=True白底黑块,有些app不识别黑底白块.
    qr.print_ascii(invert=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save("qrcode.png")

def get_random_hex(length):
    return ''.join(random.choice('abcdef0123456789') for _ in range(length))

def get_device_id():
    parts = []
    parts.append(get_random_hex(8))
    parts.append(get_random_hex(4))
    parts.append(get_random_hex(4))
    parts.append(get_random_hex(4))
    parts.append(get_random_hex(12))
    return '-'.join(parts)

def get_random_ua():
    platforms = [
        "Windows NT 10.0",
        "Windows NT 11.3",
    ]
    browsers = [
        "Chrome",
        "Firefox",
        "Safari",
        "Opera",
        "Edge",
    ]
    platform = random.choice(platforms)
    browser = random.choice(browsers)
    version = f"{random.randint(100, 115)}.0.{random.randint(1000, 9999)}.{random.randint(0, 999)}"
    return f"Mozilla/5.0 ({platform}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} {browser}/{version}"

def get_fp(device_id,user_agent):
    url = 'https://public-data-api.mihoyo.com/device-fp/api/getFp'
    data = {
        'device_id': device_id,
        'seed_id': get_random_hex(16),
        'seed_time': str(timestamp),
        'platform': '4',
        'device_fp': get_random_hex(13),
        'app_name': 'bbs_cn',
        'ext_fields': '{\"userAgent\":\"'+user_agent+'\"}'
    }
    response = session.post(url, json=data)
    data = response.json()
    if data.get("retcode")==0:
        return data.get("data")["device_fp"]
    else:
        logging.error("获取设备指纹失败")

def query_qr_login_status(ticket,headers):
    url = "https://passport-api.miyoushe.com/account/ma-cn-passport/web/queryQRLoginStatus"
    try:
        payload = {
            "ticket": ticket
        }
        response = session.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payload = response.json()
        if payload.get("retcode")==0:
            return payload.get("data")
        else:
            logging.error("查询二维码扫描状态时出错: "+payload["message"])
    except requests.exceptions.RequestException as e:
        logging.error("查询二维码扫描状态时请求发生异常：" + str(e))
    except (KeyError, ValueError) as e:
        logging.error("查询二维码扫描状态时解析响应数据发生错误：" + str(e))
    return False

def create_qr_login(headers):
    url = "https://passport-api.miyoushe.com/account/ma-cn-passport/web/createQRLogin"
    try:
        response = session.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("retcode")==0:
            logging.info("请扫描二维码")
            create_qrcode(data.get("data")["url"])
            return data.get("data")["ticket"]
        else:
            logging.error("生成二维码时出错: "+data["message"])
    except requests.exceptions.RequestException as e:
        logging.error("生成二维码时请求发生异常：" + str(e))
    except (KeyError, ValueError) as e:
        logging.error("生成二维码时解析响应数据发生错误：" + str(e))
    return False

def get_game_info(cookie):
    query = "game_biz="
    url = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?"+query
    try:
        headers = {
            'x-rpc-app_version': '2.50.1',
            "x-rpc-client_type": "5",
            "DS": DS2(query),
            "Cookie": cookie
        }
        response = session.get(url,headers=headers)
        data = response.json()
        if data.get("retcode")==0:
            logging.info("获取角色信息成功")
            return data.get("data")["list"]
        else:
            logging.error("获取角色信息失败！")
            logging.error(data)
    except requests.exceptions.RequestException as e:
        logging.error("获取角色信息时请求发生异常：" + str(e))
    except (KeyError, ValueError) as e:
        logging.error("获取角色信息时解析响应数据发生错误：" + str(e))
    return False

def get_note(info,headers):
    get_query = "server="+info["region"]+"&role_id="+info["game_uid"]
    url = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note?"+get_query
    headers["DS"] = DS2(get_query)
    response = requests.get(url, headers=headers)
    data = response.json().get("data")
    if data:
        # 每日实训
        current_train_score = data["current_train_score"]
        # 每日实训上限
        max_train_score = data["max_train_score"]
        # 体力恢复
        current_stamina = data["current_stamina"]
        max_stamina = data["max_stamina"]
        stamina_recover_time = "已溢出" if data["stamina_recover_time"] == 0 else get_time_status(data["stamina_recover_time"])
        # 历战余响剩余
        weekly_cocoon_cnt = 3-data["weekly_cocoon_cnt"]
        # 历战余响
        weekly_cocoon_limit = data["weekly_cocoon_limit"]
        # 委托执行
        accepted_epedition_num = data["accepted_epedition_num"]
        # 委托执行上限
        total_expedition_num = data["total_expedition_num"]
        expeditions = data["expeditions"]
        # 文案
        content = f"开拓力: {current_stamina}/{max_stamina}\n恢复时间: {stamina_recover_time}"
        content += f"\n每日实训: {current_train_score}/{max_train_score}"
        content += f"\n历战余响: {weekly_cocoon_cnt}/{weekly_cocoon_limit}"
        content += f"\n委托执行: {accepted_epedition_num}/{total_expedition_num}"
        expedition_num = 0
        for x in range(len(expeditions)):
            remaining_time = expeditions[x]["remaining_time"]
            if remaining_time == 0:
                expedition_num +=1
            content += f"\n委托{x+1}："+("已完成" if remaining_time == 0 else get_time_status(remaining_time))
        logging.info("星穹铁道\n"+content)
        if max_stamina - current_stamina < 30:
            title = f"体力即将溢出：{current_stamina}/{max_stamina}"
            send(title,content)
        elif max_train_score - current_train_score > 0 and nowhour > 20:
            title = f"每日实训未完成：{current_train_score}/{max_train_score}"
            send(title,content)
        elif expedition_num > 0:
            title = f"委托已完成数量：{expedition_num}个"
            send(title,content)

def get_time_status(time_second):
    # 将时间戳转换为datetime对象
    dt = datetime.datetime.fromtimestamp(int(time.time())+time_second)
    # 获取当前日期
    today = now.date()
    # 获取明天的日期
    tomorrow = today + datetime.timedelta(days=1)
    # 判断时间戳所属的日期
    if dt.date() == today:
        status = "今天 "
    elif dt.date() == tomorrow:
        status = "明天 "
    return status + dt.strftime("%H:%M")

def main():
    with open("StarRail.json","r",encoding = "utf-8") as file:
        user_info = json.load(file)
    # logging.info(get_time_status(123456))
    if not user_info.get("cookie"):
        logging.info("登录获取Cookie并进行缓存")
        device_info = user_info.get("device_info")
        if not device_info:
            device_id = get_device_id()
            user_agent = get_random_ua()
            device_fp = get_fp(device_id,user_agent)
            user_info["device_info"] = {
                "device_id": device_id,
                "user_agent": user_agent,
                "device_fp": device_fp
            }
        headers = {
            'x-rpc-app_id': 'bll8iq97cem8',
            'x-rpc-client_type': '4',
            'x-rpc-game_biz': 'bbs_cn',
            'x-rpc-device_fp': device_info["device_fp"],
            'x-rpc-device_id': device_info["device_id"]
        }
        ticket = create_qr_login(headers)
        for x in range(60):
            status = query_qr_login_status(ticket,headers)
            if status:
                if status["status"] == "Confirmed":
                    logging.info("已扫描二维码，登录完成")
                    cookie = '; '.join([f'{key}={value}' for key, value in session.cookies.get_dict().items()])
                    user_info["cookie"] = cookie
                    game_info = get_game_info(cookie)
                    if not game_info:
                        break
                    for x in game_info:
                        user_info[x["game_biz"]]=x
                    break
            else:
                break
            time.sleep(2)
    else:
        logging.info("检测到已有Cookie缓存")
        cookie = user_info["cookie"]
        headers = {
            'x-rpc-client_type': '5',
            'x-rpc-app_version': '2.50.1',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': user_info["device_info"]["user_agent"],
            'x-rpc-device_fp': "38d7ef85512f8",
            "Cookie": cookie
        }
        get_note(user_info["hkrpg_cn"],headers)
    with open("StarRail.json","w",encoding = "utf-8") as file:
        json.dump(user_info, file, indent=4, ensure_ascii=False)

if __name__=="__main__":
    session = requests.session()
    timestamp = int(time.time()*1000)
    now = datetime.datetime.now()  # 获取当前日期和时间
    nowhour = now.hour
    main()