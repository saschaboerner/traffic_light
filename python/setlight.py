import json
import logging
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
from twisted.web.client import Agent, readBody, FileBodyProducer
from twisted.protocols import basic
from twisted.python import log
from twisted.web.http_headers import Headers
from time import time
from auth import TransportWrapper
from StringIO import StringIO


class TrafficLightClient():
    def __init__(self, url):
        self.agent = Agent(reactor)
        self.remote_url = url
        self.running_request = None
        self.error_count = 0

    def make_request(self, message, handler):
        stringio = StringIO(json.dumps(message))
        req = self.agent.request("POST",
                                 self.remote_url,
                                 Headers({'Content-Type': ['application/json']}),
                                 FileBodyProducer(stringio))
        self.running_request = req
        self.running_request.addCallback(self.request_handler,
                                         handler)
        self.running_request.addErrback(log.err)
        return req

    def request_handler(self, response, result_handler):
        d = readBody(response)
        d.addCallback(self.on_data_received, result_handler)
        d.addErrback(log.err)
        self.running_request = None
        return d

    def give_way(self):
        pass
