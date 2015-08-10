from flask import Blueprint, request
from models import Conference, Participant
from asterisk import originate, confbridge_list_participants
from app import app

asterisk = Blueprint('asterisk', __name__)


def is_authenticated():
    return request.remote_addr == app.config['ASTERISK_IPADDR']


@asterisk.route('/invite_all/<int:conf_number>/<callerid>')
def invite_all(conf_number, callerid):
    if not is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()
    if not conf:
        return 'NOCONF'
    participant = Participant.query.filter_by(
        conference=conf, phone=callerid).first()
    if not participant or not participant.profile.admin:
        return 'NOTALLOWED'
    online_participants = [
        k['callerid'] for k in confbridge_list_participants(
            conf.number)]
    gen = (
        p for p in conf.participants if p.phone not in online_participants)
    for p in gen:
            originate(conf.number, p.phone, name=p.name,
        bridge_options=conf.conference_profile.get_confbridge_options(),
        user_options=p.profile.get_confbridge_options())
    return 'OK'


@asterisk.route('/checkconf/<conf_number>/<callerid>')
def check(conf_number, callerid):
    if not is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()

    if not conf:
        return 'NOCONF'

    elif callerid not in [
            k.phone for k in conf.participants] and not conf.is_public:
        return 'NOTPUBLIC'

    else:
        return 'OK'


@asterisk.route('/confprofile/<int:conf_number>')
def conf_profile(conf_number):
    if not is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()
    if not conf:
        return 'NOCONF'
    return ','.join(conf.conference_profile.get_confbridge_options())


@asterisk.route('/userprofile/<int:conf_number>/<callerid>')
def user_profile(conf_number, callerid):
    if not is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()
    if not conf:
        return 'NOCONF'
    participant = Participant.query.filter_by(conference=conf,
                                            phone=callerid).first()
    if participant:
        # Return participant profile
        return ','.join(participant.profile.get_confbridge_options())
    else:
        # Return public profile
        return ','.join(
            conf.public_participant_profile.get_confbridge_options())

