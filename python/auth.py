import json
import copy
import hashlib
import time
from hmac import HMAC
from twisted.web import resource

class TransportWrapper(object):

    def __init__(self, key):
        self.key = key
        self.digestmod = hashlib.sha256

    def encapsulate(self, challenge, message):
        assert(type(message) is dict)
        clone = copy.deepcopy(message)
        clone['_time'] = time.time()
        clone['challenge'] = challenge
        raw = json.dumps(clone)
        hashsum = HMAC(self.key, msg=raw, digestmod=self.digestmod).hexdigest()
        
        return json.dumps({"raw":raw, "hash":hashsum})

    def decapsulate(self, message, challenge):
        #assert(type(message) is str)
        packet = json.loads(message)
        if 'raw' not in packet or 'hash' not in packet:
            raise AttributeError("Packet malformatted")

        hashsum = HMAC(self.key, msg=packet['raw'], digestmod=self.digestmod).hexdigest()

        if not (hashsum == packet['hash']):
            return False

        raw_pkt = json.loads(packet['raw'])
        if raw_pkt['challenge'] != challenge:
            raise ValueError("Challenge mismatch")        

        return raw_pkt

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
