import os
import threading
import dbus

class mdns_avahi(object):
    def __init__(self):


sys_bus = dbus.SystemBus()

# get an object called / in org.freedesktop.Avahi to talk to
raw_server = sys_bus.get_object('org.freedesktop.Avahi', '/')

# objects support interfaces. get the org.freedesktop.Avahi.Server interface to our org.freedesktop.Avahi object.
server = dbus.Interface(raw_server, 'org.freedesktop.Avahi.Server')
:
# The so-called documentation is at /usr/share/avahi/introspection/Server.introspect
print server
print server.GetVersionString()
print server.GetHostName()


