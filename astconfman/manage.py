#!/usr/bin/env python

from flask import Flask
from flask.ext.script import Manager
from flask.ext.babelex import gettext
from app import app, db
from models import Contact, Conference, Participant
from models import ParticipantProfile, ConferenceProfile


manager = Manager(app)


@manager.command
def init():
    db.drop_all()
    db.create_all()

    contacts = [
        ('1010', gettext('John Smith')),
        ('1020', gettext('Sam Brown')),
    ]
    for c in contacts:
        rec = Contact(phone=c[0], name=c[1])
        db.session.add(rec)

    guest_user_profile = ParticipantProfile(name=gettext('Guest'), startmuted=True)
    db.session.add(guest_user_profile)
    marked_user_profile = ParticipantProfile(name=gettext('Marker'),marked=True)
    db.session.add(marked_user_profile)
    admin_user_profile = ParticipantProfile(name=gettext('Administrator'), admin=True)
    db.session.add(admin_user_profile)

    conf_profile = ConferenceProfile(name=gettext('Default'))
    db.session.add(conf_profile)

    conf = Conference(number=100,
                      name=gettext('Test Conference'),
                      conference_profile=conf_profile,
                      public_participant_profile=guest_user_profile,
                      is_public=True,
                      )
    db.session.add(conf)

    p1 = Participant(conference=conf, profile=admin_user_profile, phone='1001')
    p2 = Participant(conference=conf, profile=guest_user_profile, phone='1002')
    p3 = Participant(conference=conf, profile=marked_user_profile, phone='1003')
    db.session.add(p1)
    db.session.add(p2)
    db.session.add(p3)

    db.session.commit()


if __name__ == '__main__':
    manager.run()
