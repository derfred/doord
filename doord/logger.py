from twisted.python import log

def log(module, message):
    """this is wrapper for the logging infrastructure"""
    print module, message

def error(module, message):
    print module, message
