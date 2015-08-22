# Asterisk Conference Manager
**Built on Flask, SocketIO, React.js**

This is a WEB based interface for managing Asterisk ConfBridge appliction.

**Features**:

* Private (only for configured participants) and public (guests can join) conferences.
* Muted participant can indicate unmute request. 
* Contact management (addressbook).
* Conference recording (always / ondemand, web access to recordings).
* Support for dynamic ConfBridge [profiles](https://wiki.asterisk.org/wiki/display/AST/ConfBridge#ConfBridge-BridgeProfileConfigurationOptions) (any profile option can be set).
* Invite participants from WEB or phone (on press DTMF digit).
* Invite guests on demand by phone number.
* Conference management:
 * Lock / unlock conference;
 * Kick one / all;
 * Mute / unmute one / all 
* Realtime conference events log (enter, leave, kicked, mute / unmute, dial status, etc)
* Asterisk intergrators re-branding ready (change logo, banner, footer)

### Installation
Download the latest version:
```
wget https://github.com/litnimax/astconfman/archive/master.zip
unzip master.zip
mv astconfman-master astconfman
```
Or you can clone the repository with:
```
git clone https://github.com/litnimax/astconfman.git
```
Next steps:
```
cd astconfman
virtualenv env
source env/bin/activate
pip install -r requirements.txt
```
The above will download and install all runtime requirements.

### Configuration
#### WEB server configuration
Go to *instance* folder and create there config.py file with your local settings. See [config.py](https://github.com/litnimax/astconfman/blob/master/astconfman/config.py) for possible options to override.
Options in config.py file are self-descriptive. Here is an example of instance/config.py file:
```python
LANGUAGE = 'ru'
SECRET_KEY = 'jdjHDHD84s@#$%)skjfnNJsk!@0dKDJD94SJ34p,s}s,!wJ'
ADMINS = {
    'max': {
        'password': 'HJd84h&s34S',
        'email': 'max@company.com',
    },
    'alex': {
        'password': '87Jsm@#k8!d',
        'email': 'alex@company.com',
    },
}

ASTERISK_IPADDR = '192.168.0.254'
LISTEN_ADDRESS = '0.0.0.0'
DATABASE_FILE = '/var/lib/db/astconfman.db'
```

#### Asterisk configuration
You must include files in asterisk_etc folder from your Asterisk installation.

Put 
```
#include /path/to/astconfman-master/asterisk_etc/extensions.conf
```
to your /etc/asterisk/extensions.conf
and 
```
#include /path/to/astconfman-master/asterisk_etc/confbridge.conf
```
to your /etc/asterisk/confbridge.conf.

### Run WEB server
Init database:
```
cd astconfman
./manage.py init
```
Run:
```
./run.py
```

