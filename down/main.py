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

        friends = service.people().list(userId='me', collection='visible').execute(http=http)['items'] # list of all friends

        friends_ids = [plus_user['id']]

        for friend in friends:  #loop will create a list of all the user's friends' IDs
            friends_ids.append(friend['id'])


        user=User(email=emailAddress, friends_list = friends_ids, name = plus_user['displayName'], picture_url=plus_user['image']['url'])
        user.put()

    return user

def updateFriendsList(currentUser):
    http = decorator.http()
    friends = service.people().list(userId='me', collection='visible').execute(http=http)['items']
    plus_user = service.people().get(userId='me').execute(http=http)

    friends_ids = [plus_user['id']]

    for friend in friends:  #loop will create a list of all the user's friends' IDs
        friends_ids.append(friend['id'])

    currentUser.friends_list = friends_ids


class User(ndb.Model): #give u a user object and the plus user if logged in
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    picture_url = ndb.StringProperty()
    google_ID = ndb.StringProperty()
    friends_list = ndb.StringProperty(repeated=True)



    def url(self):
        url='/user?key='+self.key.urlsafe()
        return url


class Post(ndb.Model):
    text = ndb.TextProperty()
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    google_plusID = ndb.StringProperty()
    user_key=ndb.KeyProperty(kind=User)
    slideCount=ndb.IntegerProperty()
    sliderList=ndb.StringProperty(repeated=True)

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

class LoginHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):

        user = users.get_current_user()
        if user:
            self.redirect('/home')

        else:
            login_url = users.create_login_url('/')
            greeting = '<a href="{}">Sign in</a>'.format(login_url)
            self.response.write(
               '<html><body>{}</body></html>'.format(greeting))

            # template = jinja_environment.get_template('welcome.html')
            # self.response.write(template.render())


class WelcomeHandler(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()
        if user:
            self.redirect('/home')

        else:
            login_url = users.create_login_url('/login')
            template = jinja_environment.get_template('welcome.html')
            self.response.write(template.render({'login_url':login_url}))



class MainHandler(webapp2.RequestHandler):

    @decorator.oauth_required
    def get(self):

        user = users.get_current_user()
        if user: #if there is a user, welcome user, and option to sign out

            http = decorator.http()
            plus_user = service.people().get(userId='me').execute(http=http)

            updateFriendsList(user)


            user_model = getOrCreateUser(user.email())

            #greeting on top of the page and signout button
            logout_url = users.create_logout_url('/')
            greeting = 'Welcome, {}! (<a href="{}">sign out</a>)'.format(
                user_model.name, logout_url)
            self.response.write(
               '<html><body>{}</body></html>'.format(greeting))



            blog_posts = Post.query().order(-Post.date).fetch() # return list

            friends_posts = []

            for post in blog_posts:
                if post.google_plusID in user.friends_list:
                        friends_posts.append(post)

            # go through all the blog_posts and pick only the ones that were made by a friend

            template_values = {'posts':friends_posts, 'plus_user':plus_user, 'user':user} #fetch all the posts
            template = jinja_environment.get_template('home.html')
            self.response.write(template.render(template_values))

        else: #no user, option sign in
            self.redirect('/')


    @decorator.oauth_required
    def post(self):
        http = decorator.http()
        plus_user = service.people().get(userId='me').execute(http=http)

        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        # Step 1: Get info from the Request
        text = self.request.get('text')
        # Step 2: Logic -- interact with the database
        post = Post(name = user_model.name, text=text, user_key=user_model.key, google_plusID= plus_user['id'], slideCount = 0, sliderList=[])
        #google_plusID property takes current user ID and attaches it to the new post


        post.put()
        # Step 3: Render a response
        self.redirect('/home')

class DeleteHandler(webapp2.RequestHandler):
    def post(self):
        urlsafe_key = self.request.get('key')
        key = ndb.Key(urlsafe=urlsafe_key)
        key.delete()
        self.redirect('/home')

class DeleteCommentHandler(webapp2.RequestHandler):
    def post(self):
        # Where is this key coming from?
        # It should be in the form somewhere,
        # similar to how the commentkey is done
        urlsafe_key = self.request.get('key')
        # Added a log to see what the value of the key is.
        # It was empty
        #logging.info("urlsafe_key: " + urlsafe_key)
        key = ndb.Key(urlsafe=urlsafe_key)
        post = key.get()

        comment_urlsafe_key = self.request.get('commentkey')
        key = ndb.Key(urlsafe=comment_urlsafe_key)
        key.delete()
        self.redirect(post.url())


class PostHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def get(self):
        sliders=[]
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        # Step 1: Get info from the Request
        urlsafe_key = self.request.get('key')

        # Step 2: Logic -- interact with the database
        key = ndb.Key(urlsafe=urlsafe_key)
        post = key.get()
        for sliderEmail in post.sliderList:
            slider=getOrCreateUser(sliderEmail)
            sliders.append(slider)

        comments = Comment.query(Comment.post_key == post.key).order(-Post.date).fetch()
        # Step 3: Render a response

        template_values = {'post':post, 'comments':comments, 'sliders':sliders, 'user':user} #fetch all the posts
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

class SlideThruHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def post(self):
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        urlsafe_key = self.request.get('key')
        key = ndb.Key(urlsafe=urlsafe_key)
        post = key.get()
        post.slideCount=post.slideCount+1
        post.sliderList.append(user.email())
        post.put()
        template = jinja_environment.get_template('home.html')
        self.response.write(template.render({'post':post, 'email':user.email()}))
        self.redirect('/home')

class FlakeHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def post(self):
        user = users.get_current_user()
        user_model = getOrCreateUser(user.email())
        urlsafe_key = self.request.get('key')
        key = ndb.Key(urlsafe=urlsafe_key)
        post = key.get()
        post.slideCount=post.slideCount-1
        i=post.sliderList.index(user.email())
        del post.sliderList[i]
        post.put()
        template = jinja_environment.get_template('home.html')
        self.response.write(template.render({'post':post, 'email':user.email()}))
        self.redirect('/home')


app = webapp2.WSGIApplication([
    ('/', WelcomeHandler),
    ('/login', LoginHandler),
    ('/home', MainHandler),
    ('/post', PostHandler),
    ('/delete', DeleteHandler),
    ('/deletecomment', DeleteCommentHandler),
    ('/slideThru', SlideThruHandler),
    ('/flake', FlakeHandler),
    (decorator.callback_path, decorator.callback_handler())

], debug=True)
