import json
import hashlib
import time
import sys
import copy
from ConfigParser import ConfigParser, NoOptionError
from twisted.web.server import Site
from twisted.web import resource
from twisted.web.resource import NoResource
from twisted.internet import reactor, endpoints
from twisted.web.static import File
from trafficlight import TrafficLightSerial


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
        data = request.args
        if 'giveway' in data:
            try:
                value = int(data['giveway'][0])
            except:
                return "value error"
            self.localLight.setGreen(value)
        else:
            return "not ok"


class TransportWrapper(object):
    secret = "AchWieGutDassNiemandWeiss"

    def encapsulate(self, message):
        assert(type(message) is dict)
        clone = copy.deepcopy(message)
        clone['_time'] = time.time()
        raw = json.dumps(clone)
        hashsum = hashlib.sha256(raw+self.secret).hexdigest()

        return json.dumps({"raw": raw, "hash": hashsum})

    def decapsulate(self, message):
        # assert(type(message) is str)
        packet = json.loads(message)
        assert('raw' in packet)
        assert('hash' in packet)
        hashsum = hashlib.sha256(self.raw+self.secret).hexdigest()
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


if len(sys.argv) > 0:
    config_file_name = sys.argv[1]
else:
    config_file_name = None

config = ConfigParser()
if config_file_name is not None:
    config.read(config_file_name)
print(config.sections())

try:
    reset_gpio = config.get("hardware", "reset_pin")
except NoOptionError:
    reset_gpio = None

try:
    port = config.get("hardware", "port")
except NoOptionError:
    port = None

local_light = TrafficLightSerial.open(port, reset_gpio)

root = File("../website/")

interface = NoResource()
# interface.putChild("give_way", GiveWay(local_light))
interface.putChild("status", TrafficLightWeb(local_light))

root.putChild("interface", interface)
root.putChild("auth", Authenticator())


factory = Site(root)
endpoint = endpoints.TCP4ServerEndpoint(reactor, 8880)
endpoint.listen(factory)
reactor.run()
