#coding:utf-8
import json
import tornado.gen
import sys
sys.path.append('../')

from base import BaseHandler
from constants import *
from utils.common import AccessToken

from tornado.httpclient import AsyncHTTPClient,HTTPRequest

class DMHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        try:
            access_token = yield AccessToken.get_access_token()
        except Exception as e:
            self.write("errmsg: %s" % e)

        client = AsyncHTTPClient()
        url = "https://api.weixin.qq.com/cgi-bin/menu/delete?access_token=%s" % access_token
        resp = yield client.fetch(url)
        dict_data = json.loads(resp.body)
        self.write(dict_data)

class GMHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        access_token = yield AccessToken.get_access_token()
        print 'what the fuck ---------'
        print access_token
        print 'what the fuck ---------'
        client = AsyncHTTPClient()
        url = "https://api.weixin.qq.com/cgi-bin/get_current_selfmenu_info?access_token=%s"% access_token
        resp = yield client.fetch(url)
        self.write(resp.body)

class MenuHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        try:
            access_token = yield AccessToken.get_access_token()
        except Exception as e:
            self.write("errmsg: %s" % e)
        else:
            client = AsyncHTTPClient()
            url = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token=%s" % access_token
            menu = {
                "button":
                    [
                        {
                            "name": "东胜",
                            "sub_button":
                                [
                                    {
                                        "type":"view",
                                        "name":"东胜后台",
                                        "url":"https://open.weixin.qq.com/connect/oauth2/authorize?appid="+WECHAT_APP_ID+"&redirect_uri="+redirect_uri+"&response_type=code&scope=snsapi_userinfo&state=1&connect_redirect=1#wechat_redirect"
                                    },
                                ]
                        },
                        {
                            "name": "后台管理",
                            "sub_button":
                                [
                                    {
                                        "type":"view",
                                        "name":"下线代理列表",
                                        "url":"http://c1.dongshenggame.cn/admin/login"
                                    },
                                ]
                        },
                        {
                            "type": "view",
                            "name": "充值",
                            "url": "https://open.weixin.qq.com/connect/oauth2/authorize?appid="+WECHAT_APP_ID+"&redirect_uri="+redirect_uri2+"&response_type=code&scope=snsapi_userinfo&state=1&connect_redirect=1#wechat_redirect"
                        }
                    ]
                }
            req = HTTPRequest(
                url=url,
                method="POST",
                body=json.dumps(menu, ensure_ascii=False)
            )
            resp = yield client.fetch(req)
            self.write(resp.body)