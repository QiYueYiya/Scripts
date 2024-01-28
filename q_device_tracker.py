"""
cron: 0 */12 * * *
new Env('设备追踪');

只支持刷了OpenWrt的路由器，我使用的设备是360T7 237固件
其他设备暂未测试，有些设备的无线接口可能不一致导致无法查询
请自行查看，在62和63行，我的接口名称是ra0和rai0
########################################
    HomeAssistent configuration.yaml
########################################
mqtt:
  binary_sensor:
    - unique_id: Phone_device_tracker
      name: "Phone"
      state_topic: "binary_sensor/device_tracker/Phone"
      device_class: "connectivity"
      qos: 2
      device:
        name: "Device Tracker"
        model: "Device Tracker"
        manufacturer: "柒月弋"
        identifiers: python_device_tracker
"""

import requests,time,os,json
import paho.mqtt.client as mqtt
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

# MQTT 连接回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("连接成功")
    else:
        logging.error("连接失败")

# 查询设备在线状态
def check():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = [{
	    "jsonrpc": "2.0",
	    "id": 19,
	    "method": "call",
	    "params": [cookie, "iwinfo", "assoclist", {
		    "device": "ra0"
	    }]
    }, {
	    "jsonrpc": "2.0",
	    "id": 20,
	    "method": "call",
	    "params": [cookie, "iwinfo", "assoclist", {
		    "device": "rax0"
	    }]
    }]
    data = session.post(url=op_address+"/ubus", json=payload, headers=headers).json() # 获取连接5G WiFi的设备
    mac_addresses = [item["mac"] for sublist in [d["result"][1]["results"] for d in data] for item in sublist][::-1]
    for device in devices_info: # 遍历要检测的设备列表
        device["Topic"] = f"binary_sensor/device_tracker/{device['DeviceName']}" # 设备主题
        if device["MacAddr"].upper() in mac_addresses : # 如果“连接设备”列表内包含“检测设备”的MAC地址，则判断在线
            if device["LastStatus"]!="online":
                logging.info(device["DeviceName"] + ": 已连接")
            client.publish(device["Topic"],"ON")
            device["Status"] = "online"
            device["LastStatus"] = device["Status"]
        else:
            if device["LastStatus"]!="offline":
                logging.info(device["DeviceName"] + ": 已断开")
            client.publish(device["Topic"],"OFF")
            device["Status"] = "offline"
            device["LastStatus"] = device["Status"]

# 登录OpenWrt获取Token
def login():
    data = {
        "luci_username": op_username,
        "luci_password": op_password
    }
    session.post(op_address+"/cgi-bin/luci", data=data)
    cookie = session.cookies.get_dict().get("sysauth")
    print(cookie)
    return cookie

def get_timestamp_of_today():
    # 获取当前日期
    current_date = datetime.now().date()
    # 构建目标时间
    target_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23, minutes=59, seconds=30)
    # 转换为时间戳并返回
    return target_time.timestamp()


def main():
    rest = time.time()
    start = time.time()
    end = get_timestamp_of_today()
    while start < end :
        start = time.time()
        if start - rest >=60:
            try:
                check()
                rest = time.time()
            except Exception as e:
                logging.error("设备在线状态监测程序意外退出！")
                logging.error(f"错误信息：{str(e)}")
        time.sleep(1)

if __name__ == "__main__":
    with open("/ql/data/config/device_tracker.json","r") as file:
        device_tracker = json.load(file)
    # MQTT 服务器地址和端口
    mqtt_address = device_tracker["mqtt_config"]["address"]
    # MQTT 服务器端口
    mqtt_port = device_tracker["mqtt_config"]["port"]
    # MQTT 服务器用户名
    mqtt_username = device_tracker["mqtt_config"]["username"]
    # MQTT 服务器密码
    mqtt_password = device_tracker["mqtt_config"]["password"]
    # OpenWrt路由器地址
    op_address = device_tracker["openwrt_config"]["address"]
    # OpenWrt路由器用户名
    op_username = device_tracker["openwrt_config"]["username"]
    # OpenWrt路由器密码
    op_password = device_tracker["openwrt_config"]["password"]
    # 追踪设备信息
    devices_info = device_tracker["device_info"]
    # 创建 MQTT 客户端
    client = mqtt.Client(client_id="device_tracker")
    client.username_pw_set(mqtt_username, mqtt_password)
    # 设置连接和消息接收的回调函数
    client.on_connect = on_connect
    # 连接到 MQTT 代理服务器
    client.connect(mqtt_address, mqtt_port, 60)
    # 请求凭证
    session = requests.session()
    # 请求头
    # 登录OpenWrt获取Token
    cookie = login()
    # 循环查询设备在线状态
    main()
