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
import qrcode

from constants import *
from utils.common import *
from base import *

from tornado.web import RequestHandler
from tornado.web import RequestHandler, StaticFileHandler
from tornado.httpclient import AsyncHTTPClient
from datetime import datetime,timedelta

class MyChargeHandler(BaseHandler):

    def get_branches(self,uid):
        uid1s = self.redis.smembers('newAgent:branch:%s:set'%uid)
        uid1s = list(uid1s)
        uid2s = []
        if uid1s:
            for uid1 in uid1s:
                uset = self.redis.smembers('newAgent:branch:%s:set'%uid1)
                uid2s += list(uset)

        uid3s = []
        if uid2s:
            for uid2 in uid2s:
                uset = self.redis.smembers('newAgent:branch:%s:set'%uid2)
                uid3s += list(uset)

        uids =  uid1s + uid2s + uid3s
        return uids

    def get(self):

        start_time = self.get_argument("start_time","")
        end_time = self.get_argument("end_time","")
        isJson = self.get_argument("isJson", "")
        if not all((start_time,end_time)):
            start_time = datetime.strftime(datetime.now(),'%Y-%m-%d')
            end_time = datetime.strftime(datetime.now(),'%Y-%m-%d')
        st = datetime.strptime(start_time,'%Y-%m-%d')
        et = datetime.strptime(end_time,'%Y-%m-%d')

        date_str_list = []
        begin = st
        while begin < et + timedelta(1):
            date_str = datetime.strftime(begin,'%Y-%m-%d')
            date_str_list.append(date_str)
            begin += timedelta(1)

        charge_stream = 0

        uid = self.session.get('uid')
        isbind,parentAg = self.redis.hmget('users:%s'%uid,'isbind','parentAg')

        if not isbind:
            personal_bonus = self.redis.hget("newBonus:user:%s:hesh"%uid,'bonusPrice')
        else:
            personal_bonus = self.redis.hget("newBonus:agent:%s:hesh"%parentAg,'TotalPrice')

        if not personal_bonus:
            personal_bonus = 0

        data = []

        order_bonus_list = self.redis.lrange(ORDERS_BONUS,0,-1)
        uids = self.get_branches(uid)
        for order in order_bonus_list:
            order = order.split('|')
            tmpdata = {}
            if len(order) != 14:
                continue
            for index, key in enumerate(
                    ['Id', 'OrderNo', 'AgentId', 'AgAccount', 'ParentAg', 'MoneyNumber', 'BonusPrice',
                     'BonusPct',
                     'BeneficiaryUid', 'PayMoneyUid', 'PayType', 'AgentType', 'IsTick', 'NowTime']):
                tmpdata[key] = order[index]
            # if tmpdata['PayMoneyUid'] in uids:
            if not isbind:
                agentId = uid
            else:
                agentId = parentAg
            if tmpdata['AgentId'] == agentId:
                dic = {
                    "order_time":tmpdata['NowTime'],
                    "order_num":tmpdata['OrderNo'],
                    "player_num":tmpdata['BeneficiaryUid'],
                    "charge_money":tmpdata['MoneyNumber'],
                    "withdraw_rate":tmpdata['BonusPct'],
                    'withdraw_num':tmpdata['BonusPrice']
                }

                charge_stream += float(dic['charge_money'])
                for date_str in date_str_list:
                    if dic['order_time'].startswith(date_str):
                        data.append(dic)
                        break

        if isJson:
            u_success(self, '我的提成数据', data= data)
        else:
            self.render('my_charge.html',data=data,charge_stream=charge_stream,personal_bonus=personal_bonus)

class MyWithdrawHandler(BaseHandler):
    """
        我要提成
    """
    def get(self):
        uid = self.session.get('uid')
        res = self.db.query("select payment_time,amount_cent from withdraw_order where uid = %s",uid)
        print res
        data = []
        for row in res:
            time = str(row['payment_time'])
            money = float(row['amount_cent'])/100
            dic = {
                "time":time,
                "money":money
            }
            data.append(dic)
        self.render('my_withdraw.html',data=data)

    def post(self):
        start_time = self.get_argument("start_time")
        end_time = self.get_argument("end_time")
        if not all((start_time,end_time)):
            start_time = datetime.strftime(datetime.now(),'%Y-%m-%d')
            end_time = datetime.strftime(datetime.now(),'%Y-%m-%d')
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"

        uid = self.session.get('uid')

        res = self.db.query("select payment_time,amount_cent from withdraw_success_order where payment_time > %(start_time)s and payment_time <= %(end_time)s",start_time=str(start_time),end_time=str(end_time))
        print res
        data = []
        for row in res:
            time = str(row['payment_time'])
            money = float(row['amount_cent'])/100
            dic = {
                "time":time,
                "money":money
            }
            data.append(dic)
        u_success(self, '提成数据', data=data)
        # self.render('my_withdraw.html',data=data)

class QRcodeHandler(BaseHandler):
    def get(self):
        uid = self.session.get('uid')
        agent_id,nickname = self.redis.hmget('users:%s'%uid,"parentAg",'nickname')
        if not agent_id:
            agent_id = ""
        qr_url = "http://wx.qkgame.com.cn/?rid=gid:"+agent_id+","+uid
        self.render("qr_code.html",qr_url=qr_url,nickname=nickname,uid=uid)

class MyPlayerHandler(BaseHandler):
    """
        我的玩家
    """
    def get(self):
        search_id = self.get_argument('search_id','')
        isJson = self.get_argument('isJson','')
        my_uid = self.session.get('uid')

        agent_id,isbind = self.redis.hmget('users:%s'%my_uid,"parentAg","isbind")
        data = []
        if isbind:
            for account in self.redis.smembers("account4weixin:set"):
                user_table = self.redis.get('users:account:%s'%account)
                try:
                    parentAg = self.redis.hget(user_table,'parentAg')
                except:
                    parentAg = ""
                if agent_id == parentAg:
                    uid = user_table.split(':')[1]
                    nickname,parentAg = self.redis.hmget("users:%s"%uid,'nickname','parentAg')
                    roomcard = self.redis.get(USER4AGENT_CARD%(parentAg,uid))
                    dic = {
                        "name" : nickname,
                        "room_card":roomcard,
                        "id":uid
                    }
                    if search_id:
                        if uid == search_id:
                            data.append(dic)
                    else:
                        data.append(dic)
        else:
           for uid in self.redis.smembers("newAgent:branch:%s:set"%my_uid):
               nickname,parentAg = self.redis.hmget("users:%s"%uid,'nickname','parentAg')
               roomcard = self.redis.get(USER4AGENT_CARD%(parentAg,uid))
               dic = {
                   "name" : nickname,
                   "room_card":roomcard,
                   "id":uid
               }
               if search_id:
                   if uid == search_id:
                       data.append(dic)
               else:
                   data.append(dic)

        if isJson:
            u_success(self, '玩家查询成功', data=data)
        else:
            self.render("my_player.html",data=data)
