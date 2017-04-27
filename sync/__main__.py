"""
main module for localbox sync
"""
import os
import pickle
import signal
import json
import urllib
import urllib2
from logging import getLogger, ERROR
from os import makedirs, mkdir
from os.path import dirname, isdir, exists
from sys import argv
from threading import Event

import sync.__version__
from loxcommon import os_utils
from loxcommon.log import prepare_logging
from loxcommon.os_utils import open_file_ext
from sync import defaults
from sync.controllers import openfiles_ctrl
from sync.controllers.localbox_ctrl import ctrl as sync_ctrl, SyncsController
from sync.controllers.login_ctrl import LoginController
from sync.database import database_execute, DatabaseError
from sync.event_handler import create_watchdog
from sync.gui import gui_utils
from sync.gui import gui_wx
from sync.gui.taskbar import taskbarmain
from sync.localbox import LocalBox
from sync.syncer import MainSyncer
from sync.notif import NotifHandler
from .defaults import LOG_PATH, APPDIR, SYNCINI_PATH, OPEN_FILE_PORT
from .controllers import openfiles_ctrl as openfiles_ctrl

try:
    from ConfigParser import ConfigParser, SafeConfigParser
    from ConfigParser import NoOptionError
    from ConfigParser import NoSectionError
    from urllib2 import URLError
except ImportError:
    from configparser import ConfigParser, SafeConfigParser  # pylint: disable=F0401,W0611
    from configparser import NoOptionError  # pylint: disable=F0401,W0611
    from configparser import NoSectionError  # pylint: disable=F0401,W0611
    from urllib.error import URLError  # pylint: disable=F0401,W0611,E0611

    raw_input = input  # pylint: disable=W0622,C0103


def run_sync_daemon(observers=None):
    try:
        EVENT = Event()
        EVENT.clear()

        MAIN = MainSyncer(EVENT)
        MAIN.start()

        Notif = NotifHandler()
        Notif.start()

        taskbarmain(MAIN, observers)
    except Exception as error:  # pylint: disable=W0703
        getLogger(__name__).exception(error)


def run_event_daemon():
    for sync_item in SyncsController():
        create_watchdog(sync_item)


def run_file_decryption(filename):
    try:
        getLogger(__name__).info('Decrypting and opening file: %s', filename)

        # verify if the file belongs to any of the configured syncs
        sync_list = sync_ctrl.list

        localbox_client = None
        localbox_filename = None
        for sync_item in sync_list:
            getLogger(__name__).debug('sync path: %s' % sync_item.path)
            sync_path = sync_item.path if sync_item.path.endswith('/') else sync_item.path + os.path.sep
            if filename.startswith(sync_path):
                localbox_filename = os_utils.remove_extension(filename.replace(sync_item.path, ''),
                                                              defaults.LOCALBOX_EXTENSION)
                localbox_client = LocalBox(sync_item.url, sync_item.label, sync_item.path)
                break

        if not localbox_client or not localbox_filename:
            gui_utils.show_error_dialog(_('%s does not belong to any configured localbox') % filename, 'Error',
                                        True)
            getLogger(__name__).error('%s does not belong to any configured localbox' % filename)
            exit(1)

        # Request file to be opened
        data_dic = {
            "url": sync_item.url,
            "label": localbox_client.authenticator.label,
            "filename": filename,
            "localbox_filename": localbox_filename
        }

        with open(OPEN_FILE_PORT, 'rb') as f:
            port = pickle.load(f)

        url = 'http://localhost:{}/open_file'.format(port)
        data = json.dumps(data_dic)
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})

        answer = urllib2.urlopen(req)
        res_code = answer.getcode()

        # Open file and keep it in the open files list
        if res_code == 200:
            tmp_decoded_filename = answer.read()

            open_file_ext(tmp_decoded_filename)

            getLogger(__name__).info('Finished decrypting and opening file: %s', filename)

        # The file may not exist, or something else might have gone wrong
        elif res_code == 404:
            gui_utils.show_error_dialog(_('Failed to decode contents'), 'Error', standalone=True)
            getLogger(__name__).info('failed to decode contents. aborting')
            return

    except Exception as ex:
        getLogger(__name__).exception(ex)


if __name__ == '__main__':
    if not exists(APPDIR):
        mkdir(APPDIR)

    if not isdir(dirname(LOG_PATH)):
        makedirs(dirname(LOG_PATH))

    configparser = SafeConfigParser()
    configparser.read(SYNCINI_PATH)

    if not configparser.has_section('logging'):
        configparser.add_section('logging')
        configparser.set('logging', 'console', 'True')

    prepare_logging(configparser, log_path=LOG_PATH)
    getLogger('gnupg').setLevel(ERROR)

    getLogger(__name__).info("LocalBox Sync Version: %s (%s)", sync.__version__.VERSION_STRING,
                             sync.__version__.git_version)

    signal.signal(signal.SIGINT, openfiles_ctrl.remove_all)
    signal.signal(signal.SIGTERM, openfiles_ctrl.remove_all)
    try:
        # only on Windows
        signal.signal(signal.CTRL_C_EVENT, openfiles_ctrl.remove_all)
    except:
        pass

    try:
        sql = 'SELECT token FROM sites'
        database_execute(sql)
    except DatabaseError:
        sql = 'ALTER TABLE sites ADD COLUMN TOKEN CHAR(255)'
        database_execute(sql)
        getLogger(__name__).debug('TOKEN column added to table SITES')

    if len(argv) > 1:
        filename = argv[1]
        filename = ' '.join(argv[1:])

        run_file_decryption(filename)
    else:
        run_event_daemon()
        run_sync_daemon()
