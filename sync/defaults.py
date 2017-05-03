"""
listing of values/variables' default values.
"""
from os.path import abspath, join
from os.path import dirname
from os.path import exists
from os.path import expandvars
from os.path import join

PACKAGEDIR = dirname(abspath(__file__))

# assuming 'c:' only exists on 'Windows' machines and adjust path accordingly
if exists("c:"):
    APPDIR = join(expandvars("%APPDATA%"), 'LocalBox')
else:
    # We assume anything nonwindows is POSIX-like
    APPDIR = join(expandvars("$HOME"), '.config', 'localbox')

SYNCINI_PATH = join(APPDIR, 'sync.ini')
SITESINI_PATH = join(APPDIR, 'sites.ini')
LOCALBOX_SITES_PATH = join(APPDIR, 'sites.pickle')
LOCALBOX_SHARES_PATH = join(APPDIR, 'shares.pickle')
LOCALBOX_PREFERENCES_PATH = join(APPDIR, 'prefs.pickle')
LOCALBOX_ACCOUNT_PATH = join(APPDIR, 'account.pickle')
DATABASE_PATH = join(APPDIR, 'database.sqlite3')
LOG_PATH = join(APPDIR, 'localbox-sync.log')
LOCALE_PATH = join(PACKAGEDIR, 'locale')
DEFAULT_LANGUAGE = 'ENGLISH'
LOCALBOX_EXTENSION = '.lox'

OLD_SYNC_STATUS = join(APPDIR, 'localbox.pickle.')
LOCALBOX_OPENFILES = join(APPDIR, 'openfiles.pickle')

#: If the call fails because of HTTP 401, reauthenticate and retry the call this amount of times
MAX_AUTH_RETRIES = 5
