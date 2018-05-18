import json
import hashlib
import time
from ConfigParser import SafeConfigParser
from twisted.web.server import Site
from twisted.web.client import Agent
from twisted.web import server, resource
from twisted.web.resource import Resource, NoResource
from twisted.protocols import basic
from twisted.internet import reactor, endpoints, task
from twisted.web.static import File
from trafficlight import TrafficLightSerial


class TrafficLightMasterSlave(object):
    '''
    Handles master/slave behavior and synch.
    '''
    service_class = "_http._tcp.local"

    def __init__(self, config_file_name):
        self.config = SafeConfigParser()
        with open(config_file_name, "r") as f:
            self.config.read(f)
        self.isMaster = config.getboolean("general", "master")
        self.remote_hostname = config.get("general", "remote")
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
        self.localLight = local_light

    # HTTP side
    def render_GET(self, request):
        self.numberRequests += 1
        request.setHeader(b"content-type", b"text/plain")
        content = self.localLight.to_json()
        return content.encode("utf-8")

    def render_POST(self, request):
        data = request.args
        handled = False
        # Do not write masters
        try:
            key = data['key'][0]
        except KeyError:
            key = None

        if not self.localLight.isWritable(key):
            return "not writeable"

        if 'giveway' in data:
            try:
                value = int(data['giveway'][0])
            except:
                return "value error"
            self.localLight.setGreen(value)
            handled = True

        if 'temp_error' in data:
            self.localLight.setTempError(bool(int(data['temp_error'][0])))
            handled = True

        if not handled:
            return "not ok"
        else:
            return "ok"

class TransportWrapper(object):
    secret = "AchWieGutDassNiemandWeiss"

    def encapsulate(self, message):
        assert(type(message) is dict)
        clone = copy.deepcopy(message)
        clone['_time'] = time.time()
        raw = json.dumps(clone)
        hashsum = hashlib.sha256(raw+secret).hexdigest()
        
        return json.dumps({"raw":raw, "hash":hashsum})

    def decapsulate(self, message):
        #assert(type(message) is str)
        packet = json.loads(message)
        assert('raw' in packet)
        assert('hash' in packet)
        hashsum = hashlib.sha256(raw+secret).hexdigest()
        if not (hashsum == packet['hash']):
            return False
        return json.loads(raw)

class Authenticator(resource.Resource, TransportWrapper):
    isLeaf = True
    common_text = "of0iefipmdsp3ekewpds[rqf;ew.c[efwsd"

    def render_POST(self, request):
        """
        Validate clients token and if it is ok, return a signed
        answer.
        """
        data = request.content.getvalue()
        print(data)
        msg = self.decapsulate(data)
        print(msg)

    def render_GET(self, request):
        return "hallo"

class JSONAnswer(resource.Resource):
    isLeaf = False
    numberRequests = 0

    def __init__(self, to_be_jsoned):
        self.data = to_be_jsoned
        resource.Resource.__init__(self)

    # HTTP side
    def render_GET(self, request):
        return json.dumps(self.data)
