#!/usr/bin/env bash

SCRIPT=backup.py
PYTHON_VENV=venv/bin/python
CRONLOG=cronjob.log
echo "add the following to crontab file"
echo ""
echo "@reboot $(realpath -s $PYTHON_VENV) $(realpath $SCRIPT)>$(realpath $CRONLOG) 2>&1"
