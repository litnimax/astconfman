# *-* encoding:utf-8 *-*

from flask.ext.wtf import Form
from flask.ext.admin.form import BaseForm as BaseAdminForm
from flask.ext.wtf.file import FileField, file_required, file_allowed
from wtforms.validators import ValidationError
from flask.ext.babelex import lazy_gettext as _


class ContactImportForm(Form):
    filename = FileField(_('File'),
            validators=[file_required(), 
                        file_allowed(['csv', 'CSV'])])

    def validate_filename(form, field):
        data = field.data.readlines()
        linenum = 1
        for line in data:
            if not len(line.split(',')) == 2:
                msg = _('CSV file is broken, line %(linenum)s',
                              linenum=linenum)                
                raise ValidationError(msg)
            elif not line[0].isdigit():
                raise ValidationError(_(
                    'The first column does not contain phone number, line %(linenum)s', linenum=linenum))
            linenum += 1
        field.data.seek(0)
                

class ConferenceForm(BaseAdminForm):
    #class Meta:
    #    locales = ['ru_RU']
    #  See https://github.com/litnimax/astconfman/issues/8

    def validate_is_public(self, field):
        profile = self.data.get('public_participant_profile')
        if not profile:
            raise ValidationError(_(u'You must select a Public Participant'
                                          ' Profile for a Public Conference.'))

