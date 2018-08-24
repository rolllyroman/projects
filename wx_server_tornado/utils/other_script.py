#coding:utf-8

import redis
from datetime import datetime,timedelta

redis_options = dict(
    host='172.18.97.117',
    port=6379,
    db=1,
    password="168joyvick"
)
game_redis = reids.Redis(**redis_options)

accounts = game_redis.smembers("account4weixin:set")


today_str = datetime.strftime(datetime.now(),'%Y-%m-%d')
monday = datetime.strptime(today,'%Y-%m-%d')
cur_day = monday - timedelta(7)

while cur_day < monday:
    date_str = datetime.strftime(cur_day,'%Y-%m-%d')
    cur_day += timedelta(1)
