#coding:utf-8
import tornado.gen
import json
import xmltodict
import uuid
import random
import hashlib
import time
import requests
import sys
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('../')

from constants import *
from utils.common import *

from tornado.web import RequestHandler
from tornado.web import RequestHandler, StaticFileHandler
from tornado.httpclient import AsyncHTTPClient,HTTPRequest

from datetime import datetime

class BaseHandler(RequestHandler):
    """自定义基类"""

    @property
    def db(self):
        """作为RequestHandler对象的db属性"""
        return self.application.db

    @property
    def redis(self):
        """作为RequestHandler对象的redis属性"""
        return self.application.redis

    @property
    def bag_redis(self):
        """作为RequestHandler对象的bag_redis属性"""
        return self.application.bag_redis

    def prepare(self):
        self.session = Session(self)


class WechatHandler(BaseHandler):
    _key_pem = "/root/ds_wechat/linyunge/wx_server/cert/apiclient_key.pem"
    _cert_pem = "/root/ds_wechat/linyunge/wx_server/cert/apiclient_cert.pem"

    def prepare(self):
        signature = self.get_argument("signature")
        timestamp = self.get_argument("timestamp")
        nonce = self.get_argument("nonce")
        tmp = [WECHAT_TOKEN, timestamp, nonce]
        tmp.sort()
        tmp = "".join(tmp)
        real_signature = hashlib.sha1(tmp).hexdigest()
        if signature != real_signature:
            self.send_error(403)

    def get(self):
        echostr = self.get_argument("echostr")
        self.write(echostr)

    def post(self):
        xml_data = self.request.body
        dict_data = xmltodict.parse(xml_data)
        print '--------post------------------------'
        print dict_data
        print '--------------------------------'
        msg_type = dict_data["xml"]["MsgType"]
        if msg_type == "text":
            content = dict_data["xml"]["Content"]
            resp_data = {
                "xml": {
                    "ToUserName": dict_data["xml"]["FromUserName"],
                    "FromUserName": dict_data["xml"]["ToUserName"],
                    "CreateTime": int(time.time()),
                    "MsgType": "text",
                    "Content": content,
                }
            }
            self.openid = dict_data["xml"]["FromUserName"]
            self.check_redbag(content)
            #self.write(xmltodict.unparse(resp_data))

        elif msg_type == "event":
            if dict_data["xml"]["Event"] == "subscribe":
                """用户关注的事件"""
                resp_data = {
                    "xml": {
                        "ToUserName": dict_data["xml"]["FromUserName"],
                        "FromUserName": dict_data["xml"]["ToUserName"],
                        "CreateTime": int(time.time()),
                        "MsgType": "text",
                        "Content": u"感谢关注！",
                    }
                }
                self.write(xmltodict.unparse(resp_data))
        else:
            resp_data = {
                "xml": {
                    "ToUserName": dict_data["xml"]["FromUserName"],
                    "FromUserName": dict_data["xml"]["ToUserName"],
                    "CreateTime": int(time.time()),
                    "MsgType": "text",
                    "Content": "未识别的操作",
                }
            }
            self.write(xmltodict.unparse(resp_data))


    @tornado.gen.coroutine
    def enterprise_pay(self,content,uid,reward_value):
        openid = self.openid
        mch_appid = WECHAT_APP_ID
        mchid = WECHAT_MCHID
        nonce_str = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba123456789', 32))
        partner_trade_no = uuid.uuid4().hex
        check_name = "NO_CHECK"
        amount = 30
        desc = "新玩家领取红包"
        spbill_create_ip = "120.79.229.113"
        key = WECHAT_KEY

        send_list = ['openid', 'mch_appid', 'mchid', 'nonce_str', 'partner_trade_no', 'check_name', 'amount', 'desc',
                     'spbill_create_ip']
        send_list.sort()
        stringA = ""
        for val in send_list:
            stringA += val + "=" + str(eval(val)) + "&"

        stringA += "key=" + key
        m = hashlib.md5()
        m.update(stringA)
        sign = m.hexdigest().upper()
        send_list.append('sign')

        dic = {}
        for s in send_list:
            dic[s] = str(eval(s))
        dic = {"xml": dic}
        data = xmltodict.unparse(dic)
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"

        client = AsyncHTTPClient()
        req = HTTPRequest(
            url,
            method="POST",
            body=data,
            client_key=self._key_pem,
            client_cert=self._cert_pem
        )
        resp = yield client.fetch(req)

        print '======================='
        print resp.body
        print '======================='

        res_dic = xmltodict.parse(resp.body)
        # 新玩家红包领取成功 改变new_sign状态
        if res_dic['xml']['result_code'] == "SUCCESS":
            self.redis.hset('users:%s'%uid,'new_sign','3')
        self.check_success(res_dic, uid, content)

    @tornado.gen.coroutine
    def check_redbag(self,content):

        sql = "select uid,reward_value from reward_record where key_code = %s and status = 0 and item_id = 4"
        res = self.db.get(sql,content)
        if not res:
            log_info(content)
            return

        uid = res.get('uid')
        reward_value = int(res.get('reward_value'))
        # 单笔低于1元使用企业付款到零钱
        print '----------reward value---------------------------------------'
        print reward_value
        print type(reward_value)
        print '-------------------------------------------------'
        if int(reward_value) < 100:
            self.enterprise_pay(content,uid,reward_value)
            return

        nonce_str = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba123456789', 32))
        mch_billno = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba123456789', 28))
        mch_id = WECHAT_MCHID
        wxappid = WECHAT_APP_ID
        send_name = "东胜游戏"
        re_openid = self.openid
        total_amount = reward_value#100
        total_num = 1
        wishing = "恭喜发财！"
        client_ip = "120.79.229.113"
        act_name = "东胜棋牌"
        remark = "no"
        #scene_id = "PRODUCT_3"
        key = WECHAT_KEY

        send_list = [
            'nonce_str',
            'mch_billno',
            'mch_id',
            'wxappid',
            'send_name',
            're_openid',
            'total_amount',
            'total_num',
            'wishing',
            'client_ip',
            'act_name',
            'remark',
            #'scene_id'
        ]
        send_list.sort()
        stringA = ""
        for val in send_list:
            stringA += val + "=" + str(eval(val)) + "&"

        stringA += "key=" + key
        m = hashlib.md5()
        m.update(stringA)
        sign = m.hexdigest().upper()
        send_list.append('sign')

        dic = {}
        for s in send_list:
            dic[s] = str(eval(s))

        dic = {"xml":dic}
        data = xmltodict.unparse(dic,pretty=True)
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack"
        print data

        client =  AsyncHTTPClient()
        req = HTTPRequest(
            url,
            method="POST",
            body=data,
            client_key=self._key_pem,
            client_cert=self._cert_pem
        )

        resp = yield client.fetch(req)

        print '---------resp body-----------------'
        print resp.body
        print '--------------------------'
        redbag_log(uid,content,resp.body)
        res_dic = xmltodict.parse(resp.body)
        self.check_success(res_dic,uid,content)

    def check_success(self,res_dic,uid,content):
        if res_dic['xml']['result_code'] == "SUCCESS":
            now = datetime.now()
            auto = "WEIXIN auto deliver"
            sql = 'update reward_record set status=1,deliver_time =%s,card_no=%s,card_pwd=%s where key_code = %s'
            self.db.execute(sql,now,auto,auto,content)
            print 'ok!'

class ProfileHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        unionid =self.session.get('unionid')
        if unionid:
            res = self.check_unionid(unionid)
            if res == "1":
                # self.render("not_our_user.html")
                u_write(self, '您还不是我们的用户，请先登录游戏')
                return
            elif res == "2":
                # self.render("not_agent.html")
                u_write(self, '您还不是代理，请先成为代理')
                return

            self.render("cash_index.html",**res)

        code = self.get_argument("code")
        client = AsyncHTTPClient()
        url = "https://api.weixin.qq.com/sns/oauth2/access_token?" \
                  "appid=%s&secret=%s&code=%s&grant_type=authorization_code" % (WECHAT_APP_ID, WECHAT_APP_SECRET, code)
        # 使用异步客户端,通过code或者refresh_token获取token
        resp = yield client.fetch(url)
        dict_data = json.loads(resp.body)
        if "errcode" in dict_data:
            # self.write("error occur")
            u_write(self, 'error occur')
        else:
            access_token = dict_data.get('access_token')
            open_id = dict_data["openid"]
            # 获取成功则将token等信息保存在session中
            url = "https://api.weixin.qq.com/sns/userinfo?" \
                  "access_token=%s&openid=%s&lang=zh_CN" % (access_token, open_id)
            resp = yield client.fetch(url)
            user_data = json.loads(resp.body)
            if "errcode" in user_data:
                u_write(self, 'error occur again')
                # self.write("error occur again")
            else:
                openid = user_data['openid']
                unionid = user_data['unionid']
                res = self.check_unionid(unionid)
                if res == "1":
                    u_write(self, '您还不是我们的用户，请先登录游戏！')
                    # self.render("not_our_user.html")
                    return
                elif res == "2":
                    u_write(self, '您还不是代理，请先成为代理')
                    # self.render("not_agent.html")
                    return
                if res:
                    self.session.set("openid",openid)
                    self.session.set("unionid",unionid)
                    self.session.set("uid",res['uid'])
                    self.render("cash_index.html",**res)
                else:
                    u_write(self, 'undefined error')
                    # self.write('undefined error')

    def check_unionid(self,unionid):
        try:
            realAccount = self.redis.get(WEIXIN2ACCOUNT % (unionid))
            # 不是游戏用户
            if not realAccount:
                return "1"
            account2user_table = FORMAT_ACCOUNT2USER_TABLE % (realAccount)
            user_table = self.redis.get(account2user_table)

            uid = user_table.split(':')[1]
            nickname,headImgUrl,isAgent,phone,agent_id,isbind = self.redis.hmget(user_table,"nickname","headImgUrl","isAgent","phone",'parentAg','isbind')
            # 不是代理
            if not isAgent :
                return "2"

            zuid = self.redis.hget('agents:id:%s'%agent_id,'uid')
            if zuid == uid:
                agent_rank = "总代理"
                my_earning = self.redis.hget("newBonus:agent:%s:hesh" % agent_id, 'TotalPrice')
            else:
                agent_rank = "代理"
                my_earning = self.redis.hget("newBonus:user:%s:hesh" % uid, 'bonusPrice')

            if not my_earning:
                my_earning = 0

            notice_id = self.redis.lindex("notice:list",0)
            title,time,content = self.redis.hmget("notice:%s"%notice_id,"title","time","content")

        except Exception as e:
            print e
            return None
        else:
            res = {"uid":uid,"nickname":nickname,"headImgUrl":headImgUrl,"phone":phone,"agent_rank":agent_rank,"title":title,"time":time,"content":content,"my_earning":my_earning}
            return res