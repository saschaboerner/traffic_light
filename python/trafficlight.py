import json
import logging
import random
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor, task
from twisted.web.client import Agent, readBody
from twisted.protocols import basic
from twisted.python import log
from time import time

class TrafficLight(object):
    maxage = 1

    def __init__(self):
        self.state = 99
        self.batt_voltage = 0
        self.lamp_currents = [0]*3
        self.last_seen = 0
        self.give_way = True

    def seen(self):
        return (time()-self.last_seen) < self.maxage

    def to_json(self):
        data = {
            "state":self.state,
            "batt_voltage":self.batt_voltage,
            "lamp_currents":self.lamp_currents,
            "good":self.isGood()
            }
        return json.dumps(data)
    
    def from_json(self, raw):
        data = json.loads(raw)
        (self.state, self.batt_voltage, self.lamp_currents) = ( data["state"], data["batt_voltage"], data["lamp_currents"] )

    def setConfig(self, param, value):
        # Dummy to be overloaded by real implementations
        pass

    def setGreen(self, give_way):
        self.give_way = give_way
        self.sendUpdate()

    def isGood(self):
        return (self.state != 9) and (self.seen())

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
        # In transistions, flag value as invalid..
        if not (self.remote.state != self.local.state):
            return None
        return True

class TrafficLightDummy(TrafficLight):
    def __init__(self, fail_probability):
        TrafficLight.__init__(self)
        self.fail_loop = task.LoopingCall(self.simulate_failures)
        self.run_loop = task.LoopingCall(self.run)
        self.fail_probability = fail_probability
        self.state=0
        self.fail_loop.start(.5)
        self.run_loop.start(1)

    def simulate_failures(self):
        try:
                if random.random() > (1 - self.fail_probability):
                    self.state = 9
        except Exception as e:
                print "error: {}".format(e)
        print "Hier"

    def run(self):
        print "da state={}".format(self.state)
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
    def __init__(self, url, interval):
        TrafficLight.__init__(self)
        self.poll_loop = task.LoopingCall(self.poll_remote)
        self.agent = Agent(reactor)
        self.remote_url = url
        self.running_request = None
        self.error_count = 0
        self.poll_loop.start(interval)
        
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
        self.from_json(body)
        self.last_seen = time()

class TrafficLightSerial(basic.LineReceiver, TrafficLight):

    delimiter = '\n'.encode('ascii')

    config_map = { "min_on_current": 0,
                   "max_on_current": 1,
                   "max_off_current": 2
                   }

    @classmethod
    def open(cls, port, reset_pin=None, reactor=reactor):
        local_light = cls()
        serial = SerialPort(baudrate=19200, deviceNameOrPortNumber=port, protocol=local_light, reactor=reactor)
        local_light.setSerial(serial)
        local_light.setReset(reset_pin)
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

    def serviceWatchdog(self):
        self.sendUpdate()
