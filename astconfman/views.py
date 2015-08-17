import time
from flask import request, render_template, Response, redirect, url_for
from flask import Blueprint, flash, abort
from flask.ext.admin import  Admin, AdminIndexView, BaseView, expose
from flask.ext.admin.actions import action
from flask.ext.admin.contrib.sqla import ModelView, filters
from flask.ext.admin.contrib.fileadmin import FileAdmin
from flask.ext.admin.form import rules
from flask.ext.babelex import gettext, lazy_gettext
from flask.ext.httpauth import HTTPDigestAuth
from jinja2 import Markup
from wtforms.validators import Required, ValidationError
from models import Contact, Conference, ConferenceLog, Participant
from models import ConferenceProfile, ParticipantProfile
from app import  app, db
from forms import ContactImportForm
import asterisk


# Authentication
auth = HTTPDigestAuth()

def check_auth(username, password):
    if username in app.config['ADMINS'].keys() and \
            app.config['ADMINS'][username]['password'] == password:
        return True
    else:
        return False


def authenticate():
    return Response(
            gettext(
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
            raise ValidationError(lazy_gettext('Must be a number!'))


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

    @action('conference', gettext('Add to Conference'))
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
    column_list = ['phone', 'name', 'conference', 'profile']
    form_args = {
        'phone': dict(validators=[Required(),is_number]),
        'conference': dict(validators=[Required()]),
        'profile': dict(validators=[Required()]),
    }
    column_labels = {
        'phone': lazy_gettext('Phone'),
        'name': lazy_gettext('Name'),
    }


class ConferenceAdmin(ModelView, AuthBaseView):
    """
    This is active conference started in a room.
    """
    #list_template = 'conference_list.html'
    details_template = 'conference_details.html'
    can_view_details = True

    column_list = ['number', 'name', 'is_public', 'is_locked',
                   'participant_count', 'online_participant_count']
    column_filters = ['is_public']
    column_labels = {
        'number': lazy_gettext('Number'),
        'name': lazy_gettext('Name'),
        'participant_count': lazy_gettext('Participants'),
        'online_participant_count': lazy_gettext('Participants Online'),
    }

    form_create_rules = form_edit_rules = [
        rules.FieldSet(
            ('number', 'name', 'conference_profile'),
            gettext('Basic Settings')
        ),
        rules.FieldSet(
            ('is_public', 'public_participant_profile'),
            gettext('Open Access')
        ),
        rules.FieldSet(
            ('participants',),
            gettext('Participants')
        ),
    ]

    column_formatters = {
        'legend': lambda v,c,m,n: legend_formatter(v,c,m,n),
    }

    column_descriptions = {
        'participants': lazy_gettext('Use <a href="/participant/">Participants</a> menu to manage participant list'),
    }

    form_args = {
        'number': {'validators': [Required(), is_number]},
        'name': {'validators': [Required()]},
        'conference_profile': {'validators': [Required()]},
        'public_participant_profile': {'validators': [Required()]},
    }

    form_widget_args = {
        'participants': {'disabled': True},
    }

    @expose('/details/')
    def details_view(self):
        conf = self.get_one(request.args.get('id', 0))
        if not conf:
            abort(404)
        self._template_args['confbridge_participants'] = \
            asterisk.confbridge_list_participants(conf.number)
        self._template_args['confbridge'] = asterisk.confbridge_get(conf.number)
            
        return super(ConferenceAdmin, self).details_view()


    @expose('/contacts/', methods=['POST'])
    def add_contacts(self):
        if request.method == 'POST':
            if not request.form.get('conference') or not request.form.get(
                'profile'):
                    flash(
                        gettext('You must select Conference and Profile'))
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
            asterisk.originate(conf.number, phone,
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
            k['callerid'] for k in asterisk.confbridge_list_participants(conf.number)]
        gen = (p for p in conf.participants if p.phone not in online_participants)
        for p in gen:
                asterisk.originate(conf.number, p.phone, name=p.name,
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
            asterisk.confbridge_kick(conf.number, channel)
            flash(gettext('Channel %(channel)s is kicked.', channel=channel))
        else:
            asterisk.confbridge_kick_all(conf.number)
            flash(gettext('All participants have been kicked from the conference.'))

        time.sleep(1)
        return redirect(url_for('.details_view', id=conf.id))


    @expose('/mute/<conf_id>')
    @expose('/mute/<conf_id>/channel/<path:channel>')
    def mute(self, conf_id, channel=None):
        conf = Conference.query.get_or_404(conf_id)
        if channel:
            asterisk.confbridge_mute(conf.number, channel)
            msg = gettext('Participant %(channel)s muted.', channel=channel)
            flash(msg)
            #conf.log(msg)
        else:
            # Mute all
            for p in asterisk.confbridge_list_participants(conf.number):
                asterisk.confbridge_mute(conf.number, p['channel'])
            msg = gettext('Conference muted.')
            flash(msg)
            conf.log(msg)

        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/unmute/<conf_id>')
    @expose('/unmute/<conf_id>/channel/<path:channel>')
    def unmute(self, conf_id, channel=None):
        conf = Conference.query.get_or_404(conf_id)
        if channel:
            asterisk.confbridge_unmute(conf.number, channel)
            flash(gettext('Participant %(channel)s unmuted.', channel=channel))
        else:
            # Unmute all
            for p in asterisk.confbridge_list_participants(conf.number):
                asterisk.confbridge_unmute(conf.number, p['channel'])
            flash(gettext('Conference unmuted.'))

        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/record_start')
    def record_start(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        asterisk.confbridge_record_start(conf.number)
        flash(gettext('The conference recording has been started.'))
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/record_stop')
    def record_stop(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        asterisk.confbridge_record_stop(conf.number)
        flash(gettext('The conference recording has been stopped.'))
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/lock')
    def lock(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        asterisk.confbridge_lock(conf.number)
        flash(gettext('The conference has been locked.'))
        time.sleep(1)
        return redirect(url_for('.details_view', id=conf_id))


    @expose('/<int:conf_id>/unlock')
    def unlock(self, conf_id):
        conf = Conference.query.get_or_404(conf_id)
        asterisk.confbridge_unlock(conf.number)
        flash(gettext('The conference has been unlocked.'))
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
    #can_create = False
    #can_edit = False
    #list_template = 'recording_list.html'
    #column_filters = ['room', 'create_date']
    #column_default_sort = 'create_date'
    can_upload = False
    can_download = True
    can_delete = True
    can_mkdir = False
    can_rename = True

    #@expose('/update/')
    #def update_recording_list(self):
    #    for filename in os.listdir(ASTERISK_MONITOR_DIR):
    #        print filename
    #        if not Recording.query.filter_by(filename=filename).first():
    #            rec = Recording()
    #            rec.create_date = datetime.now()
    #            rec.filename = filename
    #            rec.room = '101'
    #            db.session.add(rec)
    #            db.session.commit()
    #    return redirect('recording')


class ConferenceProfileAdmin(ModelView, AuthBaseView):
    column_list = [
        'name', 'max_members', 'record_conference',
        'internal_sample_rate', 'mixing_interval', 'video_mode'
    ]

    column_descriptions = {
        'max_members': gettext("""Limits the number of participants for a single conference to a specific number. By default, conferences have no participant limit. After the limit is reached, the conference will be locked until someone leaves. Admin-level users are exempt from this limit and will still be able to join otherwise-locked, because of limit, conferences."""),
        'record_conference': gettext("""Records the conference call starting when the first user enters the room, and ending when the last user exits the room. The default recorded filename is 'confbridge-<name of conference bridge>-<start time>.wav' and the default format is 8kHz signed linear. By default, this option is disabled. This file will be located in the configured monitoring directory as set in asterisk.conf"""),
        'internal_sample_rate': gettext("""Sets the internal native sample rate at which to mix the conference. The "auto" option allows Asterisk to adjust the sample rate to the best quality / performance based on the participant makeup. Numbered values lock the rate to the specified numerical rate. If a defined number does not match an internal sampling rate supported by Asterisk, the nearest sampling rate will be used instead."""),
        'mixing_interval': gettext("""Sets, in milliseconds, the internal mixing interval. By default, the mixing interval of a bridge is 20ms. This setting reflects how "tight" or "loose" the mixing will be for the conference. Lower intervals provide a "tighter" sound with less delay in the bridge and consume more system resources. Higher intervals provide a "looser" sound with more delay in the bridge and consume less resources"""),
        'video_mode': gettext("""Configured video (as opposed to audio) distribution method for conference participants. Participants must use the same video codec. Confbridge does not provide MCU functionality. It does not transcode, scale, transrate, or otherwise manipulate the video. Options are "none," where no video source is set by default and a video source may be later set via AMI or DTMF actions; "follow_talker," where video distrubtion follows whomever is talking and providing video; "last_marked," where the last marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user previous to the last-joined will be used as the video source; and "first-marked," where the first marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user that joined next will be used as the video source. Use of video in conjunction with the jitterbuffer results in the audio being slightly out of sync with the video - because the jitterbuffer only operates on the audio stream, not the video stream. Jitterbuffer should be disabled when video is used.""")
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
            gettext('Basic')),
        rules.FieldSet(
            (
                'announce_user_count',
                'announce_user_count_all',
                'announce_only_user',
                'announcement',
                'announce_join_leave',
                ),
            gettext('Announcements')
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
            gettext('Voice Processing')
            )
    ]

    column_descriptions = {
        'admin': gettext('Sets if the user is an Admin or not. By default, no.'),
        'marked': gettext('Sets if the user is Marked or not. By default, no.'),
        'startmuted': gettext('Sets if the user should start out muted. By default, no.'),
        'pin': gettext('Sets if the user must enter a PIN before joining the conference. The user will be prompted for the PIN.'),
        'startmuted': gettext('Sets if the user should start out muted. By default, no.'),
        'quiet': gettext('When set, enter/leave prompts and user introductions are not played. By default, no.'),
        'wait_marked': gettext('Sets if the user must wait for another marked user to enter before joining the conference. By default, no.'),
        'end_marked': gettext('If enabled, every user with this option in their profile will be removed from the conference when the last marked user exists the conference.'),
        'dtmf_passthrough': gettext('Whether or not DTMF received from users should pass through the conference to other users. By default, no.'),
        'music_on_hold_when_empty': gettext('Sets whether music on hold should be played when only one person is in the conference or when the user is waiting on a marked user to enter the conference. By default, off.'),
        'music_on_hold_class': gettext('Sets the music on hold class to use for music on hold.'),
        'announce_user_count': gettext('Sets if the number of users in the conference should be announced to the caller. By default, no.'),
        'announce_user_count_all': gettext('Choices: yes, no, integer. Sets if the number of users should be announced to all other users in the conference when someone joins. When set to a number, the announcement will only occur once the user count is above the specified number'),
        'announce_only_user': gettext('Sets if the only user announcement should be played when someone enters an empty conference. By default, yes.'),
        'announcement': gettext('If set, the sound file specified by filename will be played to the user, and only the user, upon joining the conference bridge.'),
        'announce_join_leave': gettext('When enabled, this option prompts the user for their name when entering the conference. After the name is recorded, it will be played as the user enters and exists the conference. By default, no.'),
        'dsp_drop_silence': gettext('Drops what Asterisk detects as silence from entering into the bridge. Enabling this option will drastically improve performance and help remove the buildup of background noise from the conference. This option is highly recommended for large conferences, due to its performance improvements.'),
        'dsp_talking_threshold': gettext("""The time, in milliseconds, by default 160, of sound above what the DSP has established as base-line silence for a user, before that user is considered to be talking. This value affects several options:
Audio is only mixed out of a user's incoming audio stream if talking is detected. If this value is set too loose, the user will hear themselves briefly each time they begin talking until the DSP has time to establish that they are in fact talking.
When talker detection AMI events are enabled, this value determines when talking has begun, which causes AMI events to fire. If this value is set too tight, AMI events may be falsely triggered by variants in the background noise of the caller.
The drop_silence option depends on this value to determine when the user's audio should be mixed into the bridge after periods of silence. If this value is too loose, the beginning of a user's speech will get cut off as they transition from silence to talking."""),
        'dsp_silence_threshold': gettext("""The time, in milliseconds, by default 2500, of sound falling within what the DSP has established as the baseline silence, before a user is considered to be silent. The best way to approach this option is to set it slightly above the maximum amount of milliseconds of silence a user may generate during natural speech. This value affects several operations:
When talker detection AMI events are enabled, this value determines when the user has stopped talking after a period of talking. If this value is set too low, AMI events indicating that the user has stopped talking may get faslely sent out when the user briefly pauses during mid sentence.
The drop_silence option depends on this value to determine when the user's audio should begin to be dropped from the bridge, after the user stops talking. If this value is set too low, the user's audio stream may sound choppy to other participants."""),
        'talk_detection_events': gettext('Sets whether or not notifications of when a user begins and ends talking should be sent out as events over AMI. By default, no.'),
        'denoise': gettext('Whether or not a noise reduction filter should be applied to the audio before mixing. By default, off. This requires codec_speex to be built and installed. Do not confuse this option with drop_silence. denoise is useful if there is a lot of background noise for a user, as it attempts to remove the noise while still preserving the speech. This option does not remove silence from being mixed into the conference and does come at the cost of a slight performance hit.'),
        'jitterbuffer': gettext("Whether or not to place a jitter buffer on the caller's audio stream before any audio mixing is performed. This option is highly recommended, but will add a slight delay to the audio and will incur a slight performance penalty. This option makes use of the JITTERBUFFER dialplan function's default adaptive jitter buffer. For a more fine-tuned jitter buffer, disable this option and use the JITTERBUFFER dialplan function on the calling channel, before it enters the ConfBridge application."),

    }


admin = Admin(
    app,
    name='PBXWare Conf Manager',
    index_view=AdminIndexView(        
        template='admin/index.html',
        url='/'
    ),
    template_mode='bootstrap3',
    category_icon_classes={
        'Profiles': 'glyphicon glyphicon-wrench',
    }
)


admin.add_view(ConferenceAdmin(
    Conference,
    db.session,
    name=lazy_gettext('Conferences'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-bullhorn'
    )
)


admin.add_view(ParticipantAdmin(
    Participant,
    db.session,
    name=lazy_gettext('Participants'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-user'
    )
)

admin.add_view(ContactAdmin(
    Contact,
    db.session,
    name=lazy_gettext('Contacts'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-book'
    )
)

admin.add_view(RecordingAdmin(
    app.config['ASTERISK_MONITOR_DIR'],
    '/static/recording/',
    endpoint='recording',
    name=lazy_gettext('Recordings'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-hdd'
    )
)

admin.add_view(ParticipantProfileAdmin(
    ParticipantProfile,
    db.session,
    category=lazy_gettext('Profiles'),
    endpoint='participant_profile',
    url='/profile/participant/',
    name=lazy_gettext('Participant'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-user'
    )
)

admin.add_view(ConferenceProfileAdmin(
    ConferenceProfile,
    db.session,
    category=lazy_gettext('Profiles'),
    endpoint='room_profile',
    url='/profile/room/',
    name=lazy_gettext('Conference'),
    menu_icon_type='glyph',
    menu_icon_value='glyphicon-bullhorn',
    )
)
