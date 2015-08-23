# Asterisk ConfBridge Manager
This is a WEB based interface for managing Asterisk ConfBridge appliction.

**Built on Asterisk ConfBridge, Flask, SocketIO, React.js**

You can request a [new feature](https://github.com/litnimax/astconfman/issues/new) or see current requests and bugs [here](https://github.com/litnimax/astconfman/issues).

# Features

* Private (only for configured participants) and public (guests can join) conferences.
* Muted participant can indicate unmute request. 
* Contact management (addressbook) with import contacts feature.
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

### Demo

Here is the demo with the folling scenatio:
* Import contacts.
* Add contacts to participants.
* Invite all participants into conference.
* Enter conference from phone.
* Unmute request from phone.
* Invite customer by his PSTN number.
* Enter non-public conference.

[![Demo](http://img.youtube.com/vi/R1EV4D8cFj8/0.jpg)](https://youtu.be/R1EV4D8cFj8 "Demo")

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

Now you should init database and run the server:
```
cd astconfman
./manage.py init
./run.py
```
Now visit http://localhost:5000/ in your browser.

Default user/password is admin/test.

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
Asterisk must have CURL function compiled and loaded. Check it with
```
*CLI> core show  function CURL
```
You must include files in astconfman/asterisk_etc folder from your Asterisk installation.

Put 
```
#include /path/to/astconfman/asterisk_etc/extensions.conf
```
to your /etc/asterisk/extensions.conf
and
```
#include /path/to/astconfman/asterisk_etc/confbridge.conf
```
to your /etc/asterisk/confbridge.conf.

Open extensions.conf with your text editor and set your settings in *globals* section.

### Participant menu
While in the conference participants can use the following DTMF options:

* 1 - Toggle mute / unmute myself.
* 2 - Unmute request.
* 3 - Toggle mute all participants (admin profile only).
* 4 - Decrease listening volume.
* 5 - Reset listening volume.
* 6 - Increase listening volume.
* 7 - Decrease talking volume.
* 8 - Reset talking volume.
* 9 - Increase talking volume.
* 0 - Invite all / not yet connected participants (admin profile only).


