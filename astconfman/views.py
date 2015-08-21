import json
import time
from flask import request, render_template, Response, redirect, url_for
from flask import Blueprint, flash, abort, jsonify
from flask.ext.admin import  Admin, AdminIndexView, BaseView, expose
from flask.ext.admin.actions import action
from flask.ext.admin.contrib.sqla import ModelView, filters
from flask.ext.admin.contrib.fileadmin import FileAdmin
from flask.ext.admin.form import rules
from flask.ext.babelex import lazy_gettext as _, gettext
from jinja2 import Markup
from wtforms.validators import Required, ValidationError
from models import Contact, Conference, ConferenceLog, Participant
from models import ConferenceProfile, ParticipantProfile
from app import app, db, socketio
from forms import ContactImportForm, ConferenceForm
from asterisk import *


def check_auth(username, password):
    if username in app.config['ADMINS'].keys() and \
            app.config['ADMINS'][username]['password'] == password:
        return True
    else:
        return False


def authenticate():
    return Response(
            _(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials'
            ),
            401,
            {
                'WWW-Authenticate': u'Basic realm="Login Required"'
            }
        )


def is_authenticated():
    auth = request.authorization
    return auth and check_auth(auth.username, auth.password)


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


class AuthBaseView(BaseView):
    def is_accessible(self):
        return is_authenticated()

    def _handle_view(self, name, *args, **kwargs):
        if not self.is_accessible():
            return authenticate()


def legend_formatter(view, context, model, name):
        """Formatter for legend columns for profiles"""
        glyph = '<span title="%s" class="glyphicon glyphicon-%s"></span> '
        legend = ''
        if isinstance(model, ParticipantProfile):
            if model.admin:
                legend += (glyph % (gettext('Admin'), 'text-color'))
            if model.marked:
                legend += (glyph % (gettext('Marked'), 'king'))
            if model.pin:
                legend += (glyph % (gettext('PIN is set'), 'lock'))
            if model.startmuted:
                legend += (glyph % (gettext('PIN is set'), 'volume-off'))
            if model.wait_marked:
                legend += (glyph % (gettext('Wait for marked user to join'),
                                    '       glyphicon-log-in'))
            if model.end_marked:
                legend += (glyph % (gettext('End when marked user leaves'),
                                    '       glyphicon-log-out'))

        elif isinstance(model, Conference):
            if model.is_public:
                legend += (glyph % (gettext('Guests (not from participant '
                                            'list) can join'), 'plus-sign'))
            else:
                legend += (glyph % (gettext('Only for participants '
                                            'specified'), 'ban-circle'))
        return Markup(legend)



class ContactAdmin(ModelView, AuthBaseView):
    column_list = ['phone', 'name']
    form_columns = ['phone', 'name']
    create_template = 'contact_create.html'
    column_searchable_list = ['phone', 'name']
    form_args = {
        'phone': dict(validators=[Required(), is_number])
    }
    column_labels = {
        'phone': _('Phone'),
        'name': _('Name'),
    }

    @action('conference', _('Add to Conference'))
    def action_conference(self, ids):
        return render_template('action_conference.html', ids=ids,
                               conferences=Conference.query.all(),
                               profiles=ParticipantProfile.query.all())

    @expose('/import', methods=['POST', 'GET'])
    def import_contacts(self):
        form = ContactImportForm()
        if request.method == 'GET':
            return self.render('contact_import.html', form=form)

        else:
            form = ContactImportForm()
            if form.validate_on_submit():
                data = form.filename.data.readlines()
                imported = 0
                for line in data:
                    line = line.split(',')
                    c = Contact()
                    c.phone = line[0]
                    c.name = line[1].decode('utf-8')
                    db.session.add(c)
                    imported += 1
                db.session.commit()
                flash(gettext('Imported %(num)s contacts.', num=imported))
                return redirect(url_for('.index_view'))

            else:
                return self.render('contact_import.html', form=form)




class ParticipantAdmin(ModelView, AuthBaseView):
    column_searchable_list = ('phone', 'name')
    column_filters = ['conference', 'profile']
    column_formatters = {
        'legend': lambda v,c,m,n: legend_formatter(v,c,m,n)
    }
    column_list = ['phone', 'name', 'is_invited', 'conference', 'profile']
    form_args = {
        'phone': dict(validators=[Required(), is_number, is_participant_uniq]),
        'conference': dict(validators=[Required()]),
        'profile': dict(validators=[Required()]),
    }
    column_labels = {
        'phone': _('Phone'),
        'name': _('Name'),
        'conference': _('Conference'),
        'profile': _('Participant Profile'),
        'is_invited': _('Is invited on Invite All?')
    }
    column_descriptions = {
        'is_invited': _('When enabled this participant will be called on <i>Invite All</i> from <i>Manage Conference</i> menu.'),
    }


class ConferenceAdmin(ModelView, AuthBaseView):
    """
    This is active conference started in a room.
    """
    form_base_class = ConferenceForm
    can_view_details = True
    details_template = 'conference_details.html'
    edit_template = 'conference_edit.html'
    create_template = 'conference_create.html'

    column_list = ['number', 'name', 'is_public', 'is_locked',
                   'participant_count', 'invited_participant_count',
                   'online_participant_count']
    inline_models = (Participant,)
    column_labels = {
        'number': _('Conference Number'),
        'name': _('Conference Name'),
        'participant_count': _('Participants'),
        'invited_participant_count': _('Invited Participants'),
        'online_participant_count': _('Participants Online'),
        'is_locked': _('Locked'),
        'is_public': _('Public'),
        'conference_profile': _('Conference Profile'),
        'public_participant_profile': _('Public Participant Profile'),
        'participants': _('Participants'),
    }

    form_create_rules = form_edit_rules = [
        rules.FieldSet(
            ('number', 'name', 'conference_profile'),
            _('Basic Settings')
        ),
        rules.FieldSet(
            ('is_public', 'public_participant_profile'),
            _('Open Access')
        ),
        rules.FieldSet(
            (rules.Macro('conference_participants_link'), 'participants'),             
            _('Participants')
        ),
    ]

    column_formatters = {
        'legend': lambda v,c,m,n: legend_formatter(v,c,m,n),
    }

    form_args = {
        'number': dict(validators=[Required(), is_number]),
        'name': dict(validators=[Required()]),
        'conference_profile': dict(validators=[Required()]),
        'public_participant_profile': dict(validators=[Required()]),
    }


    @expose('/details/')
    def details_view(self):
        conf = Conference.query.get_or_404(request.args.get('id', 0))
        self._template_args['confbridge_participants'] = \
            confbridge_list_participants(conf.number)
        self._template_args['confbridge'] = confbridge_get(conf.number)
        return super(ConferenceAdmin, self).details_view()


    @expose('/contacts/', methods=['POST'])
    def add_contacts(self):
        if request.method == 'POST':
            if not request.form.get('conference') or not request.form.get(
                'profile'):
                    flash(
                        _('You must select Conference and Profile'))
                    return redirect(url_for('contact.index_view'))

            conference = Conference.query.filter_by(
                id=request.form['conference']).first_or_404()
            
            profile = ParticipantProfile.query.filter_by(
                id=request.form['profile']).first_or_404()

            contacts = Contact.query.filter(
                    Contact.id.in_(request.form['ids'].split(',')))
            
            for c in contacts:
                if Participant.query.filter_by(phone=c.phone,
                                               conference=conference).first():
                    flash(gettext(
                        '%(contact)s is already there.', contact=c))
                    continue
                p = Participant(phone=c.phone, name=c.name,
                                profile=profile, conference=conference)
                flash(gettext(
                    '%(contact)s added.', contact=c))

                db.session.add(p)
            db.session.commit()
                    
        return redirect(url_for('.edit_view', id=conference.id))


    @expose('/<int:conf_id>/invite_guest')
    def invite_guest(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        phone = request.args.get('phone', None)
        if phone and phone.isdigit():
            originate(conf.number, phone,
                bridge_options=conf.conference_profile.get_confbridge_options(),
                user_options=conf.public_participant_profile.get_confbridge_options())
            flash(gettext('Number %(phone)s is called for conference.',
                          phone=phone))
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/invite_participants')
    def invite_participants(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        online_participants = [
            k['callerid'] for k in confbridge_list_participants(conf.number)]
        gen = (p for p in conf.participants if p.is_invited and p.phone not in online_participants)
        for p in gen:
                originate(conf.number, p.phone, name=p.name,
            bridge_options=conf.conference_profile.get_confbridge_options(),
            user_options=p.profile.get_confbridge_options()
            )

        flash(gettext(
                'All the participants where invited to the conference'))
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf.id))



    @expose('/kick/<conf_id>')
    @expose('/kick/<conf_id>/channel/<path:channel>')
    def kick(self, conf_id, channel=None):
        conf = Conference.query.filter_by(id=conf_id).first_or_404()
        if channel:
            confbridge_kick(conf.number, channel)
            msg = gettext('Channel %(channel)s is kicked.', channel=channel)
            flash(msg)
            conf.log(msg)
        else:
            confbridge_kick_all(conf.number)
            msg = gettext('All participants have been kicked from the conference.')
            conf.log(msg)
            flash(msg)
        socketio.emit('update_participants', {
            'room': 'conference-%s' % conf.id
        })
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf.id))


    @expose('/mute/<conf_id>')
    @expose('/mute/<conf_id>/channel/<path:channel>')
    def mute(self, conf_id, channel=None):
        conf = Conference.query.get_or_404(conf_id)
        if channel:
            confbridge_mute(conf.number, channel)
            msg = gettext('Participant %(channel)s muted.', channel=channel)
            flash(msg)
            conf.log(msg)
        else:
            # Mute all
            for p in confbridge_list_participants(conf.number):
                confbridge_mute(conf.number, p['channel'])
            msg = gettext('Conference muted.')
            flash(msg)
            conf.log(msg)
        socketio.emit('update_participants', {
            'room': 'conference-%s' % conf.id
        })
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/unmute/<conf_id>')
    @expose('/unmute/<conf_id>/channel/<path:channel>')
    def unmute(self, conf_id, channel=None):
        conf = Conference.query.get_or_404(conf_id)
        if channel:
            confbridge_unmute(conf.number, channel)
            msg = gettext('Participant %(channel)s unmuted.', channel=channel)
            flash(msg)
            conf.log(msg)
        else:
            # Mute all
            for p in confbridge_list_participants(conf.number):
                confbridge_unmute(conf.number, p['channel'])
            msg = gettext('Conference unmuted.')
            flash(msg)
            conf.log(msg)
        socketio.emit('update_participants', {
            'room': 'conference-%s' % conf.id
        })
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/record_start')
    def record_start(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        confbridge_record_start(conf.number)
        msg = gettext('The conference recording has been started.')
        flash(msg)
        conf.log(msg)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/record_stop')
    def record_stop(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        confbridge_record_stop(conf.number)
        msg = gettext('The conference recording has been stopped.')
        flash(msg)
        conf.log(msg)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/lock')
    def lock(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        confbridge_lock(conf.number)
        msg = gettext('The conference has been locked.')
        flash(msg)
        conf.log(msg)
        socketio.emit('update_participants', {
            'room': 'conference-%s' % conf.id
        })
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/unlock')
    def unlock(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        confbridge_unlock(conf.number)
        msg = gettext('The conference has been unlocked.')
        flash(msg)
        conf.log(msg)
        socketio.emit('update_participants', {
            'room': 'conference-%s' % conf.id
        })
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/clear_log')
    def clear_log(self, conf_id):
        logs = ConferenceLog.query.filter_by(conference_id=conf_id)
        for log in logs:
            db.session.delete(log)
        db.session.commit()
        return redirect(url_for('.details_view', id=conf_id))


class RecordingAdmin(FileAdmin, AuthBaseView):
    can_upload = False
    can_download = True
    can_delete = True
    can_mkdir = False
    can_rename = True
    can_mkdir = False


class ConferenceProfileAdmin(ModelView, AuthBaseView):
    column_list = [
        'name', 'max_members', 'record_conference',
        'internal_sample_rate', 'mixing_interval', 'video_mode'
    ]
    column_labels = {
        'name': _('Profile Name'),
    }
    column_descriptions = {
        'max_members': _("""Limits the number of participants for a single conference to a specific number. By default, conferences have no participant limit. After the limit is reached, the conference will be locked until someone leaves. Admin-level users are exempt from this limit and will still be able to join otherwise-locked, because of limit, conferences."""),
        'record_conference': _("""Records the conference call starting when the first user enters the room, and ending when the last user exits the room. The default recorded filename is 'confbridge-<name of conference bridge>-<start time>.wav' and the default format is 8kHz signed linear. By default, this option is disabled. This file will be located in the configured monitoring directory as set in conf"""),
        'internal_sample_rate': _("""Sets the internal native sample rate at which to mix the conference. The "auto" option allows Asterisk to adjust the sample rate to the best quality / performance based on the participant makeup. Numbered values lock the rate to the specified numerical rate. If a defined number does not match an internal sampling rate supported by Asterisk, the nearest sampling rate will be used instead."""),
        'mixing_interval': _("""Sets, in milliseconds, the internal mixing interval. By default, the mixing interval of a bridge is 20ms. This setting reflects how "tight" or "loose" the mixing will be for the conference. Lower intervals provide a "tighter" sound with less delay in the bridge and consume more system resources. Higher intervals provide a "looser" sound with more delay in the bridge and consume less resources"""),
        'video_mode': _("""Configured video (as opposed to audio) distribution method for conference participants. Participants must use the same video codec. Confbridge does not provide MCU functionality. It does not transcode, scale, transrate, or otherwise manipulate the video. Options are "none," where no video source is set by default and a video source may be later set via AMI or DTMF actions; "follow_talker," where video distrubtion follows whomever is talking and providing video; "last_marked," where the last marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user previous to the last-joined will be used as the video source; and "first-marked," where the first marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user that joined next will be used as the video source. Use of video in conjunction with the jitterbuffer results in the audio being slightly out of sync with the video - because the jitterbuffer only operates on the audio stream, not the video stream. Jitterbuffer should be disabled when video is used.""")
    }
    form_choices = {
        'internal_sample_rate': [('auto','auto'), ('8000', '8000'),
                                ('12000', '12000'), ('16000', '16000'),
                                ('24000', '24000'), ('32000', '32000'),
                                ('44100', '44100'), ('48000', '48000'),
                                ('96000', '96000'), ('192000', '192000')],
        'mixing_interval': [('10', '10'), ('20', '20'), ('40', '40'), ('80','80')],
        'video_mode': [('none', 'none'), ('follow_talker', 'follow_talker'),
                        ('last_marked', 'last_marked'),
                        ('first_marked', 'first_marked')],
    }
    can_view_details = True
    form_args = {
        'name': {'validators': [Required()]},
        'mixing_interval': {'validators': [Required()]},
    }


class ParticipantProfileAdmin(ModelView, AuthBaseView):
    """Class that repesents confbridge user profiles"""
    column_list = ['name', 'legend']
    column_formatters = {
        'legend': lambda v,c,m,n: legend_formatter(v,c,m,n),
    }
    can_view_details = True
    form_args = {
        'name': {'validators': [Required()]},
        'music_on_hold_class': {'validators': [Required()]}
    }
    form_create_rules = form_edit_rules = [
        'name',
        rules.FieldSet(
            (
                'admin',
                'marked',
                'pin',
                'startmuted',
                'quiet',
                'wait_marked',
                'end_marked',            
                'music_on_hold_when_empty',
                'music_on_hold_class',
            ),
            _('Basic')),
        rules.FieldSet(
            (
                'announce_user_count',
                'announce_user_count_all',
                'announce_only_user',
                'announcement',
                'announce_join_leave',
                ),
            _('Announcements')
            ),
        rules.FieldSet(
            (
                'dsp_drop_silence',
                'dsp_talking_threshold',
                'dsp_silence_threshold',
                'talk_detection_events',
                'denoise',
                'jitterbuffer',
                'dtmf_passthrough',
                ),
            _('Voice Processing')
            )
    ]
    column_labels = {
        'name': _('Profile Name'),
        'legend': _('Legend'),
    }
    """ # I'don want to tranlate asterisk profile setting names
        'admin': _('Admin'),
        'marked': _('Marked'),
        'pin': _('PIN'),
        'startmuted': _('Start Muted'),
        'quiet': _('Quiet'),
        'wait_marked': _('Wait Marked'),
        'end_marked': _('End Marked'),
        'music_on_hold_when_empty': _('Music On Hold When Empty'),
        'music_on_hold_class': _(''),
    """
    column_descriptions = {
        'admin': _('Sets if the user is an Admin or not. By default, no.'),
        'marked': _('Sets if the user is Marked or not. By default, no.'),
        'startmuted': _('Sets if the user should start out muted. By default, no.'),
        'pin': _('Sets if the user must enter a PIN before joining the conference. The user will be prompted for the PIN.'),
        'startmuted': _('Sets if the user should start out muted. By default, no.'),
        'quiet': _('When set, enter/leave prompts and user introductions are not played. By default, no.'),
        'wait_marked': _('Sets if the user must wait for another marked user to enter before joining the conference. By default, no.'),
        'end_marked': _('If enabled, every user with this option in their profile will be removed from the conference when the last marked user exists the conference.'),
        'dtmf_passthrough': _('Whether or not DTMF received from users should pass through the conference to other users. By default, no.'),
        'music_on_hold_when_empty': _('Sets whether music on hold should be played when only one person is in the conference or when the user is waiting on a marked user to enter the conference. By default, off.'),
        'music_on_hold_class': _('Sets the music on hold class to use for music on hold.'),
        'announce_user_count': _('Sets if the number of users in the conference should be announced to the caller. By default, no.'),
        'announce_user_count_all': _('Choices: yes, no, integer. Sets if the number of users should be announced to all other users in the conference when someone joins. When set to a number, the announcement will only occur once the user count is above the specified number'),
        'announce_only_user': _('Sets if the only user announcement should be played when someone enters an empty conference. By default, yes.'),
        'announcement': _('If set, the sound file specified by filename will be played to the user, and only the user, upon joining the conference bridge.'),
        'announce_join_leave': _('When enabled, this option prompts the user for their name when entering the conference. After the name is recorded, it will be played as the user enters and exists the conference. By default, no.'),
        'dsp_drop_silence': _('Drops what Asterisk detects as silence from entering into the bridge. Enabling this option will drastically improve performance and help remove the buildup of background noise from the conference. This option is highly recommended for large conferences, due to its performance improvements.'),
        'dsp_talking_threshold': _("""The time, in milliseconds, by default 160, of sound above what the DSP has established as base-line silence for a user, before that user is considered to be talking. This value affects several options:
Audio is only mixed out of a user's incoming audio stream if talking is detected. If this value is set too loose, the user will hear themselves briefly each time they begin talking until the DSP has time to establish that they are in fact talking.
When talker detection AMI events are enabled, this value determines when talking has begun, which causes AMI events to fire. If this value is set too tight, AMI events may be falsely triggered by variants in the background noise of the caller.
The drop_silence option depends on this value to determine when the user's audio should be mixed into the bridge after periods of silence. If this value is too loose, the beginning of a user's speech will get cut off as they transition from silence to talking."""),
        'dsp_silence_threshold': _("""The time, in milliseconds, by default 2500, of sound falling within what the DSP has established as the baseline silence, before a user is considered to be silent. The best way to approach this option is to set it slightly above the maximum amount of milliseconds of silence a user may generate during natural speech. This value affects several operations:
When talker detection AMI events are enabled, this value determines when the user has stopped talking after a period of talking. If this value is set too low, AMI events indicating that the user has stopped talking may get faslely sent out when the user briefly pauses during mid sentence.
The drop_silence option depends on this value to determine when the user's audio should begin to be dropped from the bridge, after the user stops talking. If this value is set too low, the user's audio stream may sound choppy to other participants."""),
        'talk_detection_events': _('Sets whether or not notifications of when a user begins and ends talking should be sent out as events over AMI. By default, no.'),
        'denoise': _('Whether or not a noise reduction filter should be applied to the audio before mixing. By default, off. This requires codec_speex to be built and installed. Do not confuse this option with drop_silence. denoise is useful if there is a lot of background noise for a user, as it attempts to remove the noise while still preserving the speech. This option does not remove silence from being mixed into the conference and does come at the cost of a slight performance hit.'),
        'jitterbuffer': _("Whether or not to place a jitter buffer on the caller's audio stream before any audio mixing is performed. This option is highly recommended, but will add a slight delay to the audio and will incur a slight performance penalty. This option makes use of the JITTERBUFFER dialplan function's default adaptive jitter buffer. For a more fine-tuned jitter buffer, disable this option and use the JITTERBUFFER dialplan function on the calling channel, before it enters the ConfBridge application."),

    }


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return is_authenticated()

    def _handle_view(self, name, *args, **kwargs):
        if not self.is_accessible():
            return authenticate()


admin = Admin(
    app,
    name='Asterisk Conference Manager',
    index_view=MyAdminIndexView(        
        template='admin/index.html',
        url='/'
    ),
    base_template='my_master.html',
    template_mode='bootstrap3',
    category_icon_classes={
        'Profiles': 'glyphicon glyphicon-wrench',
    }
)


admin.add_view(ConferenceAdmin(
    Conference,
    db.session,
    name=_('Conferences'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-bullhorn'
    )
)


admin.add_view(ParticipantAdmin(
    Participant,
    db.session,
    name=_('Participants'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-user'
    )
)

admin.add_view(ContactAdmin(
    Contact,
    db.session,
    name=_('Contacts'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-book'
    )
)

admin.add_view(RecordingAdmin(
    app.config['ASTERISK_MONITOR_DIR'],
    '/static/recording/',
    endpoint='recording',
    name=_('Recordings'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-hdd'
    )
)

admin.add_view(ParticipantProfileAdmin(
    ParticipantProfile,
    db.session,
    category=_('Profiles'),
    endpoint='participant_profile',
    url='/profile/participant/',
    name=_('Participant'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-user'
    )
)

admin.add_view(ConferenceProfileAdmin(
    ConferenceProfile,
    db.session,
    category=_('Profiles'),
    endpoint='room_profile',
    url='/profile/room/',
    name=_('Conference'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-bullhorn',
    )
)

### ASTERISK VIEWS
asterisk = Blueprint('asterisk', __name__)

def asterisk_is_authenticated():
    return request.remote_addr == app.config['ASTERISK_IPADDR']


@asterisk.route('/invite_all/<int:conf_number>/<callerid>')
def invite_all(conf_number, callerid):
    if not asterisk_is_authenticated():
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
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()

    if not conf:
        return 'NOCONF'

    elif callerid not in [
            k.phone for k in conf.participants] and not conf.is_public:
        message = gettext('Attempt to enter non-public conference from %(phone)s.',
                    phone=callerid)
        conf.log(message)
        return 'NOTPUBLIC'

    else:
        return 'OK'


@asterisk.route('/confprofile/<int:conf_number>')
def conf_profile(conf_number):
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    conf = Conference.query.filter_by(number=conf_number).first()
    if not conf:
        return 'NOCONF'
    return ','.join(conf.conference_profile.get_confbridge_options())


@asterisk.route('/userprofile/<int:conf_number>/<callerid>')
def user_profile(conf_number, callerid):
    if not asterisk_is_authenticated():
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


@asterisk.route('/dial_status/<int:conf_number>/<callerid>/<status>')
def dial_status(conf_number, callerid, status):
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    message = gettext('Could not invite number %(num)s: %(status)s', num=callerid,
                status=status.capitalize())
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    conference.log(message)
    return 'OK'


@asterisk.route('/enter_conference/<int:conf_number>/<callerid>')
def enter_conference(conf_number, callerid):
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    message = gettext('Number %(num)s has entered the conference.', num=callerid)
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    conference.log(message)
    socketio.emit('update_participants', {
        'room': 'conference-%s' % conference.id
    })
    return 'OK'

@asterisk.route('/leave_conference/<int:conf_number>/<callerid>')
def leave_conference(conf_number, callerid):
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    message = gettext('Number %(num)s has left the conference.', num=callerid)
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    conference.log(message)
    socketio.emit('update_participants', {
        'room': 'conference-%s' % conference.id
    })
    return 'OK'


@asterisk.route('/unmute_request/<int:conf_number>/<callerid>')
def unmute_request(conf_number, callerid):
    if not asterisk_is_authenticated():
        return 'NOTAUTH'
    message = gettext('Unmute request from number %(num)s.', num=callerid)
    conference = Conference.query.filter_by(number=conf_number).first_or_404()
    conference.log(message)
    socketio.emit('unmute_request', {
        'data': callerid,
        'room': 'conference-%s' % conference.id
    })
    return 'OK'


@asterisk.route('/online_participants.json/<int:conf_number>')
def online_participants_json(conf_number):
    # This is public view called from WEB clients
    ret = confbridge_list_participants(conf_number)
    return Response(response=json.dumps(ret),
                    status=200, mimetype='application/json')
