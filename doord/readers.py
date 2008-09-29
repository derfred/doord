from twisted.internet.protocol import DatagramProtocol, Protocol, Factory
from twisted.internet import reactor, defer
from twisted.application import internet, service
from twisted.web import server, resource

import time, logger

class Reader(service.Service):
    def __init__(self, config=None):
        """The constructor, takes a config object"""
        if not config.has_key('direction'):
            raise Exception, 'Reader require a direction config'

        self.config = config

    def register_listener(self):
        """This sets up the Listener to wait for card swipes"""
        pass

    def indicate_success(self):
        """Indicate to the user that authorization was successful"""
        pass

    def indicate_failure(self):
        """Indicate to the user that authorization failed, with a beep for example"""
        pass

    def indicate_error(self):
        """Indicate to the user that there was an error in authorization"""
        pass

    def report_health(self):
        """callback to tell the daemon how this component is doing. Note this is supposed to return immediately"""
        return True

    def check_health(self):
        """callback to check with the components health. This is supposed to do an actual check and may return a Defer"""
        return defer.succeed(True)

# a very simple web interface to opening the door
class WebInterfaceResource(resource.Resource):
    isLeaf = True
    def __init__(self, reader):
        self.reader = reader

    def render_GET(self, request):
        return "<html><form action='' method='POST'><input type='submit' value='Open door'></form></html>"

    def render_POST(self, request):
        self.reader.open_door()
        request.redirect("/")
        return ""

class WebInterfaceReader(Reader):
    def __init__(self, config = {}):
        self.port = config.get('port', 8080)
        self.doord = config['doord']
        internet.TCPServer(self.port, server.Site(WebInterfaceResource(self))).setServiceParent(self.doord.getServiceCollection())

    def open_door(self):
        self.doord.handle_input(self, "")

# this is a debug Reader
class TCPConnectionReaderProtocol(Protocol):
    def connectionMade(self):
        self.factory.owner.have_connection()
        self.transport.loseConnection()

class TCPConnectionReader(Reader):
    def __init__(self, config = {}):
        self.port = config.get('port', 1717)
        self.doord = config['doord']
        factory = Factory()
        factory.protocol = TCPConnectionReaderProtocol
        factory.owner = self
        internet.TCPServer(self.port, factory).setServiceParent(self.doord.getServiceCollection())

    def have_connection(self):
        self.doord.handle_input(self, "")

# this is Reader for the Gemini2k X1010IP RFID reader
class GeminiReader(Reader, DatagramProtocol):
    def __init__(self, config = {}):
        self.doord = config['doord']
        self.port = config.get('port', 6320)
        self.min_interval = config.get('min_interval', 0.5)
        self.hb_warn_interval = config.get('hb_warn_interval', 15)
        internet.UDPServer(self.port, self).setServiceParent(self.doord.getServiceCollection())

        self.last_read = 0
        self.last_hb = 0

    def report_health(self):
        if self.last_hb == 0 or time.time() - self.last_hb < self.hb_warn_interval:
            return True
        return "no heartbeat in %d seconds (warn interval %d)" % (time.time() - self.last_hb, self.hb_warn_interval)

    def datagramReceived(self, data, (host, port)):
        #logger.log("GeminiReader", "received %r from %s:%d" % (data, host, port))
        if data[:2] == "HB":
            # this is a heartbeat message
            self.last_hb = time.time()
        elif data[:2] == "SN":
            # this is a actual card read
            self.doord.handle_input(self, data[2:10])
            self.last_read = time.time()
        else:
            # unidentified message, log it for reference
            logger.warn("GeminiReader", "unidentified packet received: %r from %s:%d" % (data, host, port))

