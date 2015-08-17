import commands
import os
import shutil
import tempfile
from flask.ext.babelex import gettext
from transliterate import translit
from app import app



def confbridge_list():
    rooms = []
    status, output = commands.getstatusoutput(
        "%s -rx 'confbridge list'" % app.config['ASTERISK_EXECUTABLE'])
    if status != 0:
        raise Exception(output)
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit():
            rooms.append(line)
    return rooms


def confbridge_list_participants(confno):
    status, output = commands.getstatusoutput("%s -rx 'confbridge list %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno))
    if status != 0:
        raise Exception(output)
    participants = []
    lines = output.split('\n')

    """
    if len(lines) <= 2:
        return []
    column_formatters = lines[1].split(' ')
    column_lens = [len(k) for k in column_formatters]
    column_indexes = []
    for line in lines[2:]:
        start_pos = 0
        participant = []
        for pos in column_lens:
            participant.append(line[start_pos:start_pos+pos].strip())
            start_pos += pos
        participants.append(participant)
    """
    if len(lines) < 3:
        return []
    for line in lines[2:]:
        line = line.split()
        if len(line) == 3:
            # No flags
            participants.append({
                'channel': line[0],
                'flags': '',
                'callerid': line[2],
                }
            )
        elif len(line) == 4:
            # Flags are set
            participants.append({
                'channel': line[0],
                'flags': line[1],
                'callerid': line[3],
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
    rooms = []
    status, output = commands.getstatusoutput(
        "%s -rx 'confbridge list'" % app.config['ASTERISK_EXECUTABLE'])
    if status != 0:
        raise Exception(output)
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit():
            rooms.append(line)
    for room in rooms:
        if room[0] == confno:
            return room


def confbridge_get_user_count(confno):
    bridges = confbridge_list()
    for bridge in bridges:
        if bridge[0] == confno:
            return bridge[1]


def confbridge_is_locked(confno):
    bridges = confbridge_list()
    for bridge in bridges:
        if bridge[0] == confno:
            return bridge[3] == 'locked'


def confbridge_kick(confno, channel):
    return commands.getoutput("%s -rx 'confbridge kick %s %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno,
        channel,
        )
    )


def confbridge_kick_all(confno):
    return commands.getoutput("%s -rx 'confbridge kick %s all'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno
        )
    )


def confbridge_mute(confno, channel):
    return commands.getoutput("%s -rx 'confbridge mute %s %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno,
        channel
        )
    )


def confbridge_unmute(confno, channel):
    return commands.getoutput("%s -rx 'confbridge unmute %s %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno,
        channel
        )
    )


def confbridge_lock(confno):
    return commands.getoutput("%s -rx 'confbridge lock %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno,
        )
    )


def confbridge_unlock(confno):
    return commands.getoutput("%s -rx 'confbridge unlock %s'" % (
        app.config['ASTERISK_EXECUTABLE'],
        confno,
        )
    )


def confbridge_record_start(confno):
    return commands.getoutput("%s -rx 'confbridge record start %s'" % (
                              app.config['ASTERISK_EXECUTABLE'],
                              confno))

def confbridge_record_stop(confno):
    return commands.getoutput("%s -rx 'confbridge record stop %s'" % (
                              app.config['ASTERISK_EXECUTABLE'],
                              confno))
