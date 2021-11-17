import json
import os
import time
from threading import Thread
from redis import Redis
import tornado
from tornado import ioloop, web, websocket, httpclient
from tornado.web import RequestHandler

class IndexHandler(RequestHandler):
    def get(self):
        self.render('index.html')

class BroadcastHandler(tornado.websocket.WebSocketHandler):
    ws_clients = set()

    def open(self):
        self.ws_clients.add(self)

    def on_message(self, message):
        print('received: ', message)
        self.write_message('Message received {}'.format(message))

    def on_close(self):
        # remove the client from `ws_clients`
        self.ws_clients.remove(self)

    @classmethod
    def broadcast(cls, message):
        """Takes a message and sends to all connected clients"""
        for client in cls.ws_clients:
            # here you can calculate `var` depending on each client
            client.write_message(message)

class DataHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print('data open!')

    def on_message(self, message):
        # pass the message to TestHandler
        # to send out to connected clients
        BroadcastHandler.broadcast(message)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/broad", BroadcastHandler),
            (r"/data", DataHandler),
            (r"/", IndexHandler)
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)


ws_app = Application()
ws_app.listen(8000)
tornado.ioloop.IOLoop.instance().start()