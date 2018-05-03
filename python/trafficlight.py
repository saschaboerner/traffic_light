import json
import logging
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
from twisted.protocols import basic

class TrafficLight(object):

    def __init__(self):
        self.state = 99
        self.batt_voltage = 0
        self.lamp_currents = [0]*3
        self.seen = False

    def to_json(self):
        data = {
            "state":self.state,
            "batt_voltage":self.batt_voltage,
            "lamp_currents":self.lamp_currents
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
        self.send_update()

    def isGood(self):
        return self.state != 9

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

class TrafficLightSerial(basic.LineReceiver):

    delimiter = '\n'

    config_map = { "min_on_current": 0,
                   "max_on_current": 1,
                   "max_off_current": 2
                   }

    @classmethod
    def open(cls, port, reactor=reactor):
        local_light = cls()
        serial = SerialPort(baudrate=19200, deviceNameOrPortNumber=port, protocol=local_light, reactor=reactor)
        local_light.setSerial(serial)
        return local_light

    def setSerial(self, serial):
        self.serial = serial

    def lineReceived(self, line):
        # Ignore blank lines
        if not line: return
        line = line.decode("ascii").strip()
        try:
            (self.state, self.batt_voltage, self.error_state, self.lamp_currents[0], self.lamp_currents[1], self.lamp_currents[2]) = line.split(" ")
        except ValueError:
            logging.info("Received garbled line")
        logging.warning("update myself: {}".format(self))

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
        self.send_update()
