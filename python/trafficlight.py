import json
import logging
import random
import urllib
import traceback
from StringIO import StringIO
from twisted.web.client import FileBodyProducer
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor, task
from twisted.web.client import Agent, readBody
from twisted.protocols import basic
from twisted.python import log
from time import time
#from zope.interface import implements


class TrafficLight(object):

    def __init__(self):
        self.logger = logging.getLogger()
        self.state = 99
        self.batt_voltage = 0
        self.lamp_currents = [0]*3
        self.last_seen = 0
        self.maxage = 2
        self.give_way = True
        self.temp_error = False
        self.read_only = False
        self.web_writeable = False
        self.group_key = None

    def setGroupKey(self, key):
        self.group_key = key

    def isWritable(self, key):
        if self.web_writeable:
            return True
        if self.group_key is None:
            return False
        if self.group_key == key:
            return True
        return False

    def dereference(self, names):
        '''
        Dereferece symbolic names (if needed)
        '''
        pass

    def setLogger(self, logger):
        self.logger = logger

    def setReadOnly(self, read_only):
        self.read_only = read_only

    def seen(self):
        return (time()-self.last_seen) < self.maxage

    def to_json(self):
        data = {
            "state":self.state,
            "batt_voltage":self.batt_voltage,
            "lamp_currents":self.lamp_currents,
            "good":self.isGood(),
            "give_way":self.give_way,
            "temp_error":self.temp_error
            }
        return json.dumps(data)

    def from_json(self, raw):
        data = json.loads(raw)
        print data
        (self.state, self.batt_voltage, self.lamp_currents) = ( data["state"], data["batt_voltage"], data["lamp_currents"] )
        (self.give_way, self.temp_error) = ( data["give_way"], data["temp_error"] )

    def setConfig(self, param, value):
        # Dummy to be overloaded by real implementations
        pass

    def setGreen(self, give_way):
        assert type(give_way) in ( bool, int )
        give_way = bool(give_way)
        if self.give_way != give_way:
            if give_way:
                self.logger.debug("Should give way")
            else:
                self.logger.debug("Should CLOSE way")

            self.give_way = give_way
            self.sendUpdate()

    def isGood(self):
        return (self.state != 9) and (self.seen())

    def setTempError(self, error_state):
        assert type(error_state) in ( bool, int )
        error_state = bool(error_state)
        if self.temp_error != error_state:
            if error_state:
                self.logger.debug("Received temp error")
            else:
                self.logger.debug("No temp error")
            self.temp_error = error_state
            self.sendUpdate()


    def __str__(self):
        return "TrafficLight(state={}, batt_voltage={}, lamp_currents={})".format(self.state, self.batt_voltage, self.lamp_currents)
class TrafficLightGroup(object):
    def __init__(self, iAmMaster, local, remote):
        self.iAmMaster = iAmMaster
        self.remote = remote
        self.local = local

    def setGreen(self, give_way):
        self.remote.setGreen(give_way)
        self.local.setGreen(give_way)

    def isGood(self):
        if not self.remote.seen():
            return False
        # In transistions, disregard state divergence for a while
        if self.remote.give_way!= self.local.give_way:
            if self.start_diverge is None:
                self.start_diverge = time()
            if (time() - self.start_diverge) > self.max_diverge:
                return "maxdiverge"
                return False
            return None
        else:
            self.start_diverge = None
        if 9 in [self.local.state, self.remote.state]:
            # If an error was detected on either side, fail here, too
            return False
        return True


class TrafficLightDummy(TrafficLight):
    @classmethod
    def open(cls, name, fail_probability):
        r = cls(float(fail_probability))
        r.setLogger( logging.getLogger(name) )
        return r

    def __init__(self, fail_probability):
        TrafficLight.__init__(self)
        self.fail_loop = task.LoopingCall(self.simulateFailures)
        self.run_loop = task.LoopingCall(self.run)
        self.fail_probability = fail_probability
        self.state=0
        self.fail_comm = False
        self.fail_lamp = False

        self.fail_loop.start(.5) .addErrback(self.error)
        self.run_loop.start(2) .addErrback(self.error)

    def sendUpdate(self):
        if self.read_only:
            self.logger.debug("Read-only: No update:")
        else:
            self.logger.debug("Would update: {}".format(self.state))

    def error(self, err):
        self.logger.debug(err)

    def simulateFailures(self):
        if random.random() > (1 - self.fail_probability):
            self.fail_lamp = random.random()>.5
            self.fail_comm = random.random()>.5
            self.logger.warning("fail_lamp={} fail_comm={}".format(self.fail_lamp, self.fail_comm))

    def reset(self):
        self.state = 0
        self.fail_comm = False
        self.fail_lamp = False

    def run(self):
        self.batt_voltage = 12 + random.random()*1.5
        if not self.fail_comm:
            self.last_seen = time()
        if self.fail_lamp:
            self.state = 9
        self.logger.debug("state={}".format(self.state))
        if self.state < 3:
            self.state += 1
        elif self.state == 5:
            if self.give_way:
                self.state = 6
        elif self.state == 6:
                self.state = 3
        elif self.state == 3:
            if not self.give_way:
                self.state = 4
        elif self.state == 4:
            self.state = 5
        elif self.state == 8 and self.temp_error == False:
            self.state = 3
        elif self.temp_error:
            self.logger.warning("Got temporary error")
            self.state = 8
        self.lamp_currents = {
            0:[60,0,0],
            1:[60,60,0],
            2:[60,60,60],
            3:[0,0,60],
            4:[0,60,0],
            5:[60,0,0],
            6:[60,60,0],
            8:[0,30,0],
            9:[0,25,0],
            }[self.state]

class TrafficLightRemote(TrafficLight):
    @classmethod
    def open(cls, name, url, interval):
        r = cls(url, float(interval))
        r.setLogger( logging.getLogger(name) )
        return r

    def __init__(self, url, interval):
        TrafficLight.__init__(self)
        self.poll_loop = task.LoopingCall(self.poll_remote)
        self.agent = Agent(reactor)
        self.remote_url = url
        self.running_request = None
        self.error_count = 0
        self.poll_loop.start(interval).addErrback(log.err)

    def update_answer_handler(self, response):
        d = readBody(response)
        # TODO maybe move it until validation?
        self.error_count = 0
        d.addCallback(self.on_update_answer_received)
        d.addErrback(log.err)
        self.running_request = None
        return d

    def on_update_answer_received(self, data):
        if not data.strip()=="ok":
            logging.error("Something went wrong trying to update remote.. Answer was:{}".format(data.strip()))

    def poll_remote(self):
        '''
        Polls remote host to get its state
        '''
        if self.running_request is not None:
            self.error_count += 1
            self.running_request.cancel()

        try:
            self.running_request = self.agent.request(b"GET", self.remote_url)
            self.running_request.addCallback(self.request_handler)
            self.running_request.addErrback(log.err)
        except Exception as e:
            print ">>>>{}".format(e)
    
    def request_handler(self, response):
        d = readBody(response)
        # TODO maybe move it until validation?
        self.error_count = 0
        d.addCallback(self.on_data_received)
        d.addErrback(log.err)
        self.running_request = None
        return d

    def on_data_received(self, body):
        self.logger.debug("body={}".format(body))
        self.from_json(body)
        self.last_seen = time()

class TrafficLightSerial(basic.LineReceiver, TrafficLight):

    delimiter = '\n'.encode('ascii')

    config_map = { "min_on_current": 0,
                   "max_on_current": 1,
                   "max_off_current": 2
                   }

    @classmethod
    def open(cls, name, port, reset_pin=None, reactor=reactor):
        local_light = cls()
        local_light.setLogger( logging.getLogger(name) )
        serial = SerialPort(baudrate=19200, deviceNameOrPortNumber=port, protocol=local_light, reactor=reactor)
        local_light.setSerial(serial)
        local_light.setReset(reset_pin)
        local_light.sendUpdate()
        return local_light

    def setSerial(self, serial):
        self.serial = serial

    def setReset(self, pin):
        if pin is None:
            self.reset_name = None
            return

        self.reset_name = "/sys/class/gpio/gpio{}/value".format(pin)
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write("{}\n".format(pin))
        except Exception as e:
            logging.error("Could not open/write exports in gpiofs: {}".format(e))

    def lineReceived(self, line):
        # Ignore blank lines
        if not line: return
        line = line.decode("ascii").strip()
        try:
            (self.state, self.batt_voltage, self.error_state, self.lamp_currents[0], self.lamp_currents[1], self.lamp_currents[2]) = line.split(" ")
            self.last_seen = time()
        except ValueError:
            logging.info("Received garbled line")
        #logging.warning("update myself: {}".format(self))

    def setConfig(self, param, value):
        if param in self.config_map:
            cmd = "s{}={}".format(self.config_map[param], int(value))
            self.sendLine(cmd)
        else:
            raise ValueError("Unknown parameter {}".format(param))

    def sendUpdate(self):
        if self.give_way:
            self.sendLine("G")
        else:
            self.sendLine("g")
        if self.temp_error:
            self.sendLine("E")
        else:
            self.sendLine("e")

    def serviceWatchdog(self):
        self.sendUpdate()

lightTypes={'serial':TrafficLightSerial,
        'group':TrafficLightGroup,
        'dummy':TrafficLightDummy,
        'remote':TrafficLightRemote
    }
