import datetime
import json
import os
from pathlib import Path

import jwt
import redis as redis
import requests
import verify as verify
from flask import Flask, session, request, send_from_directory, render_template, abort, flash, url_for
from werkzeug.utils import secure_filename, redirect

import content_management
from app import login_required


### ABOUT CONTENT ###
import publisher

app = Flask(__name__)
app.secret_key = b'35dvgy8i(UHoiawu hftvd9'
app.jwt_secret_key = 'DjOskarroInDaMix'
app.client_server = "http://127.0.0.1:5002/slyko/"

# content of main site
TOPIC_DICT = content_management.Content()

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.upload_path = Path(os.path.join(APP_ROOT, 'static/uploads'))

app.config.update(
    #SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# path to the app directory
cwd = os.path.dirname(os.path.realpath(__file__))

redis = redis.Redis()


app.queue = publisher.Publisher("localhost","slyko-exchange","resize")


def sendMessage(msg):
    payload = {"openpath": msg['openpath'],
               "savepath": msg['savepath'],
               "exp": (datetime.datetime.utcnow() + datetime.timedelta(days=1))}
    send = jwt.encode(payload, app.jwt_secret_key, algorithm='HS256')
    app.queue.publish(send)
    return

def checkFormat(filepath):
    tmp = filepath.split(".")[-1]
    return tmp in ["png","jpg","jpeg"]



@app.route("/slyko/dl/upload", methods=['POST', 'GET'])
@login_required
def upload():
    token = request.form['token']
    try:
        user = jwt.decode(token.encode(), app.jwt_secret_key, algorithm='HS256')
    except jwt.ExpiredSignatureError:
        return abort(401)
    user_path = app.upload_path.joinpath(user['user']).resolve()
    files = [x.name for x in user_path.glob('**/*') if x.is_file()]
    files_len = len(files)
    if files_len >= 5:
        flash("You cannot upload more than 5 files into a server")
        return redirect('http://127.0.0.1:5002/slyko/upload')
    if 'file' not in request.files:
        flash("You have to choose the file")
        return redirect('http://127.0.0.1:5002/slyko/upload')
    f = request.files['file']
    filename = secure_filename(f.filename)
    user_path.mkdir(parents=True, exist_ok=True)
    q = user_path / filename

    print(checkFormat(str(q)))
    f.save(str(q))
    if checkFormat(str(q)):
        sendMessage(
            {'openpath': str(q),
             'savepath': str(Path("./static", "miniatures", user['user']))})
        requests.post(app.client_server + "post?user=" + user['user'], verify=False)
    flash("Your file has been added")
    return redirect('http://127.0.0.1:5002/slyko/storage')




@app.route("/slyko/dl/download/<string:token>")
@login_required
def download(token):
    try:
        user=jwt.decode(token.encode(), app.jwt_secret_key, algorithm='HS256')
    except jwt.ExpiredSignatureError:
        return os.abort(401)
    user_path = app.upload_path.joinpath(user['user']).resolve()
    q = user_path / user['file']
    if q.exists():
        return send_from_directory(user_path, user['file'])
    else:
        os.abort(404)



# DELETING

@app.route("/slyko/dl/delete/<string:token>")
@login_required
def delete(token):
    try:
        user=jwt.decode(token.encode(), app.jwt_secret_key, algorithm='HS256')
    except jwt.ExpiredSignatureError:
        return os.abort(401)
    user_path = app.upload_path.joinpath(user['user']).resolve()
    q = user_path / user['file']
    print('ochoelra')
    if q.exists():
        os.remove(q)
        return redirect(url_for('storage'))
    else:
        os.abort(404)


@app.route('/slyko/static/<path:subpath>')
def send_static(subpath):
    return app.send_static_file(subpath)

@app.route("/slyko/dl/list/<string:user>")
def list(user):
    user_path = app.upload_path.joinpath(user).resolve()
    files = [x.name for x in user_path.glob('**/*') if x.is_file()]
    js = json.dumps({"list":files})
    return js

@app.route("/slyko/dl/miniatures/<string:user>")
def miniatures(user):
    user_path = Path("./static", "miniatures", user).resolve()
    files = [x.name for x in user_path.glob('**/*') if x.is_file()]
    js = json.dumps({"list":files})
    return js

# RUNNING MODE

if __name__ == "__main__":
    app.run(debug=True, port=5003)




