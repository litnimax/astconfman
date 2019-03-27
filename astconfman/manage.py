#!/usr/bin/env python

from flask import Flask
from flask_babelex import gettext
from flask_migrate import MigrateCommand
from flask_security import utils
from flask_script import Manager
from app import app, db, migrate, user_datastore
from models import Contact, Conference, Participant
from models import ParticipantProfile, ConferenceProfile

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def create_schema():
    db.create_all()


@manager.command
def create_admin_admin():
    user_datastore.create_role(name='admin', description='System administrator')
    user_datastore.create_role(name='user', description='Conference user')
    admin = user_datastore.create_user(username='admin',
                               password=utils.encrypt_password('admin'))
    user_datastore.add_role_to_user(admin, 'admin')
    db.session.commit()


@manager.command
def init():
    db.drop_all()
    db.create_all()

    # Create roles
    user_datastore.create_role(name='admin', description='System administrator')
    user_datastore.create_role(name='user', description='Conference user')
    admin = user_datastore.create_user(username='admin',
                               password=utils.encrypt_password('admin'))
    user = user_datastore.create_user(username='user',
                               password=utils.encrypt_password('user'))
    user_datastore.add_role_to_user(admin, 'admin')
    user_datastore.add_role_to_user(user, 'user')

    contacts = [
        ('1010', gettext('John Smith')),
        ('1020', gettext('Sam Brown')),
    ]
    for c in contacts:
        rec = Contact(phone=c[0], name=c[1], user=admin)
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
                      user=admin,
                      )
    db.session.add(conf)

    p1 = Participant(conference=conf, profile=admin_user_profile, phone='1001',
                     user=admin)
    p2 = Participant(conference=conf, profile=guest_user_profile, phone='1002',
                     user=admin)
    p3 = Participant(conference=conf, profile=marked_user_profile, phone='1003',
                     user=admin)
    db.session.add(p1)
    db.session.add(p2)
    db.session.add(p3)

    db.session.commit()


@manager.command
def start_conf(conf_num):
    conf = Conference.query.filter_by(number=conf_num).first()
    if conf:
        conf.invite_participants()


if __name__ == '__main__':
    manager.run()
