# -*- coding: utf-8 -*-

import os
from urllib import urlencode
from flask import Flask, send_from_directory, request, Response, session
from flask import g, redirect, url_for
from flask.ext.babelex import Babel, gettext, lazy_gettext
from flask.ext.socketio import SocketIO, emit, join_room
from flask.ext.sqlalchemy import SQLAlchemy, models_committed
from flask.ext.admin import Admin, AdminIndexView
from flask.ext.migrate import Migrate


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


socketio = SocketIO(app, logger=False, engineio_logger=False)
@socketio.on('join')
def on_join(data):
    join_room(data['room'])


migrate = Migrate(app, db)


babel = Babel(app)
@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')        
    return session.get('lang', app.config.get('LANGUAGE'))


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
