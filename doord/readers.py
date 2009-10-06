from twisted.internet.protocol import DatagramProtocol, Protocol, Factory
from twisted.internet import reactor, defer
from twisted.application import internet, service
from twisted.web import server, resource

import time, logger

class Reader(service.Service):
    def __init__(self, pipeline, config=None):
        """The constructor, takes a config object"""
        self.config = config
        self.pipeline = pipeline

    def handle_input(self, token):
        """Notify the owning pipeline about a access request"""
        self.pipeline.handle_input(token)

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
    def __init__(self, pipeline, config = {}):
        Reader.__init__(self, pipeline, config)
        self.port = config.get('port', 8080)
        internet.TCPServer(self.port, server.Site(WebInterfaceResource(self))).setServiceParent(self.pipeline.getServiceCollection())

    def open_door(self):
        self.handle_input("")

# this is a debug Reader
class TCPConnectionReaderProtocol(Protocol):
    def connectionMade(self):
        self.factory.owner.have_connection()
        self.transport.loseConnection()

class TCPConnectionReader(Reader):
    def __init__(self, pipeline, config = {}):
        Reader.__init__(self, pipeline, config)
        self.port = config.get('port', 1717)
        self.token = config.get('token', "")
        factory = Factory()
        factory.protocol = TCPConnectionReaderProtocol
        factory.owner = self
        internet.TCPServer(self.port, factory).setServiceParent(self.pipeline.getServiceCollection())

    def have_connection(self):
        self.handle_input(self.token)

# this is Reader for the Gemini2k X1010IP RFID reader
class GeminiReader(Reader, DatagramProtocol):
    def __init__(self, pipeline, config = {}):
        Reader.__init__(self, pipeline, config)
        self.port = config.get('port', 6320)
        self.min_interval = config.get('min_interval', 0.5)
        self.hb_warn_interval = config.get('hb_warn_interval', 15)
        internet.UDPServer(self.port, self).setServiceParent(self.pipeline.getServiceCollection())

        self.last_read = 0
        self.last_hb = 0

    def report_health(self):
        if self.last_hb == 0 or time.time() - self.last_hb < self.hb_warn_interval:
            return True
        return "no heartbeat in %d seconds (warn interval %d)" % (time.time() - self.last_hb, self.hb_warn_interval)

    def datagramReceived(self, data, (host, port)):
        # honour the minimum delta between reads, this is to prevent activation during operation cycle errors
        # in case the card is picked up multiple times
        if self.last_read != 0 and time.time() - self.last_read < self.min_interval:
            return

        self.last_hb = time.time()
        if data[:2] == "SN":
            # this is a actual card read
            self.handle_input(data[2:10])
            self.last_read = time.time()
        elif data[:2] == "HB":
            # Heartbeat messages start with a HB prefix
            # unidentified message, log it for reference
            logger.warn("GeminiReader", "unidentified packet received: %r from %s:%d" % (data, host, port))
