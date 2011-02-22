# !/usr/bin/env python

import os
import re
import logging
import doctest
import traceback
import datetime
import urllib

from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from google.appengine.api import namespace_manager
from google.appengine.ext.db.metadata import Namespace, Kind
from google.appengine.api import urlfetch

class UsedNamespace(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)

class MainPage(webapp.RequestHandler):
  """ Renders the main template."""
  def get(self):
    template_values = { 'title':'AJAX Add (via POST)', }
    path = os.path.join(os.path.dirname(__file__), "index.html")
    logging.info("looking for index.html in path->")
    logging.info(path)
    self.response.out.write(template.render(path, template_values))

class VerifyHandler(webapp.RequestHandler):
  """ Allows the functions defined in the RPCMethods class to be RPCed."""
  def __init__(self):
    webapp.RequestHandler.__init__(self)

  def post(self):
    #The request is passed in as json in the variable jsonrequest
    jsonrequest = self.request.get('jsonrequest')
    logging.info("Python verifier received: %s",jsonrequest)
    #The json request is passed to run_local and the result is written out as the response.
    try:
        protocol = 'https' if os.environ.get('HTTPS') == 'on' else 'http'
        url = '%s://%s/run' % (protocol, os.environ.get('HTTP_HOST'))
        logging.info('calling url %s', url)
        result = urlfetch.fetch(url = url,
                                payload = urllib.urlencode({'jsonrequest': jsonrequest}),
                                method = urlfetch.POST,
                                deadline = 3,
                                headers = {'Content-Type': 'application/x-www-form-urlencoded'})
        if result.status_code != 200:
            logging.error('The verifier returned an invalid status code: %s', result.status_code)
            logging.error('Content: %s', result.content)
        result = result.content
    except urlfetch.DownloadError:
        s = "Your code took too long to return. Your solution may be stuck "+\
            "in an infinite loop. Please try again."
        result = simplejson.dumps({"errors": s})
        logging.error(s)
    except Exception, e:
        errors = traceback.format_exc()
        logging.info('Error while executing tests: %s', errors)
        result = simplejson.dumps({'errors': '%s' % e})
    #logging.info('######## jsonResponse =%s', jsonResponse)
    #Change the MIME type to json.
    self.response.out.write(result)

class KeepAliveHandler(webapp.RequestHandler):
  """ Allows the functions defined in the RPCMethods class to be RPCed."""
  def __init__(self):
    webapp.RequestHandler.__init__(self)

  def get(self):
    #The request is passed in as json in the variable jsonrequest
    jsonrequest = '{"solution": "b=2", "tests": ">>> b\n 2"}'
    logging.info("Keep alive: %s",jsonrequest)
    #The json request is passed to run_local and the result is written out as the response.
    try:
        protocol = 'https' if os.environ.get('HTTPS') == 'on' else 'http'
        url = '%s://%s/verify' % (protocol, os.environ.get('HTTP_HOST'))
        logging.info('calling verifier: %s', url)
        result = urlfetch.fetch(url = url,
                                payload = urllib.urlencode({'jsonrequest': jsonrequest}),
                                method = urlfetch.POST,
                                deadline = 3,
                                headers = {'Content-Type': 'application/x-www-form-urlencoded'})
        result = result.content
    except Exception, e:
        errors = traceback.format_exc()
        logging.info('Error while executing keep_alive: %s', errors)
        result = simplejson.dumps({'errors': '%s' % e})
    #logging.info('######## jsonResponse =%s', jsonResponse)
    #Change the MIME type to json.
    self.response.out.write(result)

class RunHandler(webapp.RequestHandler):
  """ Allows the functions defined in the RPCMethods class to be RPCed."""
  def __init__(self):
    webapp.RequestHandler.__init__(self)

  def post(self):

    #The request is passed in as json in the variable jsonrequest
    jsonText = self.request.get('jsonrequest')
    logging.info("Python verifier received %s",jsonText)
    #The json request is passed to run_local and the result is written out as the response.
    jsonResponse = self.run_local(jsonText)
    #logging.info('######## jsonResponse =%s', jsonResponse)
    #Change the MIME type to json.
    self.response.out.write(jsonResponse)

  def run_local(self, requestJSON):
    namespace = UsedNamespace()
    namespace.put()
    namespace_manager.set_namespace('ns_%s' % namespace.key().id())
    logging.info('set namespace to: ns_%s' % namespace.key().id())
    
    #Add a try here to catch errors and return a better response
    requestDict = simplejson.loads(requestJSON)
    solution = requestDict['solution']
    tests = requestDict['tests']
    
    import StringIO
    import sys
    # Store App Engine's modified stdout so we can restore it later
    gae_stdout = sys.stdout
    # Redirect stdout to a StringIO object
    new_stdout = StringIO.StringIO()
    sys.stdout = new_stdout

    try:
        namespace = {}
        compiled = compile('from google.appengine.ext import db', 'submitted code', 'exec')
        exec compiled in namespace
        compiled = compile(solution, 'submitted code', 'exec')
        exec compiled in namespace

        test_cases = doctest.DocTestParser().get_examples(tests)
        results, solved = self.execute_test_cases(test_cases, namespace)
        
        # Get whatever was printed to stdout using the `print` statement (if necessary)
        printed = new_stdout.getvalue()
        # Restore App Engine's original stdout
        sys.stdout = gae_stdout
        
        responseDict = {"solved": solved , "results": results, "printed":printed}
        
        #Add a try here can catch errors. 
        responseJSON = simplejson.dumps(responseDict)
        logging.info("Python verifier returning %s",responseJSON)
        return responseJSON
    except:
        sys.stdout = gae_stdout
        errors = traceback.format_exc()
        logging.info("Python verifier returning errors =%s", errors)
        if len(errors) > 500:
            lines = errors.splitlines()
            i = len(lines) - 1
            errors = lines[i]
            i -= 1
            while i >= 0:
                line = lines[i]
                s = '%s\n%s' % (line, errors)
                if len(s) > 490:
                    break
                errors = s
                i -= 1
            errors = '...\n%s' % errors

        responseDict = {'errors': '%s' % errors}
        responseJSON = simplejson.dumps(responseDict)
        #logging.info("######## Returning json encoded errors %s", responseJSON)
        return responseJSON

  #Refactor for better readability.
  def execute_test_cases(self, testCases, namespace):
      resultList = []
      solved = True
      for e in testCases:
        if not e.want:
          exec e.source in namespace
          continue
        call = e.source.strip()
        got = eval(e.source.strip(), namespace)
        expected = eval(e.want, namespace)
        
        correct = True
        if got == expected:
          currect = True
        else:
          correct = False
          solved = False
        resultDict = {'call': call, 'expected': expected, 'received': "%(got)s" % {'got': got}, 'correct': correct}
        resultList.append(resultDict)
      return resultList, solved

class CleanDatabaseHandler(webapp.RequestHandler):
    def __init__(self):
        logging.info('__init__')
        webapp.RequestHandler.__init__(self)

    def post(self):
        self.clean()

    def get(self):
        logging.info('get')
        self.clean()

    def clean(self):
        deadline = datetime.datetime.now() - datetime.timedelta(seconds = 60)
        logging.info('number of namespaces: %s', Namespace.all().count())
        for namespace in Namespace.all():
            namespace_name = namespace.namespace_name
            logging.info('found namespace "%s"', namespace_name)
            if namespace_name[0 : 1] == '_':
                logging.info('skip system namespace: %s', namespace_name)
                continue
            mo = re.match('^ns_([0-9]+)$', namespace_name)
            if mo:
                ns = UsedNamespace.get_by_id(int(mo.group(1)))
                logging.info('UsedNamespace for namespace: %s', ns)
                if ns:
                    if ns.created > deadline:
                        logging.info('Cannot delete namespace %s yet', namespace_name)
                        continue #this namespace is still in use
                    db.delete(ns)
            #delete all kind in this namespace
            logging.info('deleting all kinds from namespace "%s"', namespace_name)
            namespace_manager.set_namespace(namespace_name)
            for kind in Kind.all():
                if namespace_name == '' and kind.kind_name == 'UsedNamespace':
                    logging.info('not delete UsedNamespace kind')
                elif kind.kind_name[0 : 1] == '_':
                    logging.info('skip system kind %s', kind.kind_name)
                else:
                    logging.info('delete kind %s', kind.kind_name)
                    try:
                        self.delete_kind(kind.kind_name)
                    except Exception, e:
                        logging.info('Got error: %s', e)
                        logging.info('Try to create the model class %s', kind.kind_name)
                        code = 'from google.appengine.ext import db\nclass %s(db.Model): pass' % kind.kind_name
                        compiled = compile(code, 'create model', 'exec')
                        namespace = {}
                        exec compiled in namespace
                        self.delete_kind(kind.kind_name)
        logging.info('number of UsedNamespace: %s', UsedNamespace.all().count())
        for ns in UsedNamespace.all():
            if ns.created > deadline:
                logging.info('Cannot delete UsedNamespace %s yet', ns.key().id())
                continue #this namespace is still in use
            logging.info('delete UsedNamespace %s', ns.key().id())
            db.delete(ns)
        self.response.out.write('Success')

    def delete_kind(self, kind_name):
        query = db.GqlQuery('SELECT __key__ FROM %s' % kind_name)
        n = 0
        while True:
            entities = query.fetch(500)
            if len(entities) == 0:
                break
            db.delete(entities)
            n += len(entities)
            logging.info('deleted %s entities', n)

def main():
  app = webapp.WSGIApplication([
    ('/', MainPage),
    ('/run', RunHandler),
    ('/verify', VerifyHandler),
    ('/clean_database', CleanDatabaseHandler),
    ('/keep_alive', KeepAliveHandler),
    ], debug=True)
  util.run_wsgi_app(app)

if __name__ == '__main__':
  main()