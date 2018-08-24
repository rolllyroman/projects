#coding:utf-8
from handlers.base import *
from handlers.menu import *
from handlers.pay import *
from handlers.show import *

urls = [
    (r"/", WechatHandler),
    (r"/menu", MenuHandler),
    (r"/profile",ProfileHandler),
    (r"/get/menu", GMHandler),
    (r"/delete/menu", DMHandler),
    (r"/cash/take",CashTakeHandler),
    (r"/charge",ChargeHandler),
    (r"/notify",NotifyHandler),
    (r"/my/charge",MyChargeHandler),
    (r"/my/withdraw",MyWithdrawHandler),
    (r"/qr/code",QRcodeHandler),
    (r"/my/player",MyPlayerHandler),
    (r"/nickname",NicknameHandler),
    (r"/check/player",CheckPlayerHandler),
]