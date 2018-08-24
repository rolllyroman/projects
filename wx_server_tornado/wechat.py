# coding:utf-8

import tornado.web
import tornado.options
import tornado.httpserver
import tornado.ioloop
import tornado.gen
import torndb
import redis

from tornado.options import options, define

from constants import *
from config import *
from urls import urls

define("port", default=80, type=int, help="")

class Application(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.db = torndb.Connection(**mysql_options)
        self.redis = redis.Redis(**redis_options)
        self.bag_redis = redis.Redis(**bag_redis_options)

def main():
    tornado.options.parse_command_line()
    app = Application(
        urls,
        **settings
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
