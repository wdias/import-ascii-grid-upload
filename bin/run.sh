#!/usr/bin/env bash

if test "${APPNAME}" = "worker" ; then
  echo "Start Grid Workers... ${HOSTNAME}"
  supervisord -c bin/supervisord.conf
else
  echo "Start server..."
  gunicorn -b 0.0.0.0:8080 --timeout=10 --workers=4 web.app:app
fi
