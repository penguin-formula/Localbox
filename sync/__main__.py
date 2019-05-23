"""
main module for localbox sync
"""
import os
import signal
import sys
import wx
from logging import getLogger, ERROR
from os import makedirs, mkdir
from os.path import dirname, isdir, exists
from threading import Event

import sync.__version__
from loxcommon import os_utils
from loxcommon.log import prepare_logging
from loxcommon.os_utils import open_file_ext
from sync import defaults
from sync.controllers.localbox_ctrl import ctrl as sync_ctrl, SyncsController
from sync.database import database_execute, DatabaseError
from sync.event_handler import create_watchdog
from sync.gui import gui_utils
from sync.gui.taskbar import taskbarmain
from sync.heartbeat import Heartbeat
from sync.localbox import LocalBox
from sync.open_file import open_file
from sync.notif.notif_handler import NotifHandler
from sync.notif.notifs import Notifs
from sync.syncer import MainSyncer
from .controllers import openfiles_ctrl as openfiles_ctrl
from .defaults import LOG_PATH, APPDIR, SYNCINI_PATH

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

try:
    import win32_unicode_argv
except ImportError:
    pass


def run_sync_daemon(observers=None):
    try:
        EVENT = Event()
        EVENT.clear()

        MAIN = MainSyncer(EVENT)
        MAIN.start()

        Notif = NotifHandler()
        Notif.start()

        heartbeat = Heartbeat(MAIN)
        heartbeat.start()

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
        try:
            filename = filename.decode('utf-8')
        except UnicodeEncodeError:
            # on purpose, it's already an utf-8 string
            pass

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
            #exit(1)

        # Request file to be opened
        data_dic = {
            "url": sync_item.url,
            "label": localbox_client.authenticator.label,
            "filename": filename,
            "localbox_filename": localbox_filename
        }

        name = "LocalBoxApp-{}".format(wx.GetUserId())
        instance = wx.SingleInstanceChecker(name)
        app_is_running = instance.IsAnotherRunning()

        if app_is_running:
            file_to_open = Notifs().openFileReq(data_dic)
        else:
            file_to_open = open_file(data_dic)

        if file_to_open is not None and os.path.exists(file_to_open):
            open_file_ext(file_to_open)
            getLogger(__name__).info('Finished decrypting and opening file: %s', filename)

        else:
            gui_utils.show_error_dialog(_('Failed to decode contents'), 'Error', standalone=True)
            getLogger(__name__).info('failed to decode contents. aborting')

    except Exception as ex:
        getLogger(__name__).exception(ex)
        gui_utils.show_error_dialog(_('Exception {}').format(ex), 'Error', standalone=True)


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

    if len(sys.argv) > 1:
        filename = ' '.join(sys.argv[1:])

        run_file_decryption(filename)
    else:
        run_event_daemon()
        run_sync_daemon()
