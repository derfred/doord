#from ldaptor.protocols.ldap import ldapclient, ldapsyntax, ldapconnector, distinguishedname
#from ldaptor import ldapfilter

from twisted.internet import defer, reactor

import logger

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
