from flask_babelex import gettext
from wtforms.validators import ValidationError
from crontab import CronTab, CronItem
from models import Participant



def is_number(form, field):
    if field.data and not field.data.isdigit():
        raise ValidationError(gettext('Must be a number!'))


def is_participant_uniq(form, field):
    #
    p = Participant.query.filter_by(conference=form.data['conference'],
                                    phone=form.data['phone']).first()
    if p:
        raise ValidationError(
            gettext('Participant with phone number %(num)s already there.',
                    num=form.data['phone']))



def is_crontab_valid(form, field):
    item = CronItem(field.data + ' /bin/echo # Just a test', cron=CronTab())
    # May be I will refactor to this:
    #item = cron.new(command='/bin/echo', comment='Aaaaa')
    #item.hour.every(4)
    #item.minute.during(5,50).every(2)
    #item.day.on(4,5,6)
    #item.dow.on(1)
    #item.month.during(1,2)
    if not item.is_valid():
        raise ValidationError(gettext('%(job)s is not a correct crontab entry.',
                              job=field.data))

