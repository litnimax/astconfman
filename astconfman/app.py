# -*- coding: utf-8 -*-
import json
import os
import gevent
from gevent.queue import Queue
from urllib import urlencode
from flask import Flask, send_from_directory, request, Response, session
from flask import g, redirect, url_for
from flask_admin import Admin, AdminIndexView
from flask_babelex import Babel, gettext, lazy_gettext
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from flask_sqlalchemy import SQLAlchemy, models_committed


app = Flask('AstConfMan', instance_relative_config=True)
app.config.from_object('config')


# For smooth language switcher
def append_to_query(s, param, value):
    params = dict(request.args.items())
    params[param] = value
    return '%s?%s' % (request.path, urlencode(params))
app.jinja_env.filters['append_to_query'] = append_to_query


try:
  app.config.from_pyfile('config.py')
except IOError:
  pass


db = SQLAlchemy()
db.init_app(app)

migrate = Migrate(app, db)

from flask_bootstrap import Bootstrap
Bootstrap(app)

babel = Babel(app)
@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')        
    return session.get('lang', app.config.get('LANGUAGE'))


# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.username


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


sse_subscriptions = []

class ServerSentEvent(object):
    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data : "data",
            self.event : "event",
            self.id : "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k)
                 for k, v in self.desc_map.iteritems() if k]

        return "%s\n\n" % "\n".join(lines)


@app.route("/sse_debug")
def sse_debug():
    return "Currently %d subscriptions" % len(sse_subscriptions)


def sse_notify(room, command, message=''):
    msg = {"room": room, "command": command, "message": message}
    for sub in sse_subscriptions[:]:
        sub.put(json.dumps(msg))


@app.route("/sse_publish")
def sse_publish():
    gevent.spawn(sse_notify, '1', 'unmute_request', 'max')
    return "OK"

@app.route("/sse_subscribe")
def subscribe():
    def gen():
        q = Queue()
        sse_subscriptions.append(q)
        try:
            while True:
                result = q.get()
                ev = ServerSentEvent(str(result))
                yield ev.encode()
        except GeneratorExit: # Or maybe use flask signals
            sse_subscriptions.remove(q)

    return Response(gen(), mimetype="text/event-stream")



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(
        app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon')


from views import asterisk
app.register_blueprint(asterisk, url_prefix='/asterisk')


from models import Contact, Conference, Participant, ParticipantProfile
from models import ConferenceProfile
from views import ContactAdmin, ParticipantProfileAdmin, ParticipantAdmin
from views import ConferenceProfileAdmin, ConferenceAdmin, RecordingAdmin
