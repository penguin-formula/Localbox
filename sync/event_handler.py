import time
from ConfigParser import NoOptionError
from logging import getLogger
from threading import Thread
from urllib2 import URLError

from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

from sync.controllers.localbox_ctrl import SyncsController
from sync.localbox import LocalBox


class LocalBoxEventHandler(LoggingEventHandler):
    """Logs all the events captured."""


def get_event_runners():
    """

    """

    runners = []
    for sync_item in SyncsController():
        try:
            url = sync_item.url
            label = sync_item.label
            localbox_client = LocalBox(url, label)

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
        event_handler = LocalBoxEventHandler()
        observer = Observer()
        observer.schedule(event_handler, SyncsController().get(self.localbox_client.label).path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
