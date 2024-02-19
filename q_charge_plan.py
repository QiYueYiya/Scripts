"""
cron: 0 5 * * *
new Env('充电计划');
"""

import os
import requests
import json
import time
from py_notify import send

def start_charge(interfaceId):
    data = {
	    "dateline": int(time.time()),
	    "interfaceId": interfaceId,
	    "payType": 1,
	    "agreementId": None,
	    "chargeStrategy": 1,
	    "strategyValue": 0,
	    "carId": None,
	    "socLimit": 100,
	    "aliScene": None,
	    "shortNo": None,
	    "concessionId": None,
	    "deductionCardRuleTypeId": None,
	    "ruleTypeIds": [],
	    "walletType": None,
	    "freeLimit": None,
	    "productIds": "",
	    "serviceId": None
    }
    response = requests.post(f"https://miniapp.echengchong.com/serviceCharge/startCharge?{auth}&appplat=11&appver=138", json=data)
    data = response.json()
    if data.get("code")==1:
        print("获取服务ID成功")
        data = query_start_charge(charge_info["interface_id"], data["data"]["serviceId"])
    else:
        print(data)
    send("充电计划",data)

def query_start_charge(interface_id, service_id):
    x = 0
    while x < 10:
        timestamp = int(time.time())
        data = {
            "dateline": timestamp,
            "interfaceId": interface_id,
            "payType": 0,
            "serviceId": service_id
        }
        response = requests.post(f"https://miniapp.echengchong.com/serviceCharge/queryStartCharge?{auth}&appplat=11&appver=138", json=data)
        data = response.json()
        if data["code"] != 302:
            print(data["msg"])
            return data["msg"]
        else:
            print(data)
        time.sleep(2)
        x += 1

if __name__=="__main__":
    if 'charge' in os.environ:
        charge_info = json.loads(os.getenv("charge"))
        timestamp = int(time.time())
        if timestamp - charge_info["time"] < 600:
            print(charge_info["allName"]+charge_info["name"]+"枪充电启动中，请稍后....")
            auth = charge_info["token"]
            start_charge(charge_info["interface_id"])
        else:
            print("非预定充电时间，退出！")
    else:
        print("请检查变量 charge")

