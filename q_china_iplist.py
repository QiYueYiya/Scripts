"""
环境变量

# 爱快地址
export ikuai_host="https://127.0.0.1"
# 爱快账号
export ikuai_username="name"
# 爱快密码
export ikuai_password="pwd"
# Github Token，用于访问API
export ikuai_token=""


cron: 30 7 * * *
new Env('爱快IP白名单');
"""

import base64
from hashlib import md5
from urllib import parse
import json
import logging
import os
import re
import requests
from py_notify import send

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)

# 创建一个空列表来存储日志消息
log_messages = []
# 将日志处理程序添加到记录器，将日志消息添加到列表中
class ListHandler(logging.Handler):
    def emit(self, record):
        log_messages.append(self.format(record))
logging = logging.getLogger()
logging.addHandler(ListHandler())

# 检查大陆IP列表更新
def check_update():
    try:
        url = "https://api.github.com/repos/mayaxcn/china-ip-list/contents/chnroute.txt" # 大陆IP列表地址
        headers = {}
        if ikuai_token: # 如果变量为True则使用Github Token
            headers["Authorization"]=ikuai_token
        res = session.get(url,headers=headers,verify=False).json()
        if res.get("name"): # 请求成功得到key “name”
            if os.path.isfile("china_iplist.txt"): # 如果sha值缓存文件存在就读取
                with open("china_iplist.txt", "r") as file:
                    last_sha = file.read()
            else:
                last_sha = "123456" # 不存在则随便定义一下，只要不和res.get("sha")相同即可
            if res.get("sha") != last_sha: # sha值不相同即有更新
                logging.info("检查到大陆IP列表更新！")
                # 将base64字符串 res.get("content") 解码，然后转换为array格式
                ip_list = base64.b64decode(res.get("content")).decode("utf-8").split("\n")
                with open("china_iplist.txt", "w") as file: # 缓存sha值
                    file.write(res.get("sha"))
                return True,ip_list # 返回大陆IP列表
            else:
                logging.info("大陆IP列表已是最新，无需更新！")
        else:
            logging.info("检查大陆IP列表更新失败: "+json.dumps(res))
    except Exception as e:
        logging.error("检查大陆IP列表更新出错: "+e)
    return False,[]

# 登录iKuai
def iKuai_Login():
    try:
        body = {
	        "username": username, # 用户名
	        "passwd": md5(password.encode(encoding='UTF-8')).hexdigest(), # 密码进行编码
	        "pass": base64.b64encode(f"salt_11{password}".encode()).decode('utf-8'), # 同上
	        "remember_password":None, # 不记住密码，True为记住密码
        }
        res = session.post(url=host+"/Action/login",data=json.dumps(body),verify=False).json()
        if res.get("Result")==10000: # 返回其他数值即登录失败
            logging.info("爱快登录成功")
            return True
        else:
            logging.info("爱快登录失败: "+res.get("ErrMsg"))
    except Exception as e:
        logging.error("错误: "+e)
    return False

# 获取分组列表
def Get_IP_Grouping():
        body = {
            "func_name":"custom_isp",
            "action":"show",
            "param":{
                "TYPE":"total,data",
                "limit":"0,20",
                "ORDER_BY":"",
                "ORDER":""
            }
        }
        res = session.post(url=host+"/Action/call", data=json.dumps(body), verify=False).json()
        if res.get("ErrMsg")=="Success":
            id_list = []
            for x in res.get("Data").get("data"):
                if "china_" in x["name"]:
                    id_list.append(x)
            return id_list

def UP_IP_Grouping():
    try:
        ip_list_split = [ip_list[i:i+5000] for i in range(0, len(ip_list), 5000)] # 每一千行分割为一个array，因为爱快一个分组最多1000行
        id_list = Get_IP_Grouping() # 获取爱快当前有多少个分组
        # 上传IP地址段到爱快分组
        for x in range(0,len(ip_list_split)): # 新获取的大陆IP列表内有几个分组
            addr_pool = ",".join(ip_list_split[x]) # 将array列表转换为字符串，用逗号隔开
            add_body = {
	            "func_name": "custom_isp",
	            "action": "edit",
	            "param": {
		            "id": id_list[x]["id"],
		            "name": id_list[x]["name"],
		            "ipgroup": addr_pool,
		            "comment": ""
	            }
            }
            res = session.post(url=host+"/Action/call",data=json.dumps(add_body),verify=False).json()
            if res.get("ErrMsg")=="Success":
                logging.info("更新大陆IP列表成功: "+id_list[x]["name"])
            else:
                logging.error("更新大陆IP列表失败: "+res.get("ErrMsg"))
                return False
        return True
    except Exception as e:
        logging.error(e)
        logging.error("上传IP分组错误, 行号", e.__traceback__.tb_lineno)
        return False

if __name__=="__main__":
    requests.packages.urllib3.disable_warnings()
    session = requests.session()
    # 相关变量
    host = os.getenv("ikuai_host")
    username = os.getenv("ikuai_username")
    password = os.getenv("ikuai_password")
    ikuai_token = os.getenv("ikuai_token")
    src_addr = [] # 缓存新获取的分组名称
    if host and username and password:
        state_update,ip_list = check_update() # 检查大陆IP列表更新
        if state_update: # 如果更新
            if iKuai_Login(): # 登录爱快
                UP_IP_Grouping() # 查看爱快当前分组列表
            send('爱快大陆IP','\n'.join(log_messages))
    else:
        logging.error("缺少环境变量。停止运行")
        send('爱快大陆IP','\n'.join(log_messages))