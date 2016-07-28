import webapp2
import jinja2
import os
from google.appengine.ext import ndb
from google.appengine.api import users
import datetime
import time
from oauth2client import client
from googleapiclient import sample_tools
import httplib2
import logging
import os
import pickle
import pprint

from googleapiclient import discovery
from oauth2client import client
from oauth2client.contrib import appengine
from google.appengine.api import memcache

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

http = httplib2.Http(memcache)
service = discovery.build("plus", "v1", http=http)
decorator = appengine.oauth2decorator_from_clientsecrets(
    CLIENT_SECRETS,
    scope=['https://www.googleapis.com/auth/plus.me','https://www.googleapis.com/auth/plus.login'],
    message="Client secrets is missing")

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

# jinja_environment.globals.update(formatDate=formatDate)
def getOrCreateUser(emailAddress):
    user=User.query(User.email==emailAddress).get()
    if not user:
        http = decorator.http()
        plus_user = service.people().get(userId='me').execute(http=http)
        user=User(email=emailAddress, name=plus_user['displayName'], picture_url=plus_user['image']['url'])
        user.put()
    return user

class User(ndb.Model): #give u a user object and the plus user if logged in
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    picture_url = ndb.StringProperty()
    

    def url(self):
        url='/user?key='+self.key.urlsafe()
        return url


class Post(ndb.Model):
    text = ndb.TextProperty()
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    user_key=ndb.KeyProperty(kind=User)

    def url(self):
        return '/post?key='+ self.key.urlsafe() #you need to use self, not post.key.blah


class Comment(ndb.Model):
    text = ndb.TextProperty()
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    post_key = ndb.KeyProperty(kind=Post)
    user_key = ndb.KeyProperty(kind=User)

class SlideIn(ndb.Model):
    post_key = ndb.KeyProperty(kind=Post)
    user_key = ndb.KeyProperty(kind=User)

class WelcomeHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        # Authenticate and construct service.d
        # service, flags = sample_tools.init(
        #     [], 'plus', 'v1', __doc__, "/Users/demouser/Desktop/cssi/im_down/down/lib",
        #     scope='https://www.googleapis.com/auth/plus.me')
        user = users.get_current_user()
        if user:
            self.redirect('/home')

        else:
            login_url = users.create_login_url('/')
            greeting = '<a href="{}">Sign in</a>'.format(login_url)
            self.response.write(
               '<html><body>{}</body></html>'.format(greeting))

            template = jinja_environment.get_template('welcome.html')
            self.response.write(template.render())



class MainHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):

        user = users.get_current_user()
        if user: #if there is a user, welcome user, and option to sign out

            http = decorator.http()
            logging.info(help(service.people().list))
            friends = service.people().list(userId='me', collection='visible').execute(http=http)
            logging.info(pprint.pprint(friends))

            # put ids of friends into a list

            plus_user = service.people().get(userId='me').execute(http=http)


            user_model = getOrCreateUser(user.email())


            logout_url = users.create_logout_url('/home')
            greeting = 'Welcome, {}! (<a href="{}">sign out</a>)'.format(
                user_model.name, logout_url)

            self.response.write(
               '<html><body>{}</body></html>'.format(greeting))

            blog_posts = Post.query().order(-Post.date).fetch()

            # go through all the blog_posts and pick only the ones that were made by a friend

            template_values = {'posts':blog_posts, 'plus_user':plus_user} #fetch all the posts

            template = jinja_environment.get_template('home.html')
            self.response.write(template.render(template_values))

        else: #no user, option sign in
            self.redirect('/')

    def post(self):
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        # Step 1: Get info from the Request
        text = self.request.get('text')
        # Step 2: Logic -- interact with the database
        post = Post(name = user_model.name, text=text, user_key=user_model.key)

        post.put()
        # Step 3: Render a response
        self.redirect('/home')

class DeleteHandler(webapp2.RequestHandler):
    def post(self):
        urlsafe_key = self.request.get('key')
        key = ndb.Key(urlsafe=urlsafe_key)
        key.delete()
        self.redirect('/home')
class PostHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def get(self):
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        # Step 1: Get info from the Request
        urlsafe_key = self.request.get('key')

        # Step 2: Logic -- interact with the database
        key = ndb.Key(urlsafe=urlsafe_key)
        post = key.get()

        comments = Comment.query(Comment.post_key == post.key).order(-Post.date).fetch()

        # Step 3: Render a response
        template_values = {'post':post, 'comments':comments} #fetch all the posts
        template = jinja_environment.get_template('post.html')
        self.response.write(template.render(template_values))

    def post(self):
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        # Step 1: Get info from the Request
        text = self.request.get('comment') #the comment string
        post_key_urlsafe = self.request.get('key') #string thats coming out of the request
        # Step 2: Logic -- interact with the database
        post_key = ndb.Key(urlsafe=post_key_urlsafe) #go from a string to a key
        post = post_key.get() #turns into the entity ( the post )

        comment = Comment(text=text, name= user_model.name, post_key=post.key, user_key=user_model.key)
        comment.put()

        # Step 3: Render a response
        self.redirect(post.url())

app = webapp2.WSGIApplication([
    ('/', WelcomeHandler),
    ('/home', MainHandler),
    ('/post', PostHandler),
    ('/delete', DeleteHandler),
    (decorator.callback_path, decorator.callback_handler())

], debug=True)
