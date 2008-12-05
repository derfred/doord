import sys
sys.path.append(".")

import logger, yaml, pipeline
from twisted.internet import defer, reactor, task
from twisted.application import internet, service


class DoorD(object):
    def __init__(self, serviceCollection):
        """the constructor"""
        self.pipelines = []
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
        error = False
        for p in self.pipelines:
            health = p.report_health()
            if health != True:
                logger.error("ReportedHealthCheck", "Pipeline %s reported bad health: %s" % (p, health))

        if not error:
            logger.log("ReportedHealthCheck", "no errors")


    def check_actual_health(self):
        """query all modules to initiate a component check"""
        pass
 
    # twisted support stuff
    def getServiceCollection(self):
        """this allows the service dependency facilities of Twisted do their thing"""
        return self.serviceCollection
 
    # configuration interface
    def load_config(self, filename):
        """this will load the configuration from the file"""
        config = yaml.load(open(filename).read())
        self.pipelines = map(lambda c: pipeline.Pipeline(self, c[0], c[1]), config.items())


application = service.Application('doord')
serviceCollection = service.IServiceCollection(application)

doord = DoorD(serviceCollection)
doord.load_config('doord.config')

