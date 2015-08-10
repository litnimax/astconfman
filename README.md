# Asterisk Conference Manager
**Built on Flask, SocketIO, React.js**

This is a special WEB based interface for managing Asterisk ConfBridge appliction.

### Installation
Download latest version:
```
wget https://github.com/litnimax/astconfman/archive/master.zip
unzip master.zip
cd astconfman-master
virtualenv env
source env/bin/activate
pip install -r requirements.txt
```

### Configuration
#### WEB server configuration
Go to *instance* folder and create there config.py file with your local settings. See [config.py](https://github.com/litnimax/astconfman/blob/master/astconfman/config.py) for options.
Some comments:
* ADMINS - users for http authorization.
* ASTERISK_IPADDR - IP address of Asterisk server. URL's fetched from dialplan are protected and open only for that IP address.

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




