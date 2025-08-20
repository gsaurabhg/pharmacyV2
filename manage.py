#!/usr/bin/env python
import os
import sys
# Redirect after logout
LOGOUT_REDIRECT_URL = '/'

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pharmacysite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

if '--nostatic' not in sys.argv:
    sys.argv.append('--nostatic')