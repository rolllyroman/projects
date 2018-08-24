#coding:utf-8
import tornado.gen
import uuid
import time
import json
import logging
import random
import sys
import os
sys.path.append('../')

from constants import *
from config import *
from tornado.httpclient import AsyncHTTPClient
from datetime import datetime

class AccessToken(object):
    """access_token辅助类"""
    _access_token = None
    _create_time = 0
    _expires_in = 0

    @classmethod
    @tornado.gen.coroutine
    def update_access_token(cls):
        client = AsyncHTTPClient()
        url = "https://api.weixin.qq.com/cgi-bin/token?" \
        "grant_type=client_credential&appid=%s&secret=%s" % (WECHAT_APP_ID, WECHAT_APP_SECRET)
        resp = yield client.fetch(url)
        dict_data = json.loads(resp.body)
        if "errcode" in dict_data:
            raise Exception("wechat server error")
        else:
            cls._access_token = dict_data["access_token"]
            cls._expires_in = dict_data["expires_in"]
            cls._create_time = time.time()


    @classmethod
    @tornado.gen.coroutine
    def get_access_token(cls):
        if time.time() - cls._create_time > (cls._expires_in - 200):
            # 向微信服务器请求access_token
            yield cls.update_access_token()
            raise tornado.gen.Return(cls._access_token)
        else:
            raise tornado.gen.Return(cls._access_token)

class Session(object):

    '''
    def __new__(cls,request_handler_obj):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Session, cls).__new__(cls)
        return cls.instance
    '''

    def __init__(self, request_handler_obj):
        # 先判断用户是否已经有了session_id
        self._request_handler = request_handler_obj
        self.session_id = request_handler_obj.get_secure_cookie("session_id")

        # 如果不存在session_id,生成session_id
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
            request_handler_obj.set_secure_cookie("session_id", self.session_id)

    def set(self,key,value):
        json_data = self._request_handler.redis.get("sess_%s" % self.session_id)
        if not json_data:
            json_data = "{}"
        data = json.loads(json_data)
        data[key] = value
        res_data = json.dumps(data)
        self._request_handler.redis.setex("sess_%s" % self.session_id,res_data,3600)

    def get(self,key):
        json_data = self._request_handler.redis.get("sess_%s" % self.session_id)
        if json_data:
            return json.loads(json_data).get(key)
        else:
            return ""

    def clear(self):
        try:
            self._request_handler.redis.delete("sess_%s" % self.session_id)
        except Exception as e:
            logging.error(e)
        self._request_handler.clear_cookie("session_id")

    def exist(self):
        return self._request_handler.redis.exists("sess_%s" % self.session_id)


def required_login(fun):
    # 保证被装饰的函数对象的__name__不变
    @functools.wraps(fun)
    def wrapper(request_handler_obj, *args, **kwargs):
        # 调用get_current_user方法判断用户是否登录
        #if not request_handler_obj.get_current_user():
        session = Session(request_handler_obj)
        if not session.get('uid'):
            self.send_error(403)
        else:
            fun(request_handler_obj, *args, **kwargs)
    return wrapper


def get_out_trade_no(goodsNum, num): #生成订单号
    MAX_TRADE_NO_COUNT = 32
    outTradeNo = datetime.now().strftime("%Y%m%d%H%M%S")
    outTradeNo += "%03d"%(int(goodsNum))
    outTradeNo += "%010d"%(int(num))
    for count in xrange(MAX_TRADE_NO_COUNT - len(outTradeNo)):
        outTradeNo += str(random.choice([0,1,2,3,4,5,6,7,8,9]))
    return outTradeNo

def log_debug(msg):
    log_name = datetime.strftime(datetime.now(),'%Y_%m_%d') + ".log"
    filename = os.path.join(LOG_PATH,log_name,)
    time_str = str(datetime.now())
    head = "[debug]["+str(time_str)+"]"
    with open(filename,'a') as f:
        f.write(head)
        f.write(msg)
        f.write('\n')

def log_info(msg):
    log_name = datetime.strftime(datetime.now(),'%Y_%m_%d') + ".log"
    filename = os.path.join(LOG_PATH,log_name)
    time_str = str(datetime.now())
    head = "[info]["+str(time_str)+"]"
    with open(filename,'a') as f:
        f.write(head)
        f.write(msg)
        f.write('\n')

def log_error(msg):
    log_name = datetime.strftime(datetime.now(),'%Y_%m_%d') + ".log"
    filename = os.path.join(LOG_PATH,log_name)
    time_str = str(datetime.now())
    head = "[error]["+str(time_str)+"]"
    with open(filename,'a') as f:
        f.write(head)
        f.write(msg)
        f.write('\n')

def redbag_log(uid,key_code,body):
    now = str(datetime.now())[:19]
    log_name = datetime.strftime(datetime.now(),'%Y_%m_%d') + ".log"
    filename = os.path.join(LOG_PATH,log_name)
    with open(filename,'a') as f:
        f.write('[%s]\n用户 %s 使用兑换码 %s 进行兑奖，兑奖结果：\n%s\n\n'%(now,uid,key_code,body))


'''
    数据回调
    @param: **key
    例如：u_dump(self, 0, 'success', data=[], coin='0')
    输出：{'msg': 'success', 'code': 0, 'data': [], 'coin': '0'}
'''
# 自行组装回调数据
def u_dump (self, code, msg='', **key):
    data = {'code': code, 'msg': msg}
    if key:
        data = dict(data, **key)
    # return json.dumps(data)
    return self.write(data)

# 成功消息回调
def u_success(self, msg, **key):
    return u_dump(self, 0, msg, **key)

# 失败消息回调
def u_error(self, msg, **key):
    return u_dump(self, 1, msg, **key)

# 跳转消息回调
def u_jump(self, url, msg='', **key):
    return u_dump(self, 0, msg, jumpUrl=url, **key)

# 新页面消息
def u_write(self, msg):
    temp = '<script>alert("{0}");</script>'.format(msg)
    self.write(temp)