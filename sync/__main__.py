"""
main module for localbox sync
"""
from threading import Lock
from getpass import getpass
from logging import getLogger
from logging import StreamHandler
from logging import FileHandler
from threading import Thread
from os.path import join
from os.path import expandvars
from os import makedirs
from os.path import isdir
from os.path import dirname
from .defaults import KEEP_RUNNING
from .defaults import SITESINI_PATH
from .defaults import SYNCINI_PATH
from .defaults import LOG_PATH
from sys import stdout

from .auth import Authenticator
from .auth import AuthenticationError
from .localbox import LocalBox
from .syncer import Syncer
from time import sleep
from .taskbar import taskbarmain
try:
    from ConfigParser import ConfigParser
    from ConfigParser import NoOptionError
    from ConfigParser import NoSectionError
except ImportError:
    from configparser import ConfigParser  # pylint: disable=F0401,W0611
    # pylint: disable=F0401
    from configparser import NoOptionError
    from configparser import NoSectionError
    raw_input = input #pylint: disable=W0622,C0103

class SyncRunner(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                 verbose=None, syncer=None):
        Thread.__init__(self, group=group, target=target, name=name, args=args,
                        kwargs=kwargs, verbose=verbose)
        self.setDaemon(True)
        self.syncer = syncer
        self.lock = Lock()
        print("SyncRunner started")

    def run(self):
        global KEEP_RUNNING
        print("running \"run\"")
        while(KEEP_RUNNING):
            self.lock.acquire()
            # TODO: Direction
            self.syncer.syncsync()
            self.lock.release()


def stop_running():
    global KEEP_RUNNING
    KEEP_RUNNING = False

def main():
    """
    temp test function
    """
    print "running main"
    location = SITESINI_PATH
    configparser = ConfigParser()
    configparser.read(location)
    sites = []
    for section in configparser.sections():
        try:
            url = configparser.get(section, 'url')
            path = configparser.get(section, 'path')
            direction = configparser.get(section, 'direction')
            localbox = LocalBox(url)
            authenticator = Authenticator(localbox.get_authentication_url(), section)
            localbox.add_authenticator(authenticator)
            if not authenticator.has_client_credentials():
                getLogger('main').info("Don't have client credentials for this host yet."
                      " We need to log in with your data for once.")
                username = raw_input("Username: ")
                password = getpass("Password: ")
                try:
                    authenticator.init_authenticate(username, password)
                except AuthenticationError:
                    getLogger.info("authentication data incorrect. Skipping entry.")
            else:
                syncer = Syncer(localbox, path, direction)
                sites.append(syncer)
        except NoOptionError as error:
            string = "Skipping '%s' due to missing option '%s'" % (section, error.option)
            getLogger('main').info(string)
    configparser.read(SYNCINI_PATH)
    try:
        delay = int(configparser.get('sync', 'delay'))
    except (NoSectionError, NoOptionError):
        delay = 3600
    while KEEP_RUNNING:
        for syncer in sites:
            runner = SyncRunner(syncer=syncer)
            runner.run()
            #if syncer.direction == 'up':
            #    syncer.upsync()
            #if syncer.direction == 'down':
            #    syncer.downsync()
            #if syncer.direction == 'sync':
            #    syncer.syncsync()
        sleep(delay)

if __name__ == '__main__':
    if not isdir(dirname(LOG_PATH)):
        makedirs(dirname(LOG_PATH))
    handlers = [StreamHandler(stdout), FileHandler(LOG_PATH)]
    for name in 'main', 'database', 'auth', 'localbox':
        logger = getLogger(name)
        for handler in handlers:
            logger.addHandler(handler)
        logger.setLevel(5)
        logger.info("Starting Localbox Sync logger " + name)

    MAIN = Thread(target=main)
    MAIN.daemon = True
    MAIN.start()

    taskbarmain()
