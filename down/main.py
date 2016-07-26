
import webapp2
import jinja2
import os
from google.appengine.ext import ndb
from google.appengine.api import users
import datetime
import time

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

class User(ndb.Model):
    name = ndb.TextProperty()
    password = ndb.TextProperty()

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
    def get(self):
        template = jinja_environment.get_template('welcome.html')
        self.response.write(template.render())

class MainHandler(webapp2.RequestHandler):
    def get(self):
        blog_posts = Post.query().order(-Post.date).fetch()
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
<<<<<<< HEAD

        comments = Comment.query(Comment.post_key == post.key).order(-Post.date).fetch()
=======
        
        comments = Comment.query(Comment.post_key == post.key).fetch()
>>>>>>> 32613bfc4b6d039b8ebd9ff28dcd8a16fa7359d0


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
    ('/post', PostHandler)

], debug=True)
