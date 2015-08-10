from flask import Blueprint, render_template
from flask import request, session
from flask.ext.socketio import SocketIO, emit, join_room, leave_room, \
    close_room, disconnect
from app import db, socketio
from models import ConferenceLog, Conference

mod = Blueprint('socketio', __name__)


@socketio.on('join')
def join(message):
    join_room(message['room'])


@mod.route('/dial_status/<int:conf_number>/<callerid>/<status>')
def dial_status(conf_number, callerid, status):
    message = 'Could not invite number %s: %s' % (callerid, status.capitalize())
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    log = ConferenceLog(conference_id=conference.id, message=message)
    db.session.add(log)
    db.session.commit()
    socketio.emit('log_message', {'data': message},
                  room='conference-%s' % conference.id)
    return 'OK'


@mod.route('/enter_conference/<int:conf_number>/<callerid>')
def enter_conference(conf_number, callerid):
    message = 'Number %s has entered the conference.' % callerid
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    log = ConferenceLog(conference_id=conference.id, message=message)
    db.session.add(log)
    db.session.commit()
    socketio.emit('log_message', {'data': message},
                  room='conference-%s' % conference.id)
    return 'OK'

@mod.route('/leave_conference/<int:conf_number>/<callerid>')
def leave_conference(conf_number, callerid):
    message = 'Number %s has left the conference.' % callerid
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    log = ConferenceLog(conference_id=conference.id, message=message)
    db.session.add(log)
    db.session.commit()
    socketio.emit('log_message', {'data': message},
                  room='conference-%s' % conference.id)
    return 'OK'


@mod.route('/unmute_request/<int:conf_number>/<callerid>')
def unmute_request(conf_number, callerid):
    message = 'Unmute request from number %s.' % callerid
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    log = ConferenceLog(conference_id=conference.id, message=message)
    db.session.add(log)
    db.session.commit()
    socketio.emit('log_message', {'data': message},
                  room='conference-%s' % conference.id)
    socketio.emit('unmute_request', {'data': callerid},
                  room='conference-%s' % conference.id)
    return 'OK'


