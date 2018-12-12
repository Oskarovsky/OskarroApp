import datetime
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, abort, send_from_directory, make_response
from flask import render_template
from flask import flash
from flask import request
from flask import url_for
from flask import redirect
from flask import session

# OAuth LIB
from os import environ as env
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv, find_dotenv
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode

import content_management
import os
import json
import jwt
import redis as redis


### ABOUT CONTENT ###

app = Flask(__name__, static_url_path='/static')

# START OAuth ----------------------------------
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id='xaTwJSSL6BkiDhFLFxY8okLueLSLcAqd',
    client_secret='ALN8y9-aX5ZpVtXcZavM9TyjW1J9qPTTzOdbboGCLsi-issBzwQ0lhE7UW2v0PB3',
    api_base_url='https://oskarro.eu.auth0.com',
    access_token_url='https://oskarro.eu.auth0.com/oauth/token',
    authorize_url='https://oskarro.eu.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)

# END OAuth ----------------------------------


app.secret_key = b'35dvgy8i(UHoiawu hftvd9'
app.jwt_secret_key = 'DjOskarroInDaMix'

# content of main site
TOPIC_DICT = content_management.Content()

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.upload_path = Path(os.path.join(APP_ROOT, './static/uploads'))

app.config.update(
    #SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_TYPE = 'redis'
)


# path to the app directory
cwd = os.path.dirname(os.path.realpath(__file__))

redis = redis.Redis()




with open("users.json") as f:
    data = json.load(f)
    app.users = data['users']


def creating_token(object,expiration):
    payload = { "user" : redis.get(session['current_user']).decode('utf-8'),
                "file" : object,
                "exp"  : (datetime.datetime.utcnow() + datetime.timedelta(seconds=expiration))}
    return jwt.encode(payload, app.jwt_secret_key, algorithm='HS256')


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'current_user' not in session:
            abort(401)
        if redis.get(session['current_user'])==None:
            abort(401)
        return f(*args, **kwargs)

    return wrapper



# WEB PAGES

@app.route('/slyko/')
def homepage():
    if not session.get('current_user'):
        return redirect(url_for('signin'))
    return render_template('main.html', TOPIC_DICT=TOPIC_DICT)



@app.route('/slyko/signin',  methods=['GET', 'POST'])
def signin():
    error = None
    if request.method == 'POST':
        current = None
        for usr in data['users']:
            if request.form['username'] == usr['username'] and request.form['password'] == usr['password']:
                current = usr
                session['logged_in'] = True
                break
        if current:
            sid = str(uuid.uuid4())
            session['current_user'] = sid
            session['logged_in'] = True
            redis.set(session['current_user'], usr['username'], ex=300)
            return redirect(url_for('homepage'))
        else:
            flash('Invalid Credentials. Please try again')
            return render_template('signin.html', error=True)

    return render_template('signin.html')


@app.route('/slyko/signup')
def signup():
    return render_template("signup.html")


# START OAuth ---------------------

# Here we're using the /callback route.
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')


@app.route('/slyko/login')
def login():
    return auth0.authorize_redirect(redirect_uri='http://127.0.0.1:5002/slyko/', audience='https://oskarro.eu.auth0.com/userinfo')


def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/slyko/login')
    return f(*args, **kwargs)

  return decorated


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('homepage.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))


# /server.py

@app.route('/slyko/logout')
def out():
    # Clear session stored data
    session.clear()
    session['current_user'] = None
    session['logged_in'] = None
    session.pop('current_user', None)
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('signin', _external=True), 'client_id': 'xaTwJSSL6BkiDhFLFxY8okLueLSLcAqd'}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


# END OAuth ---------------------










'''
@app.route('/slyko/logout')
@login_required
def logout():
    session['current_user'] = None
    session['logged_in'] = None
    #redis.delete(session['current_user'])
    session.pop('current_user', None)
    return redirect(url_for('signin'))
'''


@app.route("/slyko/storage")
@login_required
def storage():
    redis.expire(session['current_user'], time=300)
    user_path = app.upload_path.joinpath(redis.get(session['current_user']).decode('utf-8')).resolve()
    user = redis.get(session['current_user']).decode('utf-8')

    files = []
    for filename in os.listdir(str(user_path)):
        data = []
        data.append(filename)
        data.append(str(os.stat(str(user_path) + "/" + filename).st_size) + "B")
        data.append("/slyko/dl/download/" + filename)
        data.append("/slyko/dl/delete/" + filename)
        files.append(data)

    tokens = {}
    #for f in files:

    return render_template(
        'storage.html',user=redis.get(session['current_user']).decode('utf-8'),
        files_len=len(files), files=files, tokens=tokens)


@app.route("/slyko/market", methods=['GET', 'POST'])
def market():
    user_path = UPLOAD_FOLDER

    files = []
    for directory in os.listdir(str(user_path)):
        data = []
        data.append(directory)
        for filename in os.listdir(str(user_path) + "/" + directory):
            dict = []
            dict.append(filename)
            dict.append("/slyko/static/uploads/" + directory + "/" + filename)
            data.append(dict)
        files.append(data)

    tokens = {}

    return render_template(
        'market.html', files_len=len(files), files=files,
        tokens=tokens)





def does_users_dir_exists(username):
    return os.path.isdir(UPLOAD_FOLDER+"/"+username)

def create_user_dir(username):
    os.mkdir(UPLOAD_FOLDER+"/"+username)

@app.route('/slyko/static/<path:subpath>')
def send_static(subpath):
    return app.send_static_file(subpath)



@app.route('/slyko/upload')
@login_required
def file_add():
    redis.expire(session['current_user'], time=50)
    user_path = app.upload_path.joinpath(redis.get(session['current_user']).decode()).resolve()
    files = [x.name for x in user_path.glob('**/*') if x.is_file()]
    files_len = len(files)
    token = creating_token("allow", 240).decode('utf-8')
    return render_template('upload.html', files_len=files_len, token=token)


@app.route('/slyko/uploading')
def upload_file():
    if not session.get('logged_in'):
        flash("First, you have to log in to the system")
        return redirect('/slyko/')
    return render_template('upload.html')

@app.route('/slyko/getlink')
@login_required
def getlink():
    file = request.args.get('file', None)
    print(file)
    return render_template('upload.html')






# ERRORS

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")


@app.errorhandler(405)
def method_not_found(e):
    return render_template("405.html")

@app.errorhandler(401)
def auth_not_found(e):
    return render_template("401.html")




# RUNNING MODE

if __name__ == "__main__":
    app.run(debug=True, port=5002)