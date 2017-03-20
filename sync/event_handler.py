import os
from logging import getLogger
from os.path import isfile, isdir, exists

from watchdog.events import LoggingEventHandler

import sync.defaults as defaults
from loxcommon import os_utils
from sync.controllers import openfiles_ctrl
from sync.controllers.login_ctrl import LoginController
from sync.localbox import get_localbox_path


class LocalBoxEventHandler(LoggingEventHandler):
    """Logs all the events captured."""

    def __init__(self, localbox_client):
        self.localbox_client = localbox_client

    def on_moved(self, event):
        super(LoggingEventHandler, self).on_moved(event)

        pass

        try:
            localbox_path = get_localbox_path(self.localbox_client.path, event.src_path)
            passphrase = LoginController().get_passphrase(self.localbox_client.label)

            if isfile(event.dest_path):
                self.localbox_client.move_file(event.src_path, event.dest_path, passphrase)
            elif isdir(event.dst_path):
                key, iv = self.localbox_client.create_directory(localbox_path)

                for root, dirs, files in os.walk(event.dst_path):
                    for name in dirs:
                        localbox_path = get_localbox_path(self.localbox_client.path, os.path.join(root, name))
                        self.localbox_client.create_directory(localbox_path)
                    for name in files:
                        self.localbox_client.move_file(event.src_path, os.path.join(root, name), passphrase)

        except Exception as ex:
            getLogger(__name__).exception(ex)

    def on_created(self, event):
        super(LoggingEventHandler, self).on_created(event)

        if event.is_directory:
            self.localbox_client.create_directory(get_localbox_path(self.localbox_client.path, event.src_path))
        elif _should_upload_file(event.src_path):
            self.localbox_client.upload_file(fs_path=event.src_path,
                                             path=get_localbox_path(self.localbox_client.path, event.src_path),
                                             passphrase=LoginController().get_passphrase(self.localbox_client.label))
        else:
            getLogger(__name__).debug('%s ignored' % event.src_path)

    def on_deleted(self, event):
        super(LocalBoxEventHandler, self).on_deleted(event)

        try:
            if _should_delete_file(event.src_path):
                self.localbox_client.delete(get_localbox_path(self.localbox_client.path, event.src_path))
                openfiles_ctrl.remove(
                    filesystem_path=os_utils.remove_extension(event.src_path, defaults.LOCALBOX_EXTENSION))
        except Exception as ex:
            # catch any exception and log it. Then continue listening to the events
            getLogger(__name__).exception(ex)


def _should_upload_file(path):
    return exists(path) and not path.endswith(defaults.LOCALBOX_EXTENSION) and os.path.getsize(
        path) > 0 and path not in openfiles_ctrl.load()


def _should_delete_file(path):
    return path.endswith(defaults.LOCALBOX_EXTENSION) or isdir(path)
