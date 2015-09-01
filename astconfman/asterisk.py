import commands
import os
import shutil
import tempfile
from flask.ext.babelex import gettext
from transliterate import translit
from app import app


def _get_version():
    version = app.config.get('ASTERISK_VERSION', None)
    if not version:
        raise Exception('You must set ASTERISK_VERSION in your config.py')
    try:
        a,b,c = version.split('.')
        formatted = '%02.f%02.f%02.f' % (float(a),float(b),float(c))
        return formatted
    except (IndexError, ValueError):
        raise Exception('You must set the correct Asterisk version number like 13.2.0')


def _cli_command(cmd):
    status, output = commands.getstatusoutput(
        "%s -rx '%s'" % (app.config['ASTERISK_EXECUTABLE'], cmd))
    if status != 0:
        raise Exception(output)
    return output
    


def confbridge_list():
    rooms = []
    output = _cli_command('confbridge list')
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit():
            rooms.append(line)
    return rooms


def confbridge_list_participants(confno):
    output = _cli_command('confbridge list %s' % confno)
    participants = []
    lines = output.split('\n')
    # No participants is the same for all versions
    if len(lines) < 3:
        return []
    ast_version = _get_version()
    for line in lines[2:]:
        print 1, line
        line = line.split()
        channel = line[0]
        flags = ''
        callerid = ''
        if ast_version < '120000':
            if len(line) == 4:
                callerid = line[2]
                flags = 'm' if line[3] == 'Yes' else ''

        else:
            if len(line) == 3:
                # No flags
                flags = ''
                callerid = line[2]
            elif len(line) == 4:
                # Flags are set
                flags = line[1]
                callerid = line[3]

        participants.append({
                'channel': channel,
                'flags': flags,
                'callerid': callerid,
                }
        )

    return participants


def originate(confnum, number, name='', bridge_options=[], user_options=[]):
    tempname = tempfile.mktemp()
    f = open(tempname, mode='w')
    f.write(app.config['CALLOUT_TEMPLATE'] % {'number': number,
                                              'name': translit(name, 'ru',
                                                               reversed=True),
                                              'confnum': confnum})
    f.write('\n')
    # Now iterate over profile options
    for option in user_options:
        o, v = option.split('=')
        f.write('Set: CONFBRIDGE(user,%s)=%s\n' % (o, v))
    for option in bridge_options:
        o, v = option.split('=')
        f.write('Set: CONFBRIDGE(bridge,%s)=%s\n' % (o, v))

    f.flush()
    f.close()
    # Move it to Asterisk outgoing calls queue.
    try:
        shutil.move(tempname, os.path.join(
            app.config['ASTERISK_SPOOL_DIR'],
                    '%s.%s' % (confnum, number)))
        raise OSError
    except OSError:
        # This happends that Asterisk immediately deleted call file
        pass


def confbridge_get(confno):
    output = _cli_command('confbridge list')
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit() and line[0] == confno:
            return {
                'name': line[0],
                'users': int(line[1]),
                'marked': False if line[2] == '0' else True,
                'locked': False if line[3] == 'unlocked' else True
            }


def confbridge_get_user_count(confno):
    return confbridge_get(confno)['users']


def confbridge_is_locked(confno):
    return confbridge_get(confno)['locked']


def confbridge_kick(confno, channel):
    return _cli_command('confbridge kick %s %s' % (confno, channel))


def confbridge_kick_all(confno):
    return _cli_command('confbridge kick %s all' % confno)


def confbridge_mute(confno, channel):
    return _cli_command('confbridge mute %s %s' % (confno, channel))


def confbridge_unmute(confno, channel):
    return _cli_command('confbridge unmute %s %s' % (confno, channel))


def confbridge_lock(confno):
    return _cli_command('confbridge lock %s' % confno)


def confbridge_unlock(confno):
    return _cli_command('confbridge unlock %s' % confno)
    

def confbridge_record_start(confno):
    return _cli_command('confbridge record start %s' % confno)


def confbridge_record_stop(confno):
    return _cli_command('confbridge record stop %s' % confno)
