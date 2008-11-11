from twisted.internet import defer, reactor, threads

import logger, imp, os.path

class Authenticator(object):
    def __init__(self, config=None):
        """sets up the authenticator with an optional config object"""
        self.config = config

    def authenticate(self, token):
        """query the database to see if user it authorized, return True, False or raises an Exception"""
        pass

    def report_health(self):
        """callback to tell the daemon how this component is doing. Note this is supposed to return immediately"""
        return True

    def check_health(self):
        """callback to check with the components health. This is supposed to do an actual check and may return a Defer"""
        return defer.succeed(True)

class LDAPAuthenticator(object):
    def __init__(self, config=None):
        self.server = config['server']
        self.port = config.get('port', 125)

    def authenticate(self, token):
        """query the database to see if user it authorized, return True, False or raises an Exception"""
        c=ldapconnector.LDAPClientCreator(reactor, ldapclient.LDAPClient)
        d=c.connectAnonymously(config['base'], config['serviceLocationOverrides'])

class AlwaysAuthenticator(Authenticator):
    def authenticate(self, token):
        return defer.succeed(True)


class ThreadedPythonAuthenticator(Authenticator):
    def __init__(self, config={}):
        self.kwargs = config.get("kwargs", {})

        if config.has_key("file"):
            module_name = os.path.basename(config["file"]).replace(".py", "")
            dir_name = os.path.dirname(config["file"])
            fp, filename, description = imp.find_module(module_name, [dir_name])
        else:
            module_name = config["module"]
            fp, filename, description = imp.find_module(config["module"])

        try:
            module = imp.load_module(module_name, fp, filename, description)
            self.method = getattr(module, config["method"])
        finally:
            # Since we may exit via an exception, close fp explicitly.
            if fp:
                fp.close()

    def do_authenticate(self, token):
        try:
            return self.method(token, **self.kwargs)
        except Exception, e:
            return "error"

    def authenticate(self, token):
        return threads.deferToThread(self.do_authenticate, token)

