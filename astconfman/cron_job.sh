#!/bin/bash

cd `dirname $0`

source env/bin/activate

./manage.py start_conf $1
