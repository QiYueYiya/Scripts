import requests
import json
import re
import difflib
import os
import logging

def GetQLToken():
    path = '/ql/config/auth.json'
    if not os.path.exists(path):
        path = '/ql/data/config/auth.json'
    with open(path,"r",encoding="utf-8") as file:
        auth = json.load(file)
        qltoken = auth.get("token")
    try:
        url = "http://127.0.0.1:5700/api/user"
        rsp = session.get(url=url,headers={"Content-Type":"application/json","Authorization":"Bearer "+qltoken})
        if rsp.status_code != 200:
            url = "http://127.0.0.1:5700/api/user/printin"
            body={"username": auth.get("username"),"password": auth.get("password")}
            qltoken = session.post(url=url,data=body).json().get("data").get("token")
    except:
        print("无法获取青龙登录token！！！")
        exit()
    print("青龙登录token获取成功")
    return qltoken

# 运行青龙订阅任务
def qlSub(name):
    url = qlHost+"/subscriptions?searchValue="+name
    rsp = session.get(url=url, headers=qlHeader)
    if rsp.status_code == 200:
        jsons = rsp.json().get("data")
        if len(jsons):
            if "id" in jsons[0]:
                TaskID = "id"
            elif "_id" in jsons[0]:
                TaskID = "_id"
            else:
                print("获取订阅ID失败："+jsons[0]["name"])
                return False
        else:
            print(f"没有找到相关任务：{name}")
            return False
    else:
        log(f'搜索订阅失败：{str(rsp.status_code)}')
        if "message" in rsp.json():
            log(f"错误信息："+rsp.json()["message"])
        return False
    url = qlHost+"/subscriptions/run"
    rsp = session.put(url=url,headers=qlHeader,data=json.dumps([TaskID]))
    if rsp.status_code == 200:
        print(f"运行订阅成功："+jsons[0].get("name"))
        return True
    else:
        print(f"运行订阅失败："+jsons[0].get("name"))
        if "message" in rsp.json():
            log(f"错误信息："+rsp.json()["message"])
        return False

# 运行青龙任务
def qlCron(name,cmd,state):
    url = qlHost+"/crons?searchValue="+name
    rsp = session.get(url=url, headers=qlHeader)
    if rsp.status_code == 200:
        jsons = rsp.json().get("data")
        if len(jsons):
            # print("搜索到任务："+jsons[0]["name"])
            if "id" in jsons[0]:
                TaskID = "id"
            elif "_id" in jsons[0]:
                TaskID = "_id"
            else:
                print("获取任务ID失败："+jsons[0]["name"])
                return False
            # print("任务ID："+jsons[0].get(TaskID))
        else:
            print(f"没有找到相关任务：{name}")
            return False
    if state:
        # 禁用定时任务
        if os.environ.get('opencardDisable')=="true":
            qlCronDis(jsons[0]["name"],jsons[0].get(TaskID))
        # 更改任务命令
        if os.environ.get('opencardParam')!=None and "desi" not in jsons[0]["command"]:
            qlTaskChange(jsons,TaskID)
        # 检查重复任务
        if "opencardSimi" in os.environ:
            if not qlCronCheck(jsons[0]["name"]):
                return True
    # 运行定时任务
    url = qlHost+"/crons/"+cmd
    rsp = session.put(url=url,headers=qlHeader,data=json.dumps([jsons[0].get(TaskID)]))
    if rsp.status_code == 200:
        print(f"执行操作成功：{cmd} "+jsons[0]["name"])
        return True
    else:
        print(f"执行操作失败：{cmd} "+jsons[0]["name"])
        if "message" in rsp.json():
            print(f"错误信息："+rsp.json()["message"])
        return False

def qlCronDis(TaskName,TaskID):
    url = qlHost+"/crons/disable"
    rsp = session.put(url=url,headers=qlHeader,data=json.dumps([TaskID]))
    if rsp.status_code == 200:
        print(f"禁用开卡任务成功：{TaskName}")
    else:
        print(f'禁用开卡任务失败：{TaskName}')
        if "message" in rsp.json():
            print(f"错误信息："+rsp.json()["message"])

def qlTaskChange(jsons,TaskID):
    url = qlHost+"/crons"
    body = {"command": jsons[0]["command"]+" "+os.environ["opencardParam"], "schedule": jsons[0]["schedule"], "name": jsons[0]["name"], TaskID: jsons[0][TaskID]}
    rsp = session.put(url=url,headers=qlHeader,data=json.dumps(body))
    if rsp.status_code == 200:
        print("更改命令成功："+rsp.json().get("data").get("command"))
    else:
        print(f"更改命令失败："+jsons[0]["command"])
        if "message" in rsp.json():
            print(f"错误信息："+rsp.json()["message"])

# 检查重复任务 TaskName当前开卡任务名 TaskStr为nameCron.json内容
def qlCronCheck(name):
    with open('./nameCron.json',"r",encoding='UTF-8') as f:
        TaskStr = json.load(f)
    nameSplit = re.split(' |,|，',name)[::-1]
    taskName = nameSplit[0]
    if len(taskName)==0:
        taskName = nameSplit[1]
    for i in TaskStr:
        for x in TaskStr[i]:
            point = round(difflib.SequenceMatcher(None,taskName,x).quick_ratio()*100)
            if point>=int(os.environ["opencardSimi"]):
                print(f"任务名高度相似：{name}/{x}={point}%")
                print(f"放弃运行任务：{name}")
                # if Repo[0] not in TaskStr:
                #     TaskStr[Repo[0]]=[]
                # if taskName not in TaskStr[Repo[0]]:
                #     TaskStr[Repo[0]].append(taskName)
                #     with open(f"./nameCron.json","w",encoding='UTF-8') as f:
                #         json.dump(TaskStr,f,ensure_ascii=False)
                #         print(f"保存任务名到nameCron.json文件")
                return False
    return True

session = requests.session()
Host = "http://127.0.0.1:5700/api"
Header = {"Content-Type":"application/json"}
AuthFile='/ql/config/auth.json'
if not os.path.exists(AuthFile):
    AuthFile = '/ql/data/config/auth.json'
with open(AuthFile,"r",encoding="utf-8") as file:
    AuthContent = json.load(file)
    Token = AuthContent.get("token")
try:
    Header["Authorization"]="Bearer "+Token
    if session.get(url=Host+"/user",headers=Header).status_code == 401:
        logging.warn("Token失效，将重新获取Token")
        LoginData = session.post(url=Host+"/user/login",data={"username": AuthContent.get("username"),"password": AuthContent.get("password")})
        if LoginData.status_code == 200:
            NewToken = LoginData.json().get("data").get("token")
            Header["Authorization"]="Bearer "+NewToken
            logging.info("模拟登录青龙面板，获取Token成功")
        else:
            logging.error(LoginData.json().get("message"))
            exit()  
except Exception as e:
    logging.error("Token验证失败："+e)
    exit()
