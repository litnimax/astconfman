# *-* encoding: utf-8 *-*
import os
from flask.ext.babelex import lazy_gettext as _

# Default Language. Currenly only 'ru' and 'en' are supported.
LANGUAGE = 'en'

# Put here some random string
SECRET_KEY = 'change_me_here_to_random_key'

# BRAND_NAV - this defines the string on the right top navigation bar
BRAND_NAV = u'Asterisk Conference Manager'
# BRAND_FOOTER - put here your company info
BRAND_FOOTER = _(u"""(C) 2015 Asterisk Guru | <a href="http://asteriskguru.ru/">www.asteriskguru.ru</a> | Professional Asterisk support & development services.""")
# BRAND_LOGO - replace logo.png or change here url to your own logo
BRAND_LOGO = 'static/logo.png'
# URL to redirect when clicked on LOGO. Put here '#' if redirect is not required.
BRAND_LOGO_URL = 'http://www.pbxware.ru/'

# 
ADMINS = {
    'admin': {
        'password': 'test',
        'email': '',
    },

}

# ASTERISK_IPADDR - IP Address of Asterisk server. All other requests will be denied.
ASTERISK_IPADDR = '127.0.0.1'

# LISTEN_ADDRESS - Interfaces to bind to. '0.0.0.0' for all interfaces.
LISTEN_ADDRESS = '127.0.0.1'

# LISTEN_PORT - Port to listen on.
LISTEN_PORT = 5000

# Always leave DEBUG=False in production. DEBUG=True is a security hole as it
# allows the execution of arbitrary Python code. Be warned!
DEBUG = False

# SQLALCHEMY_ECHO - prints SQL statements.
SQLALCHEMY_ECHO = False

# See http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html#database-urls 
DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'astconfman.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_FILE

WTF_CSRF_ENABLED = True

# Asterisk
ASTERISK_SPOOL_DIR = '/var/spool/asterisk/outgoing/'
ASTERISK_MONITOR_DIR = '/var/spool/asterisk/monitor/'
ASTERISK_EXECUTABLE = '/usr/sbin/asterisk'

# This defines the order of tabs. You can also remove any tab from this list to hide it.
TABS = ['conferences', 'plans', 'participants', 'contacts', 'recordings',
        'participant_profiles', 'conference_profiles']

# Callout template.
CALLOUT_TEMPLATE = """Channel: Local/%(number)s@confman-dialout
Context: confman-bridge
Extension: %(confnum)s
Priority: 1
MaxRetries: 0
RetryTime: 15
WaitTime: 300
Set: participant_name=%(name)s
Set: participant_number=%(number)s
Set: conf_number=%(confnum)s
"""
