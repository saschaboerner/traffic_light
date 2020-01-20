import sys
import logging
from configparser import SafeConfigParser
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.internet import reactor, endpoints
from twisted.web.static import File
from trafficlight import lightTypes
from webserver import TrafficLightWeb, JSONAnswer

if len(sys.argv)<2:
    print("Please start with a config file name")
    sys.exit(0)

logging.basicConfig(level=logging.DEBUG)


lights = {}
conf = SafeConfigParser()
conf.read(sys.argv[1])

sections = conf.sections()

if 'web' not in sections:
    port = 8880
else:
    port = conf.getint('web', 'http_port')

light_sections = sections[:]
light_sections.remove('web')

fail = False
for s in light_sections:
    o = conf.options(s)
    if 'type' not in o:
        logging.error("{}: No type given, cannot process".format(s))
        continue
    lighttype = conf.get(s, 'type').strip()
    if lighttype not in lightTypes:
        logging.error("{}: Type '{}' is unknown, valid would be {}".format(s, lighttype, lightTypes.keys()))
        continue
    options = {k: conf.get(s, k) for k in conf.options(s)}
    del options['type']

    try:
        logging.info("Start {}".format(s))
        l = lightTypes[lighttype].open(name=s, **options)
    except TypeError as e:  # When option name is not known
        logging.error("{}: {}".format(s, e))
        continue
    lights[s] = l


root = Resource()
root.putChild("foo", File("/tmp"))
static = File("../website/")
root.putChild("static", static)

interface = JSONAnswer(list(lights.keys()))
#interface.putChild("status", TrafficLightWeb(local_light))
#root.putChild("interface", interface)

for s in lights:
    # After init, dereference symbolic names
    lights[s].dereference(lights)
    # Finally add them to the web tree
    interface.putChild(s, TrafficLightWeb(lights[s]))
#root.putChild("auth", Authenticator())

factory = Site(root)
endpoint = endpoints.TCP4ServerEndpoint(reactor, port)
endpoint.listen(factory)
reactor.run()
