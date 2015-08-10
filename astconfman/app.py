# -*- coding: utf-8 -*-

import os
from flask import Flask, send_from_directory, request, Response, session
from flask import redirect, url_for
from flask.ext.babelex import Babel, gettext, lazy_gettext
from flask.ext.socketio import SocketIO, emit
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.admin import Admin, AdminIndexView
from gevent import monkey
monkey.patch_all()


app = Flask('ConfMan', instance_relative_config=True)
app.config.from_object('config')

try:
  app.config.from_pyfile('config.py')
except IOError:
  pass

db = SQLAlchemy()
#db.app = app
db.init_app(app)

from models import Contact, Conference, Participant, ParticipantProfile, ConferenceProfile
from views import ContactAdmin, ConferenceAdmin, ParticipantAdmin, RecordingAdmin
from views import ParticipantProfileAdmin, ConferenceProfileAdmin

socketio = SocketIO(app)

babel = Babel(app)

import logging
# Enable SMTP errors
if not app.debug and app.config['SMTP_LOG_ENABLED']:
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler((app.config['SMTP_HOST'], app.config['SMTP_PORT']),
                               app.config['SMTP_FROM'],
                               [v['email'] for k,v in app.config['ADMINS'].items()],
                               'ConfMain Error')
    mail_handler.setFormatter(logging.Formatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    '''))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

if app.config['LOG_ENABLED']:
    file_handler = logging.FileHandler(app.config['LOG_FILE'])
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)


@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')        
    return session.get('lang', app.config.get('LANGUAGE'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


from views_socketio import mod  as views_socketio
app.register_blueprint(views_socketio, url_prefix='/socket')

from views_asterisk import asterisk
app.register_blueprint(asterisk, url_prefix='/asterisk')
