#!/bin/bash

# Since we're using supervisor to daemonize the app, we can use the
# supervisorctl command line tool to stop things and turn on another process
# called "maintenance" that will display a friendly message to users while the
# app is getting updated.
supervisorctl stop all

#supervisorctl start maintenance
