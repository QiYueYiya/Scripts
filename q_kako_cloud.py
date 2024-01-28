"""
cron: 30 7 */15 * *
new Env('KaKo机场续订');
"""

import requests
import os
import logging
from py_notify import send

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

url = "https://kakocc-bjf5bhbegfaac9g3.z01.azurefd.net/api/v1"
headers = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/x-www-form-urlencoded',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62'
}

def login():
    login_url = url+"/passport/auth/login"
    response = requests.post(login_url, headers=headers, data=login_data)
    if response.status_code == 200:
        auth_data = response.json().get("data").get("auth_data")
        if auth_data:
            logging.info("登录成功")
            return auth_data
        else:
            logging.error("login_error")
            logging.error(response.json())
            return False
    else:
        logging.error("login_error")
        logging.error(response.text)
        return False

def get_order(auth_data):
    order_url = url+"/user/order/save"
    headers['authorization']=auth_data
    order_data = {
        'period': 'month_price',
        'plan_id': '24',
        'coupon_code': 'free'
    }
    response = requests.post(order_url, headers=headers, data=order_data)
    if response.status_code == 200:
        order_number = response.json().get("data")
        if order_number:
            logging.info("创建订单成功")
            return order_number
        else:
            logging.error("get_order_error")
            logging.error(response.json())
            return False
    else:
        logging.error("get_order_error")
        logging.error(response.text)
        return False

def check_payment(auth_data, order_number):
    checkout_url = url+"/user/order/checkout"
    headers['authorization']=auth_data
    checkout_data = {
        'trade_no': order_number,
        'method': '2'
    }
    response = requests.post(checkout_url, headers=headers, data=checkout_data)
    if response.status_code == 200:
        payment_status = response.json().get("data")
        if payment_status:
            logging.info("订阅成功")
            send("KaKo机场","订阅成功")
            return True
        else:
            logging.error("check_payment_error")
            logging.error(response.json())
            return False
    else:
        logging.error("check_payment_error")
        logging.error(response.text)
        return False

if __name__=="__main__":
    account = os.getenv("kako_account").split(":")
    login_data = {
        'email': account[0],
        'password': account[1]
    }
    status = False
    auth_data = login()
    if auth_data:
        order_number = get_order(auth_data)
        if order_number:
            status = check_payment(auth_data, order_number)
    if not status:
        send("KaKo机场","订阅失败")
