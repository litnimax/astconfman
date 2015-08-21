#!/usr/bin/env python   
import sys
from flask import Flask
from app import app, socketio

if __name__=='__main__':
    #app.run()
    #sys.exit(0)
    socketio.run(app,
                 host=app.config['LISTEN_ADDRESS'],
                 port=app.config['LISTEN_PORT'],
                 log_output=True
                 )
