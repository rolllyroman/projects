#coding:utf-8
import os

settings = dict(
        template_path=os.path.join(os.path.dirname(__file__), "template"),
        debug=True,
        cookie_secret="61oETzKXQAGaYdghdhgfhfhfg",
        xsrf_cookie=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"),
)

# 数据库配置参数
mysql_options = dict(
    host="172.18.242.9",
    database="bag_data",
    user="root",
    password="168mysql"
)

# Redis配置参数
redis_options = dict(
    host='172.18.242.9',
    port=6379,
    db=1,
    password="Fkkg65NbRwQOnq01OGMPy5ZREsNUeURm"
)

bag_redis_options = dict(
    host='120.79.135.194',
    port=6379,
    db=2,
    password="168joyvick"
)

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs")
