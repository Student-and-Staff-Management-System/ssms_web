#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

# Run migrations
# Using --fake-initial to handle cases where tables already exist
python manage.py migrate --fake-initial
