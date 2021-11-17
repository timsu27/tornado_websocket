import json
import os
import time
from threading import Thread
from redis import Redis
import tornado
from tornado import ioloop, web, websocket, httpclient
from tornado.web import RequestHandler

# Register().callbacks数组存储Websocket的回调函数。当收到新消息时，Register()首先将  
# 消息缓存起来，如果有客户端连接，即callbacks数组不为空，则触发所有的回调函数，将消息推送
# 给客户端。
class Register(object):
    def login(self, callback):
        self.callbacks.append(callback)
        self.notify_callbacks()

    def logout(self, callback):
        self.callbacks.remove(callback)

    def trigger(self, message):
        self.messages_cache.append(message)
        self.notify_callbacks()

    def notify_callbacks(self):
        print('notify callbacks')
        if len(self.callbacks) is not 0:
            for callback in self.callbacks:
                callback(json.dumps(self.messages_cache))
            self.messages_cache.clear()
        else:
            print('There is no client connected,save message in cache only')

    def __init__(self):
        self.callbacks = []
        self.messages_cache = []

# 主页路由
class IndexHandler(RequestHandler):
    def get(self):
        self.render('index.html')

# WebsocketHandller().连接建立时，将callback注册到register，
# 连接关闭时清理自己的callback。
class MyWebSocketHandler(websocket.WebSocketHandler):
    def open(self):
        print(str(self) + "connection open")
        self.application.register.login(self.callback)

    def on_message(self, message):
        print(message)

    def on_close(self):
        self.application.register.logout(self.callback)
        print(str(self) + "connection closed")

    def callback(self, message):
        self.write_message(message)

# 接收消息，并将消息发给register
class NewMessageHandler(RequestHandler):
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body)
        print(data)
        self.application.register.trigger(data)

# 配置tornado web应用
class Application(tornado.web.Application):
    def __init__(self):
        self.register = Register()
        handlers = [
            (r"/", IndexHandler),
            (r"/pigeon", MyWebSocketHandler),
            (r"/message", NewMessageHandler)
        ]
        settings = dict(
            template_path=os.path.join(
                               os.path.dirname(__file__), "templates"),
            static_path=os.path.join(
                               os.path.dirname(__file__), "static"),
            debug=False
        )
        tornado.web.Application.__init__(self, handlers, **settings)

#这里不是Spark Streaming的主场，所以用publisher模拟发布数据
def publisher():
    r = Redis(host='localhost', port=6379, decode_responses=True)
    a = 1
    while True:
        r.publish("my_channel", "Hello:" + str(a))
        a += 1
        time.sleep(1)

# 订阅redis中的特定channel，收到消息后，调用data_handler向/message发消息
def subscriber():
    r = Redis(host='localhost', port=6379, decode_responses=True)
    p = r.pubsub()
    p.subscribe(**{'my_channel': data_handler})
    p.run_in_thread()


def data_handler(message):
    url = "http://127.0.0.1:8000/message"
    data = {'data': message['data']}
    http_request = httpclient.HTTPRequest(url, method="POST",
                                          body=json.dumps(data))
    http_client = httpclient.HTTPClient()
    http_client.fetch(http_request)

if __name__ == "__main__":
    Thread(target=publisher).start()
    subscriber()

    app = Application()
    app.listen(8000)

    tornado.ioloop.IOLoop.current().start()