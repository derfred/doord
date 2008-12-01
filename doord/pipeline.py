import actuators, authenticators, readers, logger
from twisted.internet import defer, reactor

class Pipeline(object):
    def __init__(self, doord, name, options):
        self.name = name
        self.doord = doord

        self.reader = None
        self.authenticator = None
        self.actuator = None

        self.load_config(options)

    # twisted support stuff
    def getServiceCollection(self):
        """this allows the service dependency facilities of Twisted do their thing"""
        return self.doord.getServiceCollection()

    def load_config(self, options):
        self.reader = getattr(readers, options['reader']['type'])(self, options['reader'])
        if options.has_key('authenticator'):
            self.authenticator = getattr(authenticators, options['authenticator']['type'])(options['authenticator'])
        self.actuator = getattr(actuators, options['actuator']['type'])(options['actuator'])

    # health checks
    def report_health(self):
        health = self.reader.report_health()
        if health != True:
            return "%s: %s" % (self.reader, health)

        if self.authenticator:
            health = self.authenticator.report_health()
            if health != True:
                return "%s: %s" % (self.authenticator, health)

        health = self.reader.report_health()
        if health != True:
            return "%s: %s" % (self.reader, health)

        return True

    def check_health(self):
        return defer.succeed(True)

    # app logic
    def handle_input(self, token):
        """this is called by the Reader class when a card has been swiped"""
        reactor.callLater(0.1, self.authenticate_token, token)

    def authenticate_token(self, token):
        if self.authenticator:
            self.authenticator.authenticate(token
                                            ).addCallback(lambda r: self.handle_authentication_response(r, token),
                                            ).addErrback(self.handle_authentication_error)
        else:
            self.handle_authentication_response("success", token)

    def handle_authentication_response(self, response, token):
        if response == "success":
            self.actuator.operate().addCallback(self.indicate_success)
        else:
            self.reader.indicate_failure()

    def handle_authentication_error(self, error):
        self.reader.indicate_error()

    def indicate_success(self, throwaway):
        self.reader.indicate_success()
