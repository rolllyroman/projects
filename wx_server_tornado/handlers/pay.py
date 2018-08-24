#coding:utf-8
import random
import uuid
import hashlib
import xmltodict
import requests
import tornado.gen
import time
import json
import sys
sys.path.append('../')

from constants import *
from base import BaseHandler
from tornado.httpclient import AsyncHTTPClient,HTTPRequest
from utils.common import *
from datetime import datetime

class CashTakeHandler(BaseHandler):
    """
        提现
    """
    _key_pem = "/root/weixin/web_server/quekang/cert/apiclient_key.pem"
    _cert_pem ="/root/weixin/web_server/quekang/cert/apiclient_cert.pem"

    def get(self):
        uid = self.session.get("uid")
        wr = self.get_argument('withdraw_res','')
        if not uid:
            self.send_error(403)
            return

        c_take,a_take = 0,0
        isbind,parentAg = self.redis.hmget('users:%s'%uid,'isbind','parentAg')
        if isbind:
            c_take,a_take = self.redis.hmget('newBonus:agent:%s:hesh'%parentAg,'CurPrice','accumateBonus')
        elif self.redis.exists(USER_BONUS%uid):
            c_take,a_take = self.redis.hmget(USER_BONUS%uid,'CurBonusPrice','accumateBonus')

        if not a_take:
            a_take = "0.00"
        if not c_take:
            c_take = "0.00"

        self.render("cash_take.html",c_take=c_take,a_take=a_take,wr=wr)

    def check_withdraw_can(self,uid,money):
        wd = str(datetime.now().weekday())
        today = str(datetime.strftime(datetime.now(),'%Y-%m-%d'))+"%"
        '''
        if wd == "3" or wd == "4":
            pass
        else:
            return False,"提现失败，仅提供在每周四周五可进行提现！"
        '''

        try:
            sql = "select amount_cent from withdraw_order where uid = %s and payment_time like %s and result = 1"
            res = self.db.query(sql,uid,today)
            day_sum_cent = 0
            for row in res:
                ac = row['amount_cent']
                if ac:
                    ac = float(ac)
                else:
                    ac = 0
                day_sum_cent += ac
            today_draw = float(day_sum_cent)/100
            money = float(money)
            if today_draw + money > 5000:
                return False,"提现失败，当日最大提现额为5000元！"
        except Exception as e:
            log_debug(str(datetime.now())+"---[check_withdraw_can]"+str(e))
            return False,"提现失败，提现功能维护中!"
        else:
            return True,"ok"


    def check_money_valid(self,money):
        try:
            money = float(money)
            if money <= 5000 and money > 0:
                pass
            else:
                return False,"提现失败，一次提现只能0到5000元之间"
        except Exception as e:
            print '=================check_money================'
            print str(e)
            print '=================check_money================'
            return False,'非法输入'
        else:
            return True,'ok'

    @tornado.gen.coroutine
    def post(self):

        uid = self.session.get("uid")
        money = self.get_argument('money','')
        res = self.check_money_valid(money)
        if not res[0]:
            u_error(self, res[1])

        res = self.check_withdraw_can(uid,money)
        if not res[0]:
            u_error(self, res[1])
            raise tornado.gen.Return()

        if self.redis.get('short:forbid:user:%s'%uid):
            u_error(self, '您的提现过于频繁，请稍等一会！')
            raise tornado.gen.Return()

        self.redis.setex('short:forbid:user:%s'%uid,10,10)

        if not money:
            # self.write("请填写正确的金额！")
            u_error(self, '请填写正确的金额！')
            raise tornado.gen.Return()
        else:
            try:
                money_cent = int(float(money)*100)
            except Exception as e:
                # self.write("格式不正确")
                u_error(self, '格式不正确')
                raise tornado.gen.Return()

        if not self.check_have_money(uid,money_cent):
            # self.write("你的余额不够！")
            u_error(self, '你的余额不够')
            raise tornado.gen.Return()

        openid = self.session.get("openid")
        mch_appid = WECHAT_APP_ID
        mchid = WECHAT_MCHID
        nonce_str = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba123456789',32))
        partner_trade_no = uuid.uuid4().hex
        check_name = "NO_CHECK"
        amount = money_cent
        desc = "代理提现"
        spbill_create_ip = "120.79.229.113"
        key = WECHAT_KEY

        send_list = ['openid','mch_appid','mchid','nonce_str','partner_trade_no','check_name','amount','desc','spbill_create_ip']
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
        data = xmltodict.unparse(dic)
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"

        client = AsyncHTTPClient()
        req = HTTPRequest(
            url,
            method="POST",
            body = data,
            client_key=self._key_pem,
            client_cert=self._cert_pem
        )
        resp = yield  client.fetch(req)

        res_dic = xmltodict.parse(resp.body)
        res = self.check_success(res_dic,amount)
        if res:
            # self.redirect('/cash/take?withdraw_res=1')
            u_jump(self, '/cash/take?withdraw_res=1')
        else:
            # self.write('提现失败！')
            try:
                # res = str(res_dic['xml']['return_msg'])
                if res_dic['xml']['err_code'] == "NOTENOUGH":
                    res = "商户可用提现余额不足，请不要着急，建议联系客服处理。"
                elif res_dic['xml']['err_code'] == "SENDNUM_LIMIT":
                    res =  "提现次数超出3次，提示：已达到单日最大提现次数，请改天再来。"
            except Exception as e:
                print '----except-----------'
                print str(e)
                print '---------------'
                res = "提现失败!"
            u_error(self,res)

    def check_have_money(self,uid,money_cent):
        isbind,parentAg = self.redis.hmget('users:%s'%uid,'isbind','parentAg')
        if not isbind:
            c_take = self.redis.hget(USER_BONUS%uid,'CurBonusPrice')
        else:
            c_take = self.redis.hget("newBonus:agent:%s:hesh"%parentAg,'CurPrice')
        if not c_take:
            return False
        c_take = int(float(c_take)*100)
        print c_take
        if money_cent > c_take:
            return False
        else:
            return True

    def check_success(self,res_dic,amount):
        print '--------------------check_success---------------------'
        print res_dic
        print '--------------------res_dic---------------------'
        uid = self.session.get("uid")
        openid = self.session.get("openid")
        isbind,parentAg = self.redis.hmget('users:%s'%uid,'isbind','parentAg')
        if res_dic['xml']['return_code'] == "SUCCESS" and res_dic['xml']['result_code'] == "SUCCESS":
            if isbind:
                c_take,a_take = self.redis.hmget("newBonus:agent:%s:hesh"%parentAg,'CurPrice','accumateBonus')
            else:
                c_take,a_take = self.redis.hmget(USER_BONUS%uid,'CurBonusPrice','accumateBonus')
            if not a_take:
                a_take = 0
            withdraw = float(amount)/100
            res_c = round(float(c_take) - withdraw,3)
            res_a = round(float(a_take) + withdraw,3)
            if not isbind:
                self.redis.hset(USER_BONUS%uid,'CurBonusPrice',res_c)
                self.redis.hset(USER_BONUS%uid,'accumateBonus',res_a)
            else:
                self.redis.hmset("newBonus:agent:%s:hesh"%parentAg,{"accumateBonus":res_a,"CurPrice":res_c})

            sql = "insert into withdraw_order(uid,payment_time,amount_cent,payment_no,openid,result) values(%s,%s,%s,%s,%s,%s)"
            self.db.execute(sql,uid,str(res_dic['xml']['payment_time']),amount,res_dic['xml']['payment_no'],openid,1)
            return True
        else:
            this_time = datetime.strftime(datetime.now(),'%Y-%m-%d')
            sql = "insert into withdraw_order(uid,payment_time,amount_cent,error_msg,result) values(%s,%s,%s,%s,%s)"
            self.db.execute(sql,uid,this_time,amount,str(res_dic['xml']['return_msg']),0)
            return False

class ChargeHandler(BaseHandler):
    """
        充值
    """
    @tornado.gen.coroutine
    def get(self):
        unionid = self.session.get('unionid')
        if unionid:
            res = self.check_unionid(unionid)
            if res:
                self.render("charge.html", **res)

        code = self.get_argument("code")
        client = AsyncHTTPClient()
        url = "https://api.weixin.qq.com/sns/oauth2/access_token?" \
              "appid=%s&secret=%s&code=%s&grant_type=authorization_code" % (WECHAT_APP_ID, WECHAT_APP_SECRET, code)
        # 使用异步客户端,通过code或者refresh_token获取token
        resp = yield client.fetch(url)
        dict_data = json.loads(resp.body)
        if "errcode" in dict_data:
            # self.write("请重新登录！")
            u_write(self, "请重新登录！")
        else:
            access_token = dict_data.get('access_token')
            open_id = dict_data["openid"]
            url = "https://api.weixin.qq.com/sns/userinfo?" \
                  "access_token=%s&openid=%s&lang=zh_CN" % (access_token, open_id)
            resp = yield client.fetch(url)
            user_data = json.loads(resp.body)
            if "errcode" in user_data:
                # self.write("error occur again")
                u_write(self, 'error occur again')
            else:
                openid = user_data['openid']
                unionid = user_data['unionid']
                res = self.check_unionid(unionid)
                if res:
                    self.session.set('openid',openid)
                    self.session.set('unionid',unionid)
                    self.session.set('uid',res['uid'])
                    self.render("charge.html", **res)
                    # u_success(self, '成功', data=res)
                else:
                    # self.write('no msg')
                    u_write(self, '您还不是我们的用户，请先登录游戏')

    def check_unionid(self,unionid):
        try:
            #if self.redis.exists(WEIXIN2ACCOUNT % (unionid)):
            realAccount = self.redis.get(WEIXIN2ACCOUNT % (unionid))
            account2user_table = FORMAT_ACCOUNT2USER_TABLE % (realAccount)
            user_table = self.redis.get(account2user_table)

            uid = user_table.split(':')[1]
            #user_info = self.redis.hgetall(user_table)
            nickname,headImgUrl,agent1st = self.redis.hmget(user_table,"nickname","headImgUrl",'1stAgent')
            if not agent1st:
                agent1st = ""

        except Exception as e:
            return None
        else:
            return {"uid":uid,"nickname":nickname,"headImgUrl":headImgUrl,"agent1st":agent1st}

    def get_trade_and_goods(self,goodsId,charge_uid):

        uid = charge_uid
        group_id = self.redis.hget('users:%s'%uid,'parentAg')

        goodsTable = GOODS_TABLE % (goodsId)
        cards, goodsName, present_card = self.redis.hmget(goodsTable, ('cards', 'name', 'present_cards'))
        rType, price = self.redis.hmget(goodsTable, 'type', 'price')
        rType = int(rType) if rType else 0
        # test change
        if rType == 2 or 1 == 1:
            goodsPrice = float(price)
        else:
            # 判断金币价格
            goodsPrice = self.getGoodsMoney(group_id, cards)
        goodsId2OrderId = GOODS_NUM % (goodsId)
        orderIndex = self.redis.incr(goodsId2OrderId)
        if orderIndex >= 10000000000:
            self.redis.set(goodsId2OrderId, 0)
            orderIndex = self.redis.incr(goodsId2OrderId)
        outTradeNo = get_out_trade_no(goodsId, orderIndex)
        return outTradeNo,goodsName,goodsPrice,cards,present_card

    def getGoodsMoney(self,groupId, cardNums):
        """
        获取每个玩家所在公会的价格
        """
        companyId = self.getTopAgentId(groupId)
        log_debug('[getGoodsMoney] groupId[%s] cardNums[%s] companyId[%s]' % (groupId, cardNums, companyId))
        unitPrice = self.redis.hget(AGENT_TABLE % (companyId), 'unitPrice')
        print AGENT_TABLE % (companyId)
        print 'unitPrice', unitPrice
        return int(cardNums) * round(float(unitPrice), 2)

    def getTopAgentId(self,agentId):
        """
        获取总公司ID
        """
        agType = self.redis.hget(AGENT_TABLE % (agentId), 'type')
        if agType in ['0', '1']:
            return agentId

        while 1:
            agentId = self.redis.hget(AGENT_TABLE % (agentId), 'parent_id')
            agType = self.redis.hget(AGENT_TABLE % (agentId), 'type')
            try:
                if int(agType) == 1:
                    return agentId
            except:
                log_info('[try getTopAgentId] agentId[%s] agentType[%s]' % (agentId, agType))
                return agentId

    def check_invite_code(self,invite_code,charge_uid):
        pay_uid = self.session.get('uid')
        uid = self.session.get('uid')
        amAgent,ambind = self.redis.hmget('users:%s'%uid,'isAgent','isbind')
        charge_account,agent1st = self.redis.hmget('users:%s'%charge_uid,'account','1stAgent')
        isAgent,isbind = self.redis.hmget('users:%s'%invite_code,'isAgent','isbind')

        # 如果充值uid是不存在的玩家
        if not charge_account:
            return False,"该充值用户不存在!"

        # 如果邀请码不为空，则必须是个代理,并不能是总代
        if invite_code:
            if not isAgent or isbind:
                return False,"只能输入代理id，不能输入总代或普通玩家id!"

        # 总代/代理/玩家 给自己/他人充值 填写/不填写邀请码
        if ambind:
            if pay_uid == uid:
                if invite_code:
                    return False,"系统检测到您是总代理，不可填写邀请码！"
                else:
                    return True,"ok"
            else:
                if invite_code:
                    return False,"系统检测到您是代理，不可填写邀请码！"
                else:
                    return True,"ok"

        elif amAgent:
            if pay_uid == uid:
                if invite_code:
                    return False,"系统检测到您是代理，不可填写邀请码！"
                else:
                    return True,"ok"
            else:
                if invite_code:
                    return False,"系统检测到您在给他人充值，不可填写邀请码！"
                else:
                    return True,"ok"
        else:
            if pay_uid == uid:
                if invite_code:
                    s_data = uid + ":" + invite_code
                    self.redis.setex('change_senior:session:account:%s'%charge_account,s_data,300)
                    return True,"ok"
                else:
                    s_data = uid + ":null"
                    self.redis.setex('change_senior:session:account:%s'%charge_account,s_data,300)
                    return True,"ok"
            else:
                if invite_code:
                    return False,"系统检测到您在给他人充值，不可填写邀请码！"
                else:
                    return True,"ok"


    @tornado.gen.coroutine
    def post(self):

        pay_uid = self.session.get('uid')
        charge_uid = self.get_argument('charge_uid')
        goodsId = self.get_argument('goods_id')
        invite_code = self.get_argument('invite_code','')
        res = self.check_invite_code(invite_code,charge_uid)
        if not res[0]:
            # self.write("<script>alert('不符合条件,无法充值');window.history.back();</script>")
            u_error(self,res[1])
            raise tornado.gen.Return()

        out_trade_no,goodsName,goodsPrice,cards,present_card = self.get_trade_and_goods(goodsId,charge_uid)
        appid = WECHAT_APP_ID
        mch_id = WECHAT_MCHID
        nonce_str = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba123456789',32))
        body = "房卡X"+str(int(cards)+int(present_card if present_card else 0))
        # 金额
        print '----------totalfee---------------'
        print goodsPrice
        print '----------totalfee---------------'
        total_fee = int(float(goodsPrice)*100)
        spbill_create_ip = "120.79.229.113"
        trade_type = "JSAPI"
        openid = self.session.get("openid")
        notify_url = "agent.qkgame.com.cn/notify"
        key = WECHAT_KEY

        send_list = ['appid','mch_id','nonce_str','body','out_trade_no','total_fee','spbill_create_ip','trade_type','openid','notify_url']
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

        data = xmltodict.unparse(dic).encode('utf-8')
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        client = AsyncHTTPClient()
        req = HTTPRequest(
            url,
            method="POST",
            body=data,
        )

        # 发送请求获取prepayid
        resp = yield client.fetch(req)
        print '--------------'
        print resp.body
        print '--------------'
        res_dic = xmltodict.parse(resp.body)
        prepay_id = res_dic["xml"]["prepay_id"]
        timeStamp = int(time.time())
        package = "prepay_id=" + str(prepay_id)
        signType = "MD5"
        appId = WECHAT_APP_ID
        nonceStr=nonce_str

        jssdk_list = ['appId','nonceStr','timeStamp','package','signType']
        jssdk_list.sort()
        stringA = ""
        for val in jssdk_list:
            stringA += val + "=" + str(eval(val)) + "&"

        stringA += "key=" + key
        m = hashlib.md5()
        m.update(stringA)
        paySign = m.hexdigest().upper()
        self.add_order_to_pending(nonceStr,prepay_id,goodsName,total_fee,goodsId,cards,present_card,out_trade_no,paySign,charge_uid)

        u_success(self, '请求成功', data={'signType':signType, 'appId':appId,'timeStamp':str(timeStamp),'nonceStr':nonceStr,'package':package,'paySign':paySign})


    def add_order_to_pending(self,nonceStr,prepay_id,goodsName,total_fee,goodsId,cards,present_card,outTradeNo,sign,charge_uid):

        ip = self.request.remote_ip
        uid = charge_uid
        pay_money_uid = self.session.get('uid')
        group_id,account = self.redis.hmget('users:%s'%uid,'parentAg','account')

        serverIp = self.request.remote_ip
        pipe = self.redis.pipeline()
        orderTable = ORDER_TABLE % (outTradeNo)
        timeStamp = str(int(time.time()))
        pipe.hmset(orderTable,
                   {
                       'time': timeStamp,
                       'sign': sign,
                       'nonceStr': nonceStr,
                       'prepayID': prepay_id,
                       'name': goodsName,
                       'body': "123",
                       'money': int(float(total_fee)),
                       'startTime': timeStamp,
                       'account': account,
                       'num': goodsId,
                       'type': 'pending',
                       'roomCards': cards,
                       'presentCards': present_card,
                       'PayMoneyUid'  : pay_money_uid ,
                       'PayTpe'    : "1"
                   }
                   )
        pipe.sadd(PENDING_ORDER, outTradeNo)
        pipe.lpush(ORDER_NUM_LIST, outTradeNo)
        pipe.sadd(PLAYER_ORDER % (account), outTradeNo)

        curTime = datetime.now()
        pipe.lpush(DAY_ORDER % (curTime.strftime("%Y-%m-%d")), outTradeNo)
        pipe.lpush(DAY_PENDING_ORDER % (curTime.strftime("%Y-%m-%d")), outTradeNo)
        pipe.expire(orderTable, 1 * 60 * 60)
        pipe.execute()

class NotifyHandler(BaseHandler):

    def post(self):
        body = self.request.body
        params = xmltodict.parse(body)
        params = params['xml']
        recv_sign = params['sign']
        order_no = params['out_trade_no']

        check_list = []
        for k,v in params.items():
            check_list.append(k)

        check_list.sort()
        check_list.remove('sign')
        stringA = ""
        for xml_key in check_list:
            stringA += xml_key + "=" + str(params[xml_key]) + "&"

        stringA += "key=" + WECHAT_KEY
        m = hashlib.md5()
        m.update(stringA)
        real_sign = m.hexdigest().upper()

        res = "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
        ss_set = self.redis.smembers("success:sign:set")
        oo_set = self.redis.smembers("operated:orderNo:set")
        if real_sign != recv_sign or real_sign in ss_set or order_no in oo_set:
            print 'sign error or repeat request'
            self.write(res)
            return
        else:
            self.redis.sadd("success:sign:set",real_sign)
            self.redis.sadd("operated:orderNo:set",order_no)

        if not self.verfiy_recv_data(params):
            print 'veryfy recv data error'
            self.write(res)
            return

        self.addRoomCard2Member(self.redis,params['out_trade_no'])

        item = {
            'return_code': 'SUCCESS',
            'return_msg': '支付成功'
        }
        res = self.transDict2Xml(item)
        print '=============================='
        print res
        print '=============================='
        self.write(res)

    def transDict2Xml(self,data):
        """
            将 dict 对象转换成微信支付交互所需的 XML 格式数据
        """
        xml = []
        for k in sorted(data.keys()):
            v = data.get(k)
            if not v.startswith('<![CDATA['):
                v = '<![CDATA[{}]]>'.format(v)
            xml.append('<{key}>{value}</{key}>'.format(key=k, value=v))
        return '<xml>{}</xml>'.format(''.join(xml))

    def verfiy_recv_data(self,params):
        """
            校验支付数据
        """
        curTime = datetime.now()
        orderTable = ORDER_TABLE%(params['out_trade_no'])
        if not self.redis.exists(orderTable):
            log_debug('[%s][wechatPay][error] orderNo[%s] is not exists.'%(curTime,params['out_trade_no']))
            return False

        updateInfo = {
                'money'         :       params['total_fee'],
                'endTime'       :       params['time_end'],
                'currency'      :       params['fee_type'],
                'orderNum'      :       params['transaction_id'],
                'type'          :       'successful',
        }

        pipe = self.redis.pipeline()
        try:
            log_debug('[%s][wechatPay][info] update orderInfo[%s] success.'\
                                        %(curTime,updateInfo))
            pipe.hmset(orderTable,updateInfo)
            pipe.srem(PENDING_ORDER,orderTable)
            pipe.sadd(SUCCEED_ORDER,orderTable)
            pipe.persist(orderTable)
            pipe.execute()
        except:
            log_debug('[%s][wechatPay][error] update orderInfo[%s] error.'%(curTime,updateInfo))
            return False

        return True

    def handle_invite_code(self,account):
        s_data = self.redis.get("change_senior:session:account:%s"%account)

        # 如果不存在，则不发生改变
        if not s_data:
            return

        uid = s_data.split(':')[0]
        invite_code = s_data.split(':')[1]
        if invite_code == 'null':
            self.cancel_agent(self.redis,uid)
            return

        self.change_my_1st(uid,invite_code)

        # 清理
        self.redis.delete("change_senior:session:account:%s"%account)

    def cancel_agent(self,redis,uid):
        userTable = FORMAT_USER_TABLE % uid
        Agent1st, isAgent, isbind = redis.hmget(userTable, '1stAgent', 'isAgent', 'isbind')
        if Agent1st:
            # 移除上级代理的成员列表中的自己
            print '上级代理为%s' % Agent1st
            redis.srem(AGENT_BRANCH % Agent1st, uid)
        else:
            print 'cancelAgent isAgent(%s) isbind(%s)' % (isAgent, isbind)
            redis.hdel(userTable, 'isAgent', 'isbind')
            # if isAgent or isbind:
            #     return {'code':0,'msg':'没有绑定代理,取消自己代理身份成功'}
            # return {'code':-1,'msg':'当前用户未绑定代理'}
            return {'code': 0, 'msg': '取消代理成功'}
        branch_1_users = redis.smembers(AGENT_BRANCH % uid)
        print '下1级成员列表为%s' % branch_1_users
        for _branch1_uid in branch_1_users:
            # 移除下1级成员的代理绑定关系
            redis.hdel(FORMAT_USER_TABLE % _branch1_uid, '1stAgent', '2ndAgent', '3rdAgent', 'isbind')

            branch_2_users = redis.smembers(AGENT_BRANCH % _branch1_uid)
            print '下2级成员列表为%s' % branch_2_users
            for _branch2_uid in branch_2_users:
                redis.hdel(FORMAT_USER_TABLE % _branch2_uid, '1stAgent', '2ndAgent', '3rdAgent', 'isbind')

                branch_3_users = redis.smembers(AGENT_BRANCH % _branch2_uid)
                print '下3级成员列表为%s' % branch_3_users
                for _branch3_uid in branch_3_users:
                    redis.hdel(FORMAT_USER_TABLE % _branch3_uid, '1stAgent', '2ndAgent', '3rdAgent', 'isbind')

        redis.hdel(userTable, 'isAgent', '1stAgent', '2ndAgent', '3rdAgent', 'isbind')

    def change_my_1st(self,uid,new_agent1st):
        self.cancel_agent(self.redis,uid)
        agent2nd,agent3rd,parentAg = self.redis.hmget('users:%s'%new_agent1st,'1stAgent','2ndAgent','parentAg')
        print 'change my 1st'
        print uid
        print new_agent1st
        print agent2nd
        print agent3rd
        print 'change my 1st'
        self.redis.hmset('users:%s'%uid,{
            '1stAgent':new_agent1st,
            '2ndAgent':agent2nd if agent2nd else "",
            '3rdAgent':agent3rd if agent3rd else "",
        })
        self.redis.sadd(AGENT_BRANCH %new_agent1st, uid)

    def addRoomCard2Member(self, redis, transNo):
        """
            会员增加房卡
        """
        curTime = datetime.now()
        orderTable = ORDER_TABLE % (transNo)
        if not redis.exists(orderTable):
            print('[%s][wechatPay][error] orderNo[%s] is not exists.' % (curTime, params['out_trade_no']))
            return False

        goodid, memberAccount = redis.hmget(orderTable, ('num', 'account'))
        # 处理邀请码 更改上级
        self.handle_invite_code(memberAccount)

        rType = redis.hget(GOODS_TABLE % goodid, 'type')
        rType = int(rType) if rType else None
        if rType == 2:
            addRoomCard2Member4Type2(redis, curTime, orderTable, memberAccount)
            return
        print 'orderTable', orderTable
        cardNums, present_card, money = redis.hmget(orderTable, ('roomCards', 'presentCards', 'money'))
        print '[AdminAddRoomCard2Member] 钻石数:[%s],赠送钻石数:[%s],充值金额:[%s]' % (cardNums, present_card, money)

        try:
            money = float(money) * 0.01
        except:
            money = 0.0
        try:
            present_card = int(present_card)
        except:
            present_card = 0

        account2user_table = FORMAT_ACCOUNT2USER_TABLE % (memberAccount)  # 从账号获得账号信息，和旧系统一样
        userTable = redis.get(account2user_table)

        id = userTable.split(':')[1]
        groupId, totalPay, isAgent = redis.hmget(userTable, 'parentAg', "totalPay", "isAgent")
        print 'isAgent', isAgent
        try:
            totalPay = float(totalPay)
        except Exception, error:
            totalPay = 0.0

        pipe = redis.pipeline()
        # 记录玩家的总充值金额
        pipe.hincrbyfloat(userTable, "totalPay", money)

        # 记录玩家订单号
        redis.lpush(USER_ORDER_list % (id), transNo)

        becomeAgent = 0
        if not isAgent:
            # 判断是否满足成为代理的金额
            totalPay = totalPay + money
            fullLimit = redis.hget(GLOBAL_BONUS_PCT, "fullLimit") or 300
            fullLimit = float(fullLimit)
            print '总充值为%s,成为代理需充值的金额为%s' % (totalPay, fullLimit)
            if totalPay >= fullLimit:
                # 成为代理
                pipe.hset(userTable, 'isAgent', '1')
                '''创建市级代理'''
                becomeAgent = 1
        else:
            becomeAgent = 2
        ################################################################
        pipe.incrby(USER4AGENT_CARD % (groupId, id), (int(cardNums) + present_card))
        # 记录充值卡总额
        if not redis.exists(USER4AGENT_RECHARGE % (groupId, id)):
            pipe.set(USER4AGENT_RECHARGE % (groupId, id), 0)
        pipe.incrby(USER4AGENT_RECHARGE % (groupId, id), int(cardNums))
        CardMoney = self.getCardMoney( groupId)
        print('[%s][wechatPay] recharge CardMoney[%s]' % (curTime, CardMoney))
        pipe.execute()
        ################################新增#############################
        self.New_countRateOfAgent(redis, userTable, transNo, money, becomeAgent)
        ################################################################
        return becomeAgent


    # changed
    def New_countRateOfAgent(self,redis,userTable, transNo, MoneyNumber, becomeAgent):
        '''
        计算分红
        :param redis:
        :param userTable:充值的玩家key
        :param transNo: 订单号
        :param MoneyNumber: 充值金额
        :return:
        '''
        # MoneyNumber *= 0.01
        orderTable = ORDER_TABLE % (transNo)
        UID = userTable.split(':')[1]

        date_time = datetime.now()
        now_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
        print(
            '[HALLFUNC][countRateOfAgent][info] userTable[%s] MoneyNumber[%s] orderTable[%s] becomeAgent[%s]' %
            (userTable, MoneyNumber, orderTable, becomeAgent))

        PayMoneyUid, PayType = redis.hmget(orderTable, ('PayMoneyUid', 'PayType'))
        try:
            PayMoneyUid = int(PayMoneyUid)
            PayType = int(PayType)
        except Exception as error:
            # traceback.print_exc()
            PayMoneyUid = UID
            PayType = 0

        print 'PayMoneyUid', PayMoneyUid
        print 'PayType', PayType

        curTime = datetime.now()
        date = curTime.strftime("%Y-%m-%d")

        if not redis.exists(GLOBAL_BONUS_PCT):
            print '代理分红比例不存在'
            redis.hmset(GLOBAL_BONUS_PCT,
                        {'BonusPct1st': 0.50, 'BonusPct2nd': 0.20, 'BonusPct3rd': 0.05, 'fullLimit': 300})

        BonusPct1st, BonusPct2nd, BonusPct3rd = redis.hmget(GLOBAL_BONUS_PCT, 'BonusPct1st', 'BonusPct2nd',
                                                            'BonusPct3rd')

        for attr in ['BonusPct1st', 'BonusPct2nd', 'BonusPct3rd']:
            try:
                exec ('%s = float(%s)' % (attr, attr))
            except:
                exec ('%s = 0.0' % (attr))

        if becomeAgent != 0:  # 代理充值
            BonusPct1st = BonusPct2nd
            BonusPct2nd = BonusPct3rd
            BonusPct3rd = 0.0

        print '充值玩家为%s' % ('普通玩家' if not becomeAgent else ('代理' if becomeAgent == 2 else '准代理'))
        print '1级代理分红为%s' % (BonusPct1st)
        print '2级代理分红为%s' % (BonusPct2nd)
        print '3级代理分红为%s' % (BonusPct3rd)

        print 'userTable为%s' % userTable
        Agent1st, Agent2nd, Agent3rd, myparentAg = redis.hmget(userTable, '1stAgent', '2ndAgent', '3rdAgent',
                                                               'parentAg')
        print '1级代理为%s' % Agent1st
        print '2级代理为%s' % Agent2nd
        print '3级代理为%s' % Agent3rd
        print '工会号为%s' % myparentAg

        pipe = redis.pipeline()

        Agent1stPrice = Agent2stPrice = Agent3rdPrice = 0.0
        str_data_1st = str_data_2nd = str_data_3rd = ''

        # boss属性
        BossBonusPct = 1.0
        AgentBossPrice = MoneyNumber
        MoneyNumber = float(MoneyNumber)

        sql_list = []

        if Agent1st and BonusPct1st:
            # 代理分红表
            agent1st = USER_BONUS % Agent1st
            Agent1stPrice = round((MoneyNumber * BonusPct1st), 3)
            pipe.hincrbyfloat(agent1st, 'fromAgent1st', Agent1stPrice)
            pipe.hincrbyfloat(agent1st, 'bonusPrice', Agent1stPrice)
            pipe.hincrbyfloat(agent1st, 'CurBonusPrice', Agent1stPrice)
            # boss比例
            BossBonusPct -= BonusPct1st
            AgentBossPrice -= Agent1stPrice
            # 充值分红记录
            Agent1stAccount, parentAg1st = redis.hmget(FORMAT_USER_TABLE % (Agent1st), 'account', 'parentAg')
            parentAg1st = parentAg1st if parentAg1st else '无'
            Primary_Key_1st = redis.incr(ORDERS_BONUS_NUM)
            data_1st = [Primary_Key_1st, transNo, Agent1st, Agent1stAccount, parentAg1st,
                        MoneyNumber, Agent1stPrice, BonusPct1st, UID, PayMoneyUid, PayType, 1, 0, now_time, ]

            str_data_1st = "|".join([str(_data) for _data in data_1st])
            print 'data_1st', str_data_1st
            pipe.lpush(ORDERS_BONUS, str_data_1st)
            '''
            Primary_Key_1st:分红编号
            transNo:订单号
            Agent1st:代理的id
            Agent1stAccount:代理账号
            parentAg1st:代理的公会
            MoneyNumber:充值金额
            Agent1stPrice:分红金额
            BonusPct1st:分红比例
            UID:充值玩家的id
            becomeAgent:分红类型(0为玩家充值,1为准代理(玩家)充值,2为代理充值)
            istick是否已纳现:0(否),1(是)
            now_time:充值时间
            '''
        if Agent2nd and BonusPct2nd:
            # 代理分红表
            agent2nd = USER_BONUS % Agent2nd
            Agent2stPrice = round(MoneyNumber * BonusPct2nd, 3)
            pipe.hincrbyfloat(agent2nd, 'fromAgent2nd', Agent2stPrice)
            pipe.hincrbyfloat(agent2nd, 'bonusPrice', Agent2stPrice)
            pipe.hincrbyfloat(agent2nd, 'CurBonusPrice', Agent2stPrice)
            # boss比例
            BossBonusPct -= BonusPct2nd
            AgentBossPrice -= Agent2stPrice
            # 充值分红记录
            Agent2ndAccount, parentAg2nd = redis.hmget(FORMAT_USER_TABLE % (Agent2nd), 'account', 'parentAg')
            parentAg2nd = parentAg2nd if parentAg2nd else '无'
            Primary_Key_2nd = redis.incr(ORDERS_BONUS_NUM)
            data_2nd = [Primary_Key_2nd, transNo, Agent2nd, Agent2ndAccount, parentAg2nd,
                        MoneyNumber, Agent2stPrice, BonusPct2nd, UID, PayMoneyUid, PayType, 2, 0, now_time]
            str_data_2nd = "|".join([str(_data) for _data in data_2nd])
            print 'data_2nd', str_data_2nd
            pipe.lpush(ORDERS_BONUS, str_data_2nd)
        if Agent3rd and BonusPct3rd:
            # 代理分红表
            agent3rd = USER_BONUS % Agent3rd
            Agent3rdPrice = round(MoneyNumber * BonusPct3rd, 3)
            pipe.hincrbyfloat(agent3rd, 'fromAgent3rd', Agent3rdPrice)
            pipe.hincrbyfloat(agent3rd, 'bonusPrice', Agent3rdPrice)
            pipe.hincrbyfloat(agent3rd, 'CurBonusPrice', Agent3rdPrice)

            # boss比例
            BossBonusPct -= BonusPct3rd
            AgentBossPrice -= Agent3rdPrice
            # 充值分红记录
            Agent3rdAccount, parentAg3nd = redis.hmget(FORMAT_USER_TABLE % (Agent2nd), 'account', 'parentAg')
            parentAg3nd = parentAg3nd if parentAg3nd else '无'
            Primary_Key_3rd = redis.incr(ORDERS_BONUS_NUM)
            data_3rd = [Primary_Key_3rd, transNo, Agent3rd, Agent3rdAccount, parentAg3nd,
                        MoneyNumber, Agent3rdPrice, BonusPct3rd, UID, PayMoneyUid, PayType, 3, 0, now_time]
            str_data_3rd = "|".join([str(_data) for _data in data_3rd])

            print 'data_3rd', str_data_3rd
            pipe.lpush(ORDERS_BONUS, str_data_3rd)

        bind_uid = redis.hget("agents:id:%s"%myparentAg,'uid')
        if myparentAg and bind_uid:  # 有工会
            # boss比例
            BossBonusPct /= 2.0
            AgentBossPrice /= 2.0

            Primary_Key_agent = redis.incr(ORDERS_BONUS_NUM)
            data_agent = [Primary_Key_agent, transNo, myparentAg, '渠道', myparentAg,
                          MoneyNumber, AgentBossPrice, BossBonusPct, UID, PayMoneyUid, PayType, 4, 0, now_time]
            str_data_agent = "|".join([str(_data) for _data in data_agent])
            pipe.lpush(ORDERS_BONUS, str_data_agent)
            print 'str_data_agent', str_data_agent
            pipe.hincrbyfloat(AGENT_BONUS % myparentAg, 'TotalPrice', AgentBossPrice)
            pipe.hincrbyfloat(AGENT_BONUS % myparentAg, 'CurPrice', AgentBossPrice)

        Primary_Key_boss = redis.incr(ORDERS_BOSS_BONUS_NUM)
        data_boss = [Primary_Key_boss, transNo, '无', '总公司', '无', MoneyNumber,
                     AgentBossPrice, BossBonusPct, UID, PayMoneyUid, PayType, 5, 0, now_time]
        str_data_boss = "|".join([str(_data) for _data in data_boss])
        pipe.lpush(ORDERS_BOSS_BONUS, str_data_boss)
        print 'str_data_boss', str_data_boss
        pipe.hincrbyfloat(BOSS_BONUS, 'TotalPrice', AgentBossPrice)
        pipe.execute()


    def getCardMoney(self, groupId):
        """
        会员购卡单价
        """
        AgentTable = AGENT_TABLE % (groupId)
        unitPrice, parentId, atype = self.redis.hmget(AgentTable, 'unitPrice', 'parent_id', 'type')
        log_debug('[HALLFUNC][getCardMoney][info] groupId[%s] price[%s]' % (groupId, unitPrice))
        if atype in ['2', '3']:
            return self.getCardMoney(parentId)

        return unitPrice

    def addRoomCard2Member4Type2(self, curTime, orderTable, memberAccount):
        gold, money = self.redis.hmget(orderTable, ('roomCards', 'money'))
        addGold2Merber(memberAccount, money, gold)

    def addGold2Merber(self, account, money, num):
        """
            玩家增加金币
            redis:
            account: 账号
            money:  购买金额
            num:  购买金币数
        """
        now = datetime.now()
        date = now.strftime("%Y-%m-%d %H:%M:%S")
        ymd = now.strftime("%Y-%m-%d")
        user_table = redis.get(FORMAT_ACCOUNT2USER_TABLE % account)
        if not user_table:
            return
        uid = user_table.split(':')[1]
        pipe = self.redis.pipeline()
        pipe.hincrby(FORMAT_USER_TABLE % uid, 'gold', num)

        # 每天购买金币的用户集合，用来统计每天购买人数
        pipe.sadd(DAILY_USER_GOLD2_SET % ymd, account)
        # 添加充值金币数到每天总金币数表
        pipe.incrby(DAILY_GOLD2_SUM % ymd, num)
        # 每人每天购买金币总数
        pipe.incrby(DAILY_ACCOUNT_GOLD2_SUM % (account, ymd), num)
        # 每人每天购买金额总数
        pipe.incrby(DAILY_ACCOUNT_GOLD2_MONEY_SUM % (account, ymd), money)
        # 将充值金额数增加到每日充值金额表
        pipe.incrby(DAILY_GOLD2_MONEY_SUM % ymd, money)
        pipe.execute()
        saveBuyGoldRecord( account, {'gold': num, 'money': money, 'date': date})
        return redis.hget(FORMAT_USER_TABLE % uid, 'gold')

    def saveBuyGoldRecord(self, account, data):
        """
            保存金币流水
        """
        try:
            if not self.redis.sismember(GOLD_ACCOUNT_SET_TOTAL, account):
                self.redis.sadd(GOLD_ACCOUNT_SET_TOTAL, account)
            prredis = getPrivateRedisInst(MASTER_GAMEID)
            num = prredis.incr(GOLD_BUY_RECORD_COUNT_TABLE)
            record_key = GOLD_BUY_RECORD_TABLE % num
            pipe = prredis.pipeline()
            data['account'] = account
            pipe.hmset(record_key, data)
            pipe.expire(record_key, GOLD_ROOM_MAX_TIME)
            pipe.lpush(GOLD_BUY_RECORD_ACCOUNT_LIST % account, record_key)
            pipe.lpush(GOLD_BUY_RECORD_LIST_TOTAL, record_key)
            pipe.incr(GOLD_BUY_RECORD_ACCOUNT_GOLD_SUM % account, data['gold'])
            pipe.incr(GOLD_BUY_RECORD_ACCOUNT_MOENY_SUM % account, data['money'])
            pipe.execute()
            user_info = get_user_info(account)
            if not user_info:
                return
            agentid = user_info['parentAg']
            gold = user_info['gold']
            prredis.zadd(GOLD_MONEY_RANK_WITH_AGENT_ZSET % agentid, account, gold)
        except Exception as e:
            log_error(e)

    def get_user_info(self,account):
        """ 获取玩家信息"""
        info = {}
        user_table = self.redis.get(FORMAT_ACCOUNT2USER_TABLE % account)
        if not user_table:
            return info
        info = self.redis.hgetall(user_table)
        info['uid'] = user_table.split(':')[1]
        return info

    def getPrivateRedisInst(self, gameid):
        """
            获取redis连接实例
        """
        try:
            if not self.redis.exists(GAME2REDIS % gameid):
                return None
            info = self.redis.hgetall(GAME2REDIS % gameid)
            ip = info['ip']
            passwd = info['passwd']
            port = int(info['port'])
            dbnum = int(info['num'])
            import redis
            redisdb = redis.ConnectionPool(host=ip, port=port, db=dbnum, password=passwd)
            return redis.Redis(connection_pool=redisdb)
        except:
            log_error('获取redis连接实例FAILED')
            return None

class NicknameHandler(BaseHandler):
    def post(self):
        uid = self.get_argument('uid')
        nickname = self.redis.hget('users:%s'%uid,'nickname')
        if nickname:
            # self.write({"code":0,"msg":"ok","data":nickname})
            u_success(self, 'ok', data=nickname)
        else:
            # self.write({"code":1,"msg":"no exists","data":'该用户不存在！'})
            u_error(self, 'no exists', data='该用户不存在！')

class CheckPlayerHandler(BaseHandler):
    def get(self):
        uid = self.get_argument('uid')
        print '========================charge log======================='
        print uid
        print '========================charge log======================='
        isbind,isAgent = self.redis.hmget('users:%s'%uid,'isbind','isAgent')
        if not isbind and not isAgent:
            self.write("1")
        else:
            self.write("0")

