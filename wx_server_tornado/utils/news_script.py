#coding:utf-8

import redis
from datetime import datetime,timedelta

redis_options = dict(
    host='172.18.97.117',
    port=6379,
    db=1,
    password="168joyvick"
)
game_redis = redis.Redis(**redis_options)

today_str = datetime.strftime(datetime.now(),'%Y-%m-%d')
today = datetime.strptime(today_str,'%Y-%m-%d')
cur_day = today - timedelta(3)

accounts = []
while cur_day < today:
    date_str = datetime.strftime(cur_day,'%Y-%m-%d')
    acs_day = game_redis.smembers('login:date:account:%s'%date_str)
    acs_day =  list(acs_day)
    accounts += acs_day
    cur_day  += timedelta(1)

print accounts
