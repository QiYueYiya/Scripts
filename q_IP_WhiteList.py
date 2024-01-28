"""
环境变量

# 爱快地址
export ikuai_host="https://127.0.0.1"
# 爱快账号
export ikuai_username="name"
# 爱快密码
export ikuai_password="pwd"
# 分组名称前缀
export ikuai_group_name="name"
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

# 检查IP列表更新
def check_update():
    try:
        url = "https://api.github.com/repos/metowolf/iplist/contents/data/cncity/360000.txt" # IP列表地址
        headers = {}
        if ikuai_token: # 如果变量为True则使用Github Token
            headers["Authorization"]=ikuai_token
        res = session.get(url,headers=headers,verify=False).json()
        if res.get("name"): # 请求成功得到key “name”
            if os.path.isfile("ip_check_update.txt"): # 如果sha值缓存文件存在就读取
                with open("ip_check_update.txt", "r") as file:
                    last_sha = file.read()
            else:
                last_sha = "123456" # 不存在则随便定义一下，只要不和res.get("sha")相同即可
            if res.get("sha") != last_sha: # sha值不相同即有更新
                logging.info("检查到IP列表更新！")
                # 将base64字符串 res.get("content") 解码，添加内网IP，然后转换为array格式
                ip_list = ("10.10.10.1/24\n172.16.0.1/22\n"+base64.b64decode(res.get("content")).decode("utf-8")).split("\n")
                with open("ip_check_update.txt", "w") as file: # 缓存sha值
                    file.write(res.get("sha"))
                return True,ip_list # 返回IP列表
            else:
                logging.info("IP列表已是最新，无需更新！")
        else:
            logging.info("检查IP列表更新失败: "+json.dumps(res))
    except Exception as e:
        logging.error("检查IP列表更新出错: "+e)
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
    try:
        query_body = { # 分组列表的请求体格式
	        "func_name": "ipgroup",
	        "action": "show",
	        "param": {
		        "TYPE": "total,data",
		        "limit": "0,100",
		        "ORDER_BY": "",
		        "ORDER": "",
		        "FINDS": "group_name",
		        "KEYWORDS": group_name
	        }
        }
        res = session.post(url=host+"/Action/call",data=json.dumps(query_body),verify=False).json()
        if res.get("ErrMsg")=="Success":
            return res["Data"]["data"] # 返回数据
        else:
            logging.error("获取分组失败: "+res.get("ErrMsg"))
            return False
    except Exception as e:
        logging.error(e)
        logging.error("错误, 退出！")
    return False

def UP_IP_Grouping():
    try:
        ip_list_split = [ip_list[i:i+1000] for i in range(0, len(ip_list), 1000)] # 每一千行分割为一个array，因为爱快一个分组最多1000行
        grouping = Get_IP_Grouping() # 获取爱快当前有多少个分组
        # 上传IP地址段到爱快分组
        for x in range(0,len(ip_list_split)): # 新获取的ip列表内有几个分组
            addr_pool = ",".join(ip_list_split[x]) # 将array列表转换为字符串，用逗号隔开
            comment = "".join(re.findall(r",",addr_pool)) # 提取出addr_pool中的逗号
            add_body = { # 编辑分组请求体格式
                "func_name": "ipgroup",
                "action": "edit",
                "param": {
                    "addr_pool": addr_pool,
                    "comment": comment,
                    "type": 0
                }
            }
            add_body["param"]["group_name"] = group_name + str(x+1) # 分组名称
            src_addr.append(group_name + str(x+1)) # 缓存分组名称
            if len(grouping) > x: # 如果爱快当前分组数量大于ip列表的分组数量
                add_body["param"]["id"] = grouping[x]["id"] # 沿用ID
            else:
                add_body["action"] = "add" # 新建分组
                add_body["param"]["newRow"] = True
            res = session.post(url=host+"/Action/call",data=json.dumps(add_body),verify=False).json()
            if res.get("ErrMsg")=="Success":
                logging.info("更新IP列表成功: "+group_name + str(x+1))
            else:
                logging.error("更新IP列表失败: "+res.get("ErrMsg"))
                return False
        # 如果爱快分组数量大于实际分组数量, 则删除多余的分组
        if len(grouping) > len(ip_list_split):
            del_body = { # 删除分组请求体格式
                "func_name": "ipgroup",
                "action": "del",
                "param": {}
            }
            for x in range(len(ip_list_split),len(grouping)): # 查看多余的分组
                del_body["param"]["id"] = grouping[x]["id"] # 分配多余分组的ID
                res = session.post(url=host+"/Action/call",data=json.dumps(del_body),verify=False).json()
                if res.get("ErrMsg")=="Success":
                    logging.info("删除多余分组: "+grouping[x]["group_name"])
                else:
                    logging.error("删除多余分组失败: "+res.get("ErrMsg"))
                    return False
        return True
    except Exception as e:
        logging.error(e)
        logging.error("上传IP分组错误, 行号", e.__traceback__.tb_lineno)
        return False

def UP_IP_WhiteList():
    try:
        body = { # 查看爱快IP白名单请求体格式
	        "func_name": "dnat",
	        "action": "show",
	        "param": {
		        "TYPE": "total,data",
		        "limit": "0,100",
		        "ORDER_BY": "",
		        "ORDER": ""
	        }
        }
        res = session.post(url=host+"/Action/call",data=json.dumps(body),verify=False).json()
        if res.get("ErrMsg")=="Success":
            success_list = []
            for x in res["Data"]["data"]: # 遍历列表
                if group_name in x["src_addr"]: # 如果IP白名单分组内包含分组名称前缀
                    x["src_addr"] = ",".join(src_addr) # 更新IP白名单分组为新获取的
                    body["action"] = "edit" # 编辑模式
                    body["param"] = x # 设置相关信息
                    res = session.post(url=host+"/Action/call",data=json.dumps(body),verify=False).json()
                    if res.get("ErrMsg")=="Success":
                        success_list.append(x["comment"])
                    else:
                        logging.error("更改允许访问IP失败: "+x["comment"]+" "+res.get("ErrMsg"))
            logging.info(f"更改允许访问IP成功: {len(success_list)}个")
        else:
            logging.error("获取列表失败: "+res.get("ErrMsg"))
    except Exception as e:
        logging.error(e)
        logging.error('更改允许访问IP错误, 行号', e.__traceback__.tb_lineno)

if __name__=="__main__":
    requests.packages.urllib3.disable_warnings()
    session = requests.session()
    # 相关变量
    host = os.getenv("ikuai_host")
    username = os.getenv("ikuai_username")
    password = os.getenv("ikuai_password")
    group_name = os.getenv("ikuai_group_name")
    ikuai_token = os.getenv("ikuai_token")
    src_addr = [] # 缓存新获取的分组名称
    if host and username and password and group_name:
        state_update,ip_list = check_update() # 检查IP列表更新
        if state_update: # 如果更新
            if iKuai_Login(): # 登录爱快
                if UP_IP_Grouping(): # 查看爱快当前分组列表
                    UP_IP_WhiteList() # 更新分组到IP白名单
            send('爱快IP白名单','\n'.join(log_messages))
    else:
        logging.error("缺少环境变量。停止运行")
        send('爱快IP白名单','\n'.join(log_messages))