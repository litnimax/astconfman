# *-* encoding: utf-8 *-*
import os
from flask_babelex import lazy_gettext as _

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

# ASTERISK_IPADDR - IP Address of Asterisk server. All other requests will be denied.
ASTERISK_IPADDR = '127.0.0.1'

# LISTEN_ADDRESS - Interfaces to bind to. '0.0.0.0' for all interfaces.
LISTEN_ADDRESS = '0.0.0.0'

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

SECURITY_REGISTERABLE = False
SECURITY_RECOVERABLE = False
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
SECURITY_USER_IDENTITY_ATTRIBUTES = 'username'
SECURITY_PASSWORD_HASH = 'sha512_crypt'
SECURITY_PASSWORD_SALT = 'bla-bla-bla'


# Asterisk
ASTERISK_SPOOL_DIR = '/var/spool/asterisk/outgoing/'
ASTERISK_MONITOR_DIR = '/var/spool/asterisk/monitor/'
ASTERISK_EXECUTABLE = '/usr/sbin/asterisk'
ASTERISK_SSH_ENABLED = False
ASTERISK_SSH_PORT = '22'
ASTERISK_SSH_HOST = 'localhost'
ASTERISK_SSH_USER = 'asterisk'
ASTERISK_SSH_KEY = 'ssh-rsa AAAAB3NzaC1yc2EA...' # Put your key in instance config

# You can remove any tab by adding it here.
DISABLED_TABS = []

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
