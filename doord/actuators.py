from twisted.internet import defer, reactor
from twisted.internet.protocol import Protocol, ClientCreator
from twisted.conch.telnet import Telnet, TelnetTransport, TelnetProtocol

import logger, re

def logInboundConversation(module, data):
    """this will write the data to the log, in line oriented conversation style"""
    logger.log(module, "\n".join(map(lambda l: "< %s" % l, data.split("\n"))))

class Actuator(object):
    def __init__(self, config=None):
        """the constructor, with an optional config object"""
        self.config = config

    def operate(self):
        """operate the actuator to open the door"""
        pass

    def report_health(self):
        """callback to tell the daemon how this component is doing. Note this is supposed to return immediately"""
        return True

    def check_health(self):
        """callback to check with the components health. This is supposed to do an actual check and returns a Defer"""
        return defer.succeed(True)

def any_line_matches(regex, string):
    for line in string.split("\n"):
        if re.match(regex, line):
            return True
    return False

class PerleProtocol(Telnet):
    mode = "WaitForUser"
    prompt = ""
    buffer = ""

    def __init__(self, perle_actuator, user, password, relay):
        Telnet.__init__(self)
        self.perle_actuator = perle_actuator
        self.user = user
        self.password = password
        self.relay = relay

    def write(self, command):
        """docstring for issue_command"""
        self._write(command + '\r\n')

    def applicationDataReceived(self, data):
        """this is the dispatcher for the state methods"""
        self.buffer += data
        if self.prompt != "" and self.buffer.find(self.prompt) == -1:
            return

        mode = getattr(self, "handle_%s" % self.mode)(self.buffer)

        self.buffer = ""

        if mode == "Done":
            self.perle_actuator.finish_cycle()
            self.transport.loseConnection()
        elif mode != None:
            self.mode = mode

    def handle_WaitForUser(self, data):
        if data.find("Login:") == -1:
            logger.error("PerleActuator", "got unexpected input in state WaitForUser: %s" % data)
            return "Done"
        self.write(self.user)
        self.prompt = "Password:"
        return "WaitForPassword"

    def handle_WaitForPassword(self, data):
        if data.find("Password:") == -1:
            logger.error("PerleActuator", "got unexpected input in state WaitForPassword: %s" % data)
            return "Done"
        self.write(self.password + '\r\n')
        self.prompt = "DS1 D2R2#"
        return "WaitForIssueLoginCheck"

    def handle_WaitForIssueLoginCheck(self, data):
         self.write('show iochannel status')
         return "WaitForLoginCheck"

    def handle_WaitForLoginCheck(self, data):
         if not any_line_matches('^%s.+Inactive' % self.relay.upper(), data):
             logger.error("PerleActuator", "Relay active on login!")
             return "Done"
         self.write('iochannel %s output activate' % self.relay)
         return "WaitForIssueActivationConfirmation"

    def handle_WaitForIssueActivationConfirmation(self, data):
        self.write('show iochannel status')
        return "WaitForActivationConfirmation"

    def handle_WaitForActivationConfirmation(self, data):
        if not any_line_matches('^%s.+Active' % self.relay.upper(), data):
            logger.error("PerleActuator", "Relay not active after activation!")
            return "Done"
        self.write('iochannel %s output deactivate' % self.relay)
        return "WaitForIssueDeactivationConfirmation"

    def handle_WaitForIssueDeactivationConfirmation(self, data):
        self.write('show iochannel status')
        return "WaitForDeactivationConfirmation"
    
    def handle_WaitForDeactivationConfirmation(self, data):
        if not any_line_matches('^%s.+Inactive' % self.relay.upper(), data):
            logger.error("PerleActuator", "Relay not inactive after deactivation!")
            return "Done"
        self.write('logout')
        return "Done"


class PerleActuator(Actuator):
    def __init__(self, config={}):
        self.ip = config['ip']
        self.port = config.get('port', 23)
        self.user = config['user']
        self.password = config['password']
        self.relay = config.get("relay", "r1")
        self.d = None

    def operate(self):
        if self.d != None:
            logger.log("PerleActuator", "operated while in activation cycle")
            return
        c = ClientCreator(reactor, PerleProtocol, self, self.user, self.password, self.relay)
        c.connectTCP(self.ip, self.port)

        self.d = defer.Deferred()
        return self.d

    def finish_cycle(self):
        """this is the callback from the PerleProtocol to indicate that the activation cycle has completed"""
        d = self.d
        self.d = None
        d.callback(None)
