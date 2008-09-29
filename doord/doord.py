import sys
sys.path.append(".")

import readers, actuators, authenticators, logger
from twisted.internet import defer, reactor, task
from twisted.application import internet, service


class DoorD(object):
    def __init__(self, serviceCollection):
        """the constructor"""
        self.readers = []
        self.actuator = None
        self.authenticators = []
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
    def add_reader(self, reader_class, config = {}):
        """append a new reader to the list of input readers"""
        self.readers.append(reader_class(dict(config, doord=self)))

    def set_actuator(self, actuator_class, config = {}):
        """append a new actuator to the list of available actuators"""
        self.actuator = actuator_class(config)

    def add_authenticator(self, authenticator_class, config = {}):
        """append a new authenticator to the list of available authenticators"""
        self.authenticators.append(authenticator_class(config))

    # app logic
    def handle_input(self, reader, token):
        """this is called by the Reader class when a card has been swiped"""
        reactor.callLater(0.1, self.authenticate_token, reader, token)

    def authenticate_token(self, reader, token):
        self.authenticators[0].authenticate(token
                                            ).addCallback(lambda r: self.handle_authentication_response(reader, r)
                                            ).addErrback(lambda e: self.handle_authentication_error(reader, e))

    def handle_authentication_response(self, reader, response):
        if response:
            self.actuator.operate().addCallback(self.indicate_success)
        else:
            reader.indicate_failure()

    def handle_authentication_error(self, reader, error):
        reader.indicate_error()

    def indicate_success(self, throwaway):
        self.readers[0].indicate_success()


application = service.Application('doord')
serviceCollection = service.IServiceCollection(application)

doord = DoorD(serviceCollection)
doord.add_reader(readers.GeminiReader, { "port": 6320 })
doord.add_reader(readers.GeminiReader, { "port": 6321 })
doord.add_reader(readers.TCPConnectionReader, {  })
doord.add_reader(readers.WebInterfaceReader, {  })
doord.add_authenticator(authenticators.AlwaysAuthenticator)
doord.set_actuator(actuators.PerleActuator, { 'ip': '192.168.1.3', 'port': 23, 'user': 'admin', 'password': 'superuser' })

