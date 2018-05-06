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
from webserver import TrafficLightWeb


local_light = TrafficLightSerial.open("/dev/serial0")

root = File("../website/")

interface = NoResource()
interface.putChild("status", TrafficLightWeb(local_light))

root.putChild("local", interface)
root.putChild("auth", Authenticator())

factory = Site(root)
endpoint = endpoints.TCP4ServerEndpoint(reactor, 8880)
endpoint.listen(factory)
reactor.run()
