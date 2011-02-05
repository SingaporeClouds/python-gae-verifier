#import random
#import datetime
#import hashlib
#import logging
#
#def namespace_manager_default_namespace_for_request():
#    """Determine which namespace is to be used for a request.
#    """
#    md5 = hashlib.md5()
#    md5.update('%s-%s' % (random.random(), datetime.datetime.now()))
#    name = md5.hexdigest()
#    logging.info('set namespace: %s', name)
#    return name
