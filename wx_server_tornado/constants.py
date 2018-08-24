#coding:utf-8
import urllib

#WECHAT_TOKEN = "ds_wl"
#WECHAT_APP_ID = "wx26d9b1bfc4ed8019"
#WECHAT_APP_SECRET = "08fda16a5d866d81723b43da307b0e01"

WECHAT_TOKEN = "ds_yl"
WECHAT_APP_ID = "wx2a41d9cf0dda8e1e"
WECHAT_APP_SECRET = "5fa61fad870be1090ddaaeeeb404df89"

# WECHAT_APP_ID = "wx5db7c680fbb8de90"
# WECHAT_APP_SECRET = "2e82c680f81b24e62b2612339dcc1d6b"

WECHAT_MCHID = "1482346692"
WECHAT_KEY = "b7ee74e495ec47f4af8d4cc71b4785b6"


WEIXIN2ACCOUNT = 'unionid2account:weixin:%s:key'
FORMAT_ACCOUNT2USER_TABLE = "users:account:%s"
USER_BONUS = "newBonus:user:%s:hesh"
ORDER_TABLE     =    'orders:id:%s'
GOODS_TABLE = 'goods:id:%s'
GOODS_NUM = 'goodsNum:%s:101:key'
PENDING_ORDER = 'pendingGoods:101:set'
ORDER_NUM_LIST = 'orderNumList:101:list'
PLAYER_ORDER = 'playerOrder:%s:101:set'
DAY_ORDER = 'dayOrder:%s:101:list'
DAY_PENDING_ORDER = 'dayPendingOrder:%s:101:list'
SUCCEED_ORDER = 'succeedGoods:101:set'
AGENT_TABLE         =     'agents:id:%s'
DAILY_USER_GOLD2_SET = 'gold2:user:date:%s:set'
DAILY_ACCOUNT_GOLD2_MONEY_SUM = 'gold2:account:%s:money:date:%s:sum'
DAILY_GOLD2_MONEY_SUM = 'gold2:money:date:%s:sum'
GOLD_ACCOUNT_SET_TOTAL = 'gold:account:set:total'
MASTER_GAMEID = '555'
GAME2REDIS = 'gameRedisDatas:%s:hesh'
GOLD_BUY_RECORD_COUNT_TABLE = "gold:buy:record:count"
GOLD_BUY_RECORD_TABLE = "gold:buy:record:%s:table"
GOLD_BUY_RECORD_ACCOUNT_LIST = "gold:buy:record:account:%s:list"
GOLD_BUY_RECORD_LIST_TOTAL = "gold:buy:record:list:total"
GOLD_BUY_RECORD_ACCOUNT_GOLD_SUM = "gold:buy:record:account:%s:gold:sum"
GOLD_BUY_RECORD_ACCOUNT_MOENY_SUM = "gold:buy:record:account:%s:money:sum"
GOLD_MONEY_RANK_WITH_AGENT_ZSET = "gold:money:rank:%s:zset"
USER_ORDER_list = "newOrder:user:%s:list"
GLOBAL_BONUS_PCT = "newBonus:global:hesh"
USER4AGENT_CARD = 'agent:%s:user:%s:card'
USER4AGENT_RECHARGE = 'agent:%s:user:%s:recharge:total'
FORMAT_USER_TABLE = "users:%s"
ORDERS_BONUS_NUM = "newOrder:orders:num"
ORDERS_BONUS = "newOrder:bonus:list"
AGENT_BONUS = "newBonus:agent:%s:hesh"
ORDERS_BOSS_BONUS_NUM = "newOrder:boosBonus:num"
ORDERS_BOSS_BONUS = "newOrder:boosBonus:list"
BOSS_BONUS = "newBonus:boss:hesh"
PLAYER_DAY_USE_CARD = 'playerUseCardData:player:%s:day:%s:list'
SAVE_PLAYER_DAY_USE_CARD_TIME = 91 * 24 * 60 * 60
AGENT_RATE_DATE  = 'agent:%s:rate:%s:price:%s:date:%s'
AGENT_COMPAY_RATE_DATE ='agent:%s:date:%s'
AGENT_BRANCH = "newAgent:branch:%s:set"

redirect_uri = urllib.quote('http://120.79.55.182/transfer')
redirect_uri2 = urllib.quote('http:/120.79.55.182/transfer_charge')


