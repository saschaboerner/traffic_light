import json
import logging
from configparser import SafeConfigParser
from twisted.web.client import Agent, readBody
from twisted.web import resource
from twisted.internet import reactor, task


class TrafficLightMasterSlave(object):
    '''
    Handles master/slave behavior and synch.
    '''
    service_class = "_http._tcp.local"

    def __init__(self, config_file_name):
        self.config = SafeConfigParser()
        with open(config_file_name, "r") as f:
            self.config.read(f)
        self.isMaster = self.config.getboolean("general", "master")
        self.remote_hostname = self.config.get("general", "remote")
        if self.remote_hostname is None:
            logging.error("No remote hostname defined. No master/slave capability possible!")

        self.poll_loop = task.LoopingCall(self.poll_remote)
        self.poll_loop.start(0.25)
        self.agent = Agent(reactor)
        self.remote_url = "http://{}:8880/interface/status".format(self.remote_hostname).encode("ascii")
        self.running_request = None
        self.error_count = 0
        # Publish own service
        # TODO

    def poll_remote(self):
        '''
        Polls remote host to get its state
        '''
        if self.running_request is not None:
            self.error_count += 1
            self.running_request.cancel()

        self.running_request = self.agent.request(b"GET", self.remote_url)
        self.running_request.addCallback(self.request_handler)
        pass

    def request_handler(self, response):
        d = readBody(response)
        # TODO maybe move it until validation?
        self.error_count = 0
        if not self.isMaster:
            # Only master need to really process the answer,
            # a slave is happy when it sees the master
            d.addCallback(self.on_slave_received)
        else:
            d.addCallback(self.on_master_received)

    def on_slave_received(self, body):
        pass

    def on_master_received(self, body):
        pass

    def on_discover(self, host):
        '''
        When discovering an external host, determine who's the master
        and tell the host about it.
        '''
        pass


class TrafficLightWeb(resource.Resource):
    isLeaf = True
    numberRequests = 0

    def __init__(self, local_light):
        self.myLight = local_light
        print(local_light)

    # HTTP side
    def render_GET(self, request):
        challenge = None
        if 'challenge' in request.args:
            challenge = request.args['challenge'][0]

        self.numberRequests += 1
        request.setHeader(b"content-type", b"text/plain")
        content = self.myLight.to_json(challenge)
        return content

    def render_POST(self, request):
        data = request.args
        handled = False
        # When no key is passed -> fail quickly
        try:
            key = data['key'][0]
        except KeyError:
            key = None

        if not self.myLight.isWritable(key):
            return "not writeable"

        if 'giveway' in data:
            try:
                value = int(data['giveway'][0])
            except:
                return "value error"
            self.myLight.setGreen(value)
            handled = True

        if 'temp_error' in data:
            self.myLight.setTempError(bool(int(data['temp_error'][0])))
            handled = True

        if not handled:
            return "not ok"
        else:
            return "ok"


class JSONAnswer(resource.Resource):
    isLeaf = False
    numberRequests = 0

    def __init__(self, to_be_jsoned):
        self.data = to_be_jsoned
        resource.Resource.__init__(self)

    # HTTP side
    def render_GET(self, request):
        return bytes(json.dumps(self.data).encode('utf8'))
