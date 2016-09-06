#!/bin/bash

# Make sure everything you'd expect is owned by the datamade user
chown -R datamade.www-data /home/datamade

# Install things into the correct virtual environment
/home/datamade/.virtualenvs/nmid/bin/pip install -r /home/datamade/dedupe-api/requirements.txt --upgrade

# Decrypt encrypted files with blackbox
cd /home/datamade/dedupe-api && blackbox_postdeploy

# Run any setup scripts that you might have.
/home/datamade/.virtualenvs/dedupe-api/bin/python /home/datamade/dedupe-api/init_db.py
