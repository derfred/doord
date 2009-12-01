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

    def __str__(self):
        return "Pipeline<%s>" % self.name

    # twisted support stuff
    def getServiceCollection(self):
        """this allows the service dependency facilities of Twisted do their thing"""
        return self.doord.getServiceCollection()

    def load_config(self, options):
        self.reader = getattr(readers, options['reader']['type'])(self, options['reader'])
        if options.has_key('authenticator'):
            self.authenticator = getattr(authenticators, options['authenticator']['type'])(options['authenticator'])
        self.actuator = getattr(actuators, options['actuator']['type'])(options['actuator'])
        self.permissive = options.get("permissive", False)

    # health checks
    def report_health(self):
        health = self.reader.report_health()
        if health != True:
            log_message = "%s: %s" % (self.reader, health)
            self.call_health_check_failback(self.reader, log_message)
            return log_message

        if self.authenticator:
            health = self.authenticator.report_health()
            if health != True:
                log_message = "%s: %s" % (self.authenticator, health)
                self.call_health_check_failback(self.authenticator, log_message)
                return log_message

        health = self.actuator.report_health()
        if health != True:
            log_message = "%s: %s" % (self.actuator, health)
            self.call_health_check_failback(self.actuator, log_message)
            return log_message

        return True

    def check_health(self):
        return defer.succeed(True)

    def call_health_check_failback(self, object, health):
        command = object.get_config("health_check_failback", None)
        if command:
            subprocess.Popen(command, shell=True, env={ log_message: health })

    # app logic
    def handle_input(self, token):
        """this is called by the Reader class when a card has been swiped"""
        reactor.callLater(0.1, self.authenticate_token, token)

    def authenticate_token(self, token):
        if self.authenticator:
            logger.log("Pipeline %s" % self.name, "authenticating token %s" % token)
            self.authenticator.authenticate(token
                                            ).addCallback(lambda r: self.handle_authentication_response(r, token),
                                            ).addErrback(self.handle_authentication_error)
        else:
            self.handle_authentication_response("success", token)

    def handle_authentication_response(self, response, token):
        if response == "success" or self.permissive:
            logger.log("Pipeline %s" % self.name, "opening door for authentication result %s" % response)
            deferred = self.actuator.operate()
            if deferred:
                deferred.addCallback(self.indicate_success)
        else:
            logger.log("Pipeline %s" % self.name, "refusing entry to token %s" % token)
            self.reader.indicate_failure()

    def handle_authentication_error(self, error):
        self.reader.indicate_error()

    def indicate_success(self, throwaway):
        self.reader.indicate_success()
