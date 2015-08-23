from flask.ext.babelex import gettext
from wtforms.validators import ValidationError
from models import Participant


def is_number(form, field):
    if field.data and not field.data.isdigit():
        raise ValidationError(gettext('Must be a number!'))


def is_participant_uniq(form, field):
    p = Participant.query.filter_by(conference=form.data['conference'],
                                    phone=form.data['phone']).first()
    if p:
        raise ValidationError(
            gettext('Participant with phone number %(num)s already there.',
                    num=form.data['phone']))
