'''
Created on Nov 1, 2009

@author: Chris
'''
import unittest
from google.appengine.ext import db
import logging
from time import sleep
from singpath import models
from google.appengine.api import users
from django.utils import simplejson as json
from google.appengine.api import urlfetch

class Test(unittest.TestCase):

    def setUp(self):
        language = models.Interface(name='test').save()
        path = models.Path(name='test', interface=language).save()
        problemset = models.Problemset(name='test',path=path, minSolutionsNeeded=10).save()

        p = models.Problem(name="test",
                           solution="b=2",
                           tests = ">>> b \n 2",
                           problemset = problemset,
                           owner=users.get_current_user(),
                           author=users.get_current_user()).save()

        g = models.Game(name="test",
                          player1 = users.get_current_user(),
                          player2 = users.get_current_user()).save()

        level_badge = models.Level_Badge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path,
                         problemset=problemset).save()

    def tearDown(self):
        p = models.Problem.all().filter("name =", 'test').get().delete()
        g = models.Game.all().filter("name =", 'test').get().delete()

    #create a new test_suite for badge award testing.
    #def testCheckForBadges(self):
    def testVerify(self):
        pass
        
    def testCreateBadgeAwards(self):
        level_badge = models.Level_Badge.all().filter("name =", 'test').get()
        badgeAward = models.BadgeAward(user = users.get_current_user(), badge = level_badge)
        badgeAward.put()
        badge_awards = models.BadgeAward.all()
        self.assertTrue(badge_awards.count()==1)

    def testCreateBadges(self):
        path = models.Path.all().filter("name =", 'test').get()
        problemset = models.Problemset.all().filter('name =', 'test').get()

        badge = models.Badge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path)
        badge.put()
        badges = db.GqlQuery('SELECT * FROM Badge')
        self.assertTrue(badges.count()==2)

        level_badge = models.Level_Badge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path,
                         problemset=problemset)

        level_badge.put()
        badges = db.GqlQuery('SELECT * FROM Badge')
        self.assertTrue(badges.count()==3)
        level_badges = models.Level_Badge.all()
        self.assertTrue(level_badges.count()==2)

        mastery_badge = models.Mastery_Badge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path,
                         problemset=problemset)

        mastery_badge.put()

        badges = db.GqlQuery('SELECT * FROM Badge')
        self.assertTrue(badges.count()==4)
        mastery_badges = models.Mastery_Badge.all()
        self.assertTrue(mastery_badges.count()==1)

        achievement_badge = models.AchievementBadge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path)
        achievement_badge.put()

        badges = db.GqlQuery('SELECT * FROM Badge')
        self.assertTrue(badges.count()==5)
        achievement_badges = models.AchievementBadge.all()
        self.assertTrue(achievement_badges.count()==1)

        custom_badge = models.Custom_Badge(name="test",
                         owner=users.get_current_user(),
                         description="Test Badge",
                         url="static/SingpathBadge.gif",
                         path=path)
        custom_badge.put()

        badges = db.GqlQuery('SELECT * FROM Badge')
        self.assertTrue(badges.count()==6)
        custom_badges = models.Custom_Badge.all()
        self.assertTrue(custom_badges.count()==1)

   
    def testCreateAndDeleteProblem(self):
        problems = db.GqlQuery('SELECT * FROM Problem ORDER BY created DESC')
        self.assertTrue(problems.count()==1)
        p = models.Problem(name="Test Problem",
                           solution="Test Solution",
                           owner=users.get_current_user(),
                           author=users.get_current_user())
        p.save()
        problems = db.GqlQuery('SELECT * FROM Problem ORDER BY created DESC')
        self.assertTrue(problems.count()==2)
        p.delete()
        problems = db.GqlQuery('SELECT * FROM Problem ORDER BY created DESC')
        self.assertTrue(problems.count()==1)

    def testCreateAndDeleteGame(self):
        games = db.GqlQuery('SELECT * FROM Game')
        self.assertTrue(games.count()==1)
        g = models.Game()
        g.save()
        games = db.GqlQuery('SELECT * FROM Game')
        self.assertTrue(games.count()==2)
        #self.assertTrue(
        tenMinGames = models.Game.all().filter("game_type =", g.timed_interview)
        self.assertTrue(tenMinGames.count()==2)
        g.delete()
        games = db.GqlQuery('SELECT * FROM Game')
        self.assertTrue(games.count()==1)

    def testGetGameStatus(self):
        g = models.Game()
        #New problems should start off awaiting problems.
        self.assertTrue(g.status == g.awaiting_problems)
        g.update_status()
        #First status update should not change the status awaiting problems.
        self.assertTrue(g.status == g.awaiting_problems)
        #Need to replace this with the reference to p that the model can lookup.
        p = models.Problem.all().filter("name =", 'test').get()

        problem_id = p.key().id()

        # Need to get the set that problesm should be added from.
        problemset = models.Problemset.all().filter("name =", 'test').get()
        problemset_id = problemset.key().id()


        g.load_problems(1, str(problemset_id))
        self.assertTrue(g.problems==[problem_id])
        self.assertTrue(g.status == g.awaiting_timelimit)
        g.save()

        #Ensure that problems don't get loaded when more are requested than avaiable.
        g2 = models.Game()
        g2.load_problems(2, problemset_id)
        self.assertTrue(g2.problems==[])

        #Add a few more problems and create another game.
        for x in range(5):
          p2 = models.Problem(name="Test Problem", problemset=problemset, solution="Test Solution", owner=users.get_current_user(), author=users.get_current_user())
          p2.save()
          #Ensure that problems don't get loaded when more are requested than avaiable.
        g3 = models.Game()
        g3.load_problems(4, str(problemset_id))
        self.assertTrue(len(g3.problems)==4)
        self.assertTrue(g3.problems.count(problem_id)==1)

        #Solved problem_id and make sure that problem is not longer part of game problems

        pu = models.ProblemUser(name = "Test Problem User", problem = p, author = users.get_current_user(), game = g, solved = True)
        pu.save()
        g.solvedProblems.append(p.key().id())
        g.put()
        
        
        #Load problems for game again now that there is a problem solved and ensure orginal problem_id is not added to game.
        g3.load_problems(4, str(problemset_id))
        self.assertTrue(g3.problems.count(problem_id)==0)

        g.set_timelimit(5000)

        #You can't just save problems here to close a game. 
        #You have to add solved problems to the list and then check_for_solved_problem should catch the error.
        
        self.assertTrue(g.status == g.game_closed)

        #Should still be accepting solutions as long as solution fails.
        pu.solved=False
        pu.save()
        g.solvedProblems = []
        g.put()
        
        g.update_status()
        self.assertTrue(g.status == g.accepting_solutions)

        #Ensure that the game closes after timeouts. Comment out to speed up tests
        #sleep(1)
        #g.set_timelimit(1)
        #self.assertTrue(g.status == g.game_closed)

    def testCreateAndDeleteProblemUser(self):
        problemUsers = db.GqlQuery('SELECT * FROM ProblemUser')
        self.assertTrue(problemUsers.count()==0)
        p = models.Problem.all().filter("name =", 'test').get()
        g = models.Game.all().filter("name =", 'test').get()

        pu = models.ProblemUser(name = "Test Problem User",
                           problem = p,
                           author = users.get_current_user(),
                           game = g,
                           solution = "Test PU Solution",
                           solved = False)
        pu.save()
        problemUsers = db.GqlQuery('SELECT * FROM ProblemUser')
        self.assertTrue(problemUsers.count()==1)
        self.assertTrue(pu.problem == p)
        self.assertTrue(pu.game == g)
        self.assertFalse(pu.solved)
        pu.solved = True
        self.assertTrue(pu.solved)

        self.assertTrue(p.problem_users.count()==1)
        self.assertTrue(g.problem_users.count()==1)
        pu.delete()
        self.assertTrue(p.problem_users.count()==0)
        self.assertTrue(g.problem_users.count()==0)
        #for pu in p.problem_users:
        #    logging.info('%s: %s' % (pu.name, pu.solution))

    def testCreateAndDeleteSetPathAPI(self):
        s = models.Problemset(name='test', minSolutionsNeeded=10).save()
        self.assertTrue("test" == models.Problemset.all().filter("name =", 'test').get().name)
        p = models.Path(name='test').save()
        self.assertTrue("test" == models.Path.all().filter("name =", 'test').get().name)
        a = models.Interface(name='test').save()
        self.assertTrue("test" == models.Interface.all().filter("name =", 'test').get().name)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
