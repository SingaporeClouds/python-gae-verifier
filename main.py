# !/usr/bin/env python

import os
import logging
import doctest
import traceback

from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

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
    jsonText = self.request.get('jsonrequest')
    logging.info("Python verifier received %s",jsonText)
    #The json request is passed to run_local and the result is written out as the response.
    jsonResponse = self.run_local(jsonText)
    #logging.info('######## jsonResponse =%s', jsonResponse)
    #Change the MIME type to json.
    self.response.out.write(jsonResponse)

  def run_local(self, requestJSON):
    
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
        compiled = compile(solution, 'submitted code', 'exec')
        namespace = {}
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
        responseDict = {'errors': errors}
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
        resultDict = {'call':call, 'expected':expected, 'received': "%r" % got, 'correct':correct }
        resultList.append(resultDict)
      return resultList, solved

def main():
  app = webapp.WSGIApplication([
    ('/', MainPage),
    ('/verify', VerifyHandler),
    ], debug=True)
  util.run_wsgi_app(app)

if __name__ == '__main__':
  main()