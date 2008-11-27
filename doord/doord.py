import sys
sys.path.append(".")

import readers, actuators, authenticators, logger
from twisted.internet import defer, reactor, task
from twisted.application import internet, service


class DoorD(object):
    def __init__(self, serviceCollection):
        """the constructor"""
        self.readers = {}
        self.authenticators = {}
        self.actuators = {}

        self.reader_to_authenticator = {}
        self.reader_to_actuator = {}

        self.serviceCollection = serviceCollection

        # do health report check every 5 seconds
        self.reported_health_check = internet.TimerService(5, self.check_reported_health)
        self.reported_health_check.setServiceParent(serviceCollection)

        # do actual health check every 59 seconds, so as not to overleave with the above (to often...)
        self.actual_health_check = internet.TimerService(59, self.check_actual_health)
        self.actual_health_check.setServiceParent(serviceCollection)

    # health monitoring interface
    def check_reported_health(self):
        """query all modules for their reported health, that is mainly the heartbeat monitoring"""
        for reader in self.readers:
            health = reader.report_health()
            if health != True:
                logger.error("ReportedHealthCheck", "Reader %s reported bad health: %s" % (reader, health))

        for authenticator in self.authenticators:
            health = authenticator.report_health()
            if health != True:
                logger.error("ReportedHealthCheck", "Authenticator %s reported bad health: %s" % (authenticator, health))

        if self.actuator:
            health = self.actuator.report_health()
            if health != True:
                logger.error("ReportedHealthCheck", "Actuator %s reported bad health: %s" % (self.actuator, health))

    def check_actual_health(self):
        """query all modules to initiate a component check"""
        pass

    # twisted support stuff
    def getServiceCollection(self):
        """this allows the service dependency facilities of Twisted do their thing"""
        return self.serviceCollection

    # configuration interface
    def add_reader(self, name, reader):
        """this adds a reader by the given name, will cause the reader to be started"""
        #self.readers.append(reader)

    def link_authenticator_to_reader(self, reader, authenticator):
        """link the authenticator to the reader, authenticators are queried in order of addition"""
        if self.reader_to_authenticator.has_key(reader):
            self.reader_to_authenticator[reader].append(authenticator)
        else:
            self.reader_to_authenticator[reader] = [authenticator]

    def add_authenticator(self, name, s={}):
        pass

    def set_actuator(self, name, d):
        pass

    def link_actuator_to_reader(self, reader, actuator):
        """link an actuator to a reader, which will cause it to operate if authentication is successful"""
        self.reader_to_actuator[reader] = actuator


    # app logic
    def handle_input(self, reader, token):
        """this is called by the Reader class when a card has been swiped"""
        reactor.callLater(0.1, self.authenticate_token, reader, token)

    def authenticate_token(self, reader, token):
        self.authenticators[0].authenticate(token
                                            ).addCallback(lambda r: self.handle_authentication_response(reader, r)
                                            ).addErrback(lambda e: self.handle_authentication_error(reader, e))

    def handle_authentication_response(self, reader, response):
        if response == "success":
            self.actuator.operate().addCallback(self.indicate_success)
        else:
            reader.indicate_failure()

    def handle_authentication_error(self, reader, error):
        reader.indicate_error()

    def indicate_success(self, throwaway):
        self.readers[0].indicate_success()


application = service.Application('doord')
serviceCollection = service.IServiceCollection(application)

authenticators.ThreadedPythonAuthenticator({ "file": "/Users/frederikfix/ds/rfidAuthenticator.py", "method": "check_access", "kwargs": { "hubId": 12, "resourceId": 12} })

doord = DoorD(serviceCollection)
doord.add_reader(readers.GeminiReader, { "port": 6320 })
doord.add_reader(readers.GeminiReader, { "port": 6321 })
doord.add_reader(readers.TCPConnectionReader, {  })
doord.add_reader(readers.WebInterfaceReader, {  })
doord.add_authenticator(authenticators.AlwaysAuthenticator)
doord.add_authenticator(authenticators.ThreadedPythonAuthenticator, { "file": "/Users/frederikfix/ds/rfidAuthenticator.py", "method": "check_access", "kwargs": { "hubId": 12, "resourceId": 12} })
doord.set_actuator(actuators.PerleActuator, { 'ip': '192.168.1.3', 'port': 23, 'user': 'admin', 'password': 'superuser' })

