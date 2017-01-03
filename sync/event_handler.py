import os
import time
from ConfigParser import NoOptionError
from logging import getLogger
from threading import Thread
from urllib2 import URLError

from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

import sync.defaults as defaults
from sync.controllers import openfiles_ctrl
from sync.controllers.localbox_ctrl import SyncsController
from sync.controllers.login_ctrl import LoginController
from sync.localbox import LocalBox, get_localbox_path


class LocalBoxEventHandler(LoggingEventHandler):
    """Logs all the events captured."""

    def __init__(self, localbox_client):
        self.localbox_client = localbox_client

    def on_created(self, event):
        super(LoggingEventHandler, self).on_created(event)

        if event.is_directory:
            self.localbox_client.create_directory(get_localbox_path(self.localbox_client.path, event.src_path))
        elif _should_upload_file(event.src_path):
            self.localbox_client.upload_file(fs_path=event.src_path,
                                             path=get_localbox_path(self.localbox_client.path, event.src_path),
                                             passphrase=LoginController().get_passphrase(self.localbox_client.label))


def _should_upload_file(path):
    return not path.endswith(defaults.LOCALBOX_EXTENSION) and os.path.getsize(
        path) > 0 and path not in openfiles_ctrl.load()


def get_event_runners():
    """

    """

    runners = []
    for sync_item in SyncsController():
        try:
            url = sync_item.url
            label = sync_item.label
            localbox_client = LocalBox(url, label, sync_item.path)

            runner = LocalBoxEventRunner(localbox_client=localbox_client)
            runners.append(runner)
        except NoOptionError as error:
            getLogger(__name__).exception(error)
            string = "Skipping '%s' due to missing option '%s'" % (sync_item, error.option)
            getLogger(__name__).info(string)
        except URLError as error:
            getLogger(__name__).exception(error)
            string = "Skipping '%s' because it cannot be reached" % (sync_item)
            getLogger(__name__).info(string)

    return runners


class LocalBoxEventRunner(Thread):
    """
    Thread responsible for listening for file system events
    """

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, localbox_client=None):
        Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        self.setDaemon(True)
        self.localbox_client = localbox_client

    def run(self):
        """
        Function that runs one iteration of the synchronization
        """
        getLogger(__name__).debug('running event handler: ' + self.localbox_client.label)
        event_handler = LocalBoxEventHandler(self.localbox_client)
        observer = Observer()
        observer.schedule(event_handler, SyncsController().get(self.localbox_client.label).path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
