# *-* encoding:utf-8 *-*

from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, file_required, file_allowed
from wtforms.validators import ValidationError
from flask.ext.babelex import gettext


class ContactImportForm(Form):
    filename = FileField(gettext('File'),
            validators=[file_required(), 
                        file_allowed(['csv', 'CSV'])])

    def validate_filename(form, field):
        data = field.data.readlines()
        linenum = 1
        for line in data:
            if not len(line.split(',')) == 2:
                msg = gettext('CSV file is broken, line %(linenum)s',
                              linenum=linenum)                
                raise ValidationError(msg)
            elif not line[0].isdigit():
                raise ValidationError(gettext(
                    'The first column does not contain phone number, line %(linenum)s', linenum=linenum))
            linenum += 1
        field.data.seek(0)
                

