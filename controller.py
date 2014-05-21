import endpoints
import logging
import datetime
import hashlib
import uuid
from protorpc import messages
from protorpc import message_types
from protorpc import remote
import json
from google.appengine.ext import ndb
import time
import collections
from google.appengine.api import background_thread
from google.appengine.api import mail


WEB_CLIENT_ID = 'greek-app'
ANDROID_CLIENT_ID = 'replace this with your Android client ID'
IOS_CLIENT_ID = 'replace this with your iOS client ID'
ANDROID_AUDIENCE = WEB_CLIENT_ID

"""Password Salt"""
SALT = 'Mary had a little lamb, whose fleece was white as snow and everywhere that mary went the lamb was sure to go'
"""error codes for returning errors"""
ERROR_BAD_ID = 'BAD_TOKEN'


class IncomingMessage(messages.Message):
    user_name = messages.StringField(1)
    token = messages.StringField(2)
    data = messages.StringField(3)

class OutgoingMessage(messages.Message):
    error = messages.StringField(1)
    data = messages.StringField(2)

"""MODELS"""
class User(ndb.Model):
    user_name = ndb.StringProperty()
    hash_pass = ndb.StringProperty()
    current_token = ndb.StringProperty()
    previous_token = ndb.StringProperty()
    timestamp = ndb.DateTimeProperty()
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    email = ndb.StringProperty()
    dob = ndb.DateProperty()
    address = ndb.StringProperty()
    city = ndb.StringProperty()
    state = ndb.StringProperty()
    zip = ndb.IntegerProperty()
    phone = ndb.IntegerProperty()
    class_year = ndb.IntegerProperty()
    is_alumni = ndb.BooleanProperty()
    organization = ndb.KeyProperty()
    tag = ndb.StringProperty(repeated=True)

class Organization(ndb.Model):
    name = ndb.StringProperty()
    school = ndb.StringProperty()
    type = ndb.StringProperty()


def emailSignup(key):
    new_user = key.get()
    to_email = new_user.email
    logging.debug(new_user.organization)
    token = new_user.organization.get().name
    token += new_user.first_name
    token += generate_token
    new_user.current_token = token
    signup_link = 'https://greek-app.appspot.com/newuser/'+token
    from_email = 'netegreek@greek-app.appspotmail.com'
    subject = "Registration for NeteGreek App!"
    body = "Hello!\n"
    body += "Your account has been created! To finish setting up your NeteGreek account please follow the link below.\n"
    body += signup_link + "\n\n -NeteGreek Team"
    new_user.put()
    mail.send_mail(from_email, to_email, subject, body)


def testEmail():
    from_email = 'netegreek@greek-app.appspotmail.com'
    body = "Hello! this is a test email! Have a great day!"
    to_email = 'derek.wene@yahoo.com'
    subject = 'test'
    mail.send_mail(from_email, to_email, subject, body)


def dumpJSON(item):
    dthandler = lambda obj: (
        obj.isoformat()
        if isinstance(obj, datetime.datetime)
        or isinstance(obj, datetime.date)
        else None)
    logging.debug(item)
    return json.dumps(item, dthandler)

def check_auth(user_name, token):
    user = User.query(User.user_name == user_name).get()
    if user.current_token == token:
        return user.key
    else:
        return False

def generate_token():
    return str(uuid.uuid4())

def get_key_from_token(token):
    user = User.query().filter(User.current_token == token).get()
    if user:
        return user.key
    return 0

@endpoints.api(name='netegreek', version='v1', allowed_client_ids=[WEB_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID],
               audiences=[ANDROID_AUDIENCE])
class RESTApi(remote.Service):
    USER_TOKEN = endpoints.ResourceContainer(message_types.VoidMessage, token=messages.StringField(1,
                                              variant=messages.Variant.STRING))

    ORG_IN = endpoints.ResourceContainer(IncomingMessage,
                                        user_name=messages.StringField(1, variant=messages.Variant.STRING),
                                        token=messages.StringField(2, variant=messages.Variant.STRING),
                                        data=messages.StringField(3, variant=messages.Variant.STRING))
    """USER REQUESTS"""
    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/register_organization',
                      http_method='POST', name='auth.register_organization')
    def register_organization(self, request):
        clump = json.loads(request.data)
        logging.error(clump)
        new_org = Organization(name=clump['organization']['name'], school=clump['organization']['school'])
        new_org.put()
        user = clump['user']
        new_user = User(user_name=user['user_name'])
        new_user.hash_pass = hashlib.sha224(user['password'] + SALT).hexdigest()
        new_user.first_name = user['first_name']
        new_user.last_name = user['last_name']
        new_user.email = user['email']
        new_user.organization = new_org.key
        new_user.tag = ['council']
        new_user.put()
        return OutgoingMessage(error='', data='OK')


    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/login',
                      http_method='GET', name='auth.login')
    def login(self, request):
        clump = json.loads(request.data)
        user_name = clump['user_name']
        password = clump['password']
        user = User.query(User.user_name == user_name).get()
        if user.hash_pass == hashlib.sha224(password + SALT).hexdigest():
            user.current_token = generate_token()
            return OutgoingMessage(data=user.current_token)
        return OutgoingMessage(error=ERROR_BAD_ID, data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/add_users',
                      http_method='POST', name='auth.add_users')
    def add_users(self, request):
        check_auth(request.user_name, request.token)
        clump = json.loads(request.data)
        logging.error(clump)
        for user in clump['users']:
            new_user = User()
            new_user.first_name = user['first_name']
            new_user.last_name = user['last_name']
            new_user.email = user['email']
            new_user.class_year = user['class_year']
            new_user.organization = User.query(User.user_name == request.user_name).get().organization
            new_user.put()
            emailSignup(new_user.key)

        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/new_user',
                      http_method='GET', name='auth.new_user')
    def register_user(self, request):
        data = json.loads(request.data)
        user = User.query(User.current_token == data["token"])
        if user and user.user_name == '':
            user_dict = user.__dict__
            logging.error(user_dict)
            user_dict["hash_pass"] = "xxx"
            user_dict["current_token"] = "xxx"
            user_dict["previous_token"] = "xxx"
            return OutgoingMessage(error='', data=json.dumps(user_dict))
        return OutgoingMessage(error=ERROR_BAD_ID, data='')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/add_credentials',
                      http_method='GET', name='auth.add_credentials')
    def add_credentials(self, request):
        data = json.loads(request.token)
        user = User.query(User.current_token == data["token"])
        if user and user.user_name == '':
            user_dict = user.__dict__
            logging.error(user_dict)
            user_dict["hash_pass"] = "xxx"
            user_dict["current_token"] = "xxx"
            user_dict["previous_token"] = "xxx"
            return OutgoingMessage(error='', data=json.dumps(user_dict))
        return OutgoingMessage(error=ERROR_BAD_ID, data='')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/test_email',
                      http_method='POST', name='auth.test_email')
    def test_email(self, request):
        background_thread.BackgroundThread(target=testEmail, args=[]).start()
        return OutgoingMessage(error='', data='OK')


"""
    @endpoints.method(IncomingMessage, OutgoingMessage, path='auth/register',
                      http_method='POST', name='auth.register')
    def add_users(self, request):

        user = User()
        user.user_name = request.user_name
        user.first_name = request.first_name
        user.last_name = request.last_name
        user.email = request.email
        user.hash_pass = hashlib.sha224(request.password + "this is a random string to help in the salting progress "
                                                           "blah").hexdigest()
        user.current_token = str(uuid.uuid4())
        user.time_stamp = datetime.datetime.now()
        user.put()
        time.sleep(.25)
        try:
            return UserCreds(current_token=user.current_token, first_name=user.first_name, last_name=user.last_name)
        except:
            return OutgoingMessage(message='error')

    @endpoints.method(USER_PASS, UserCreds, path='auth/login/{user_name}/{password}',
                      http_method='GET', name='auth.login')
    def login_user(self, request):
        user = User.query().filter(User.user_name == request.user_name).get()
        logging.error(user)
        if user:
            if user.hash_pass == hashlib.sha224(request.password + "this is a random string to help in the salting"
                                                                   " progress blah").hexdigest():
                user.current_token = str(uuid.uuid4())
                user.time_stamp = datetime.datetime.now()
                user.put()
                time.sleep(.5)
                return UserCreds(current_token=user.current_token, first_name=user.first_name, last_name=user.last_name)

        return OutgoingMessage(message='error')
"""
APPLICATION = endpoints.api_server([RESTApi])
