import json
import hashlib
import time
from twisted.web.server import Site
from twisted.web import server, resource
from twisted.web.resource import Resource, NoResource
from twisted.protocols import basic
from twisted.internet import reactor, endpoints
from twisted.web.static import File
from trafficlight import TrafficLightSerial


class TrafficLightMasterSlave(object):
    '''
    Handles master/slave behaviour and synch.
    '''
    service_class = "_http._tcp.local"

    def __init__(self):
        self.isMaster = False
        # Publish own service
        # TODO
    
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
        content = local_light.to_json()
        return content.encode("utf-8")

    def render_POST(self, request):
        print (request.content.getvalue())

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

local_light = TrafficLightSerial.open("/dev/serial0")

root = File("../website/")
root.putChild("foo", File("/tmp"))

interface = NoResource()
#interface.putChild("give_way", GiveWay(local_light))
interface.putChild("status", TrafficLightWeb(local_light))

root.putChild("interface", interface)
root.putChild("auth", Authenticator())


factory = Site(root)
endpoint = endpoints.TCP4ServerEndpoint(reactor, 8880)
endpoint.listen(factory)
reactor.run()
