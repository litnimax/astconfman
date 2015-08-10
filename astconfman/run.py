#!/usr/bin/env python   

from flask import Flask
from app import app, socketio

if __name__=='__main__':
    socketio.run(app)