#!/usr/bin/env python   
import sys
from gevent.wsgi import WSGIServer
from app import app


if __name__=='__main__':
    server = WSGIServer((app.config['LISTEN_ADDRESS'],
                         app.config['LISTEN_PORT']),
                        app)
    server.serve_forever()