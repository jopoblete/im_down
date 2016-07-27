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

from googleapiclient import discovery
from oauth2client import client
from oauth2client.contrib import appengine
from google.appengine.api import memcache

CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

http = httplib2.Http(memcache)
service = discovery.build("plus", "v1", http=http)
decorator = appengine.oauth2decorator_from_clientsecrets(
    CLIENT_SECRETS,
    scope='https://www.googleapis.com/auth/plus.me',
    message="Client secrets is missing")

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

# jinja_environment.globals.update(formatDate=formatDate)

class User(ndb.Model):
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    picture=ndb.BlobProperty()
    def url(self):
        url='/user?key='+self.key.urlsafe()
        return url


class Post(ndb.Model):
    text = ndb.TextProperty()
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    def url(self):
        return '/post?key='+ self.key.urlsafe() #you need to use self, not post.key.blah


class Comment(ndb.Model):
    text = ndb.TextProperty()
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    post_key = ndb.KeyProperty(kind=Post)

class SlideIn(ndb.Model):
    post_key = ndb.KeyProperty(kind=Post)

class WelcomeHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):
        # Authenticate and construct service.d
        # service, flags = sample_tools.init(
        #     [], 'plus', 'v1', __doc__, "/Users/demouser/Desktop/cssi/im_down/down/lib",
        #     scope='https://www.googleapis.com/auth/plus.me')
        http = decorator.http()
        plus_user = service.people().get(userId='me').execute(http=http)
        template = jinja_environment.get_template('welcome.html')
        self.response.write(template.render(
            {'plus_user_image': plus_user['image']['url']}))

class MainHandler(webapp2.RequestHandler):
    def get(self):
        blog_posts = Post.query().order(-Post.date).fetch()
        user = users.get_current_user()
        userEmail = users.get_current_user().email()

        newuser = User(email=userEmail)

        template_values = {'posts':blog_posts} #fetch all the posts
        template = jinja_environment.get_template('home.html')
        self.response.write(template.render(template_values))

    def post(self):
        # Step 1: Get info from the Request
        text = self.request.get('text')
        # Step 2: Logic -- interact with the database
        post = Post(name = 'yungmarmar', text=text)

        post.put()

        # Step 3: Render a response
        self.redirect('/home')


class PostHandler(webapp2.RequestHandler):
    def get(self):
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
        # Step 1: Get info from the Request
        text = self.request.get('comment') #the comment string
        post_key_urlsafe = self.request.get('key') #string thats coming out of the request

        # Step 2: Logic -- interact with the database
        post_key = ndb.Key(urlsafe=post_key_urlsafe) #go from a string to a key
        post = post_key.get() #turns into the entity ( the post )

        comment = Comment(text=text, name= 'Loser', post_key=post.key)
        comment.put()




        # Step 3: Render a response
        self.redirect(post.url())



app = webapp2.WSGIApplication([
    ('/', WelcomeHandler),
    ('/home', MainHandler),
    ('/post', PostHandler),
    (decorator.callback_path, decorator.callback_handler())

], debug=True)
