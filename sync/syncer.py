import os
from logging import getLogger
from os import listdir
from os import makedirs
from os import remove
from os import sep
from os import utime
from os.path import dirname
from os.path import exists
from os.path import isdir
from os.path import join
from shutil import rmtree
from threading import Thread, Lock, Event
from time import sleep
from time import time

try:
    from ConfigParser import ConfigParser, NoSectionError, NoOptionError
except:
    from configparser import ConfigParser, NoSectionError, NoOptionError

try:
    from urllib2 import URLError
except:
    from urllib.error import URLError

from loxcommon import os_utils
from sync import defaults, SYNCINI_PATH
from sync.controllers.localbox_ctrl import SyncsController
from sync.controllers.login_ctrl import LoginController
from sync.defaults import SITESINI_PATH
from sync.localbox import LocalBox
from sync.profiling import profile
from .defaults import OLD_SYNC_STATUS
from .metavfs import MetaVFS


class Syncer(object):
    def __init__(self, localbox_instance, file_root_path, direction, name=None):
        self.localbox = localbox_instance
        self.name = name
        self.filepath = file_root_path.replace('/', sep)
        self.localbox_metadata = None
        self.filepath_metadata = None
        self.direction = direction
        self._stop_event = None

    @property
    def stop_event(self):
        return self._stop_event

    @stop_event.setter
    def stop_event(self, value):
        self._stop_event = value

    def _should_stop_sync(self):
        if self._stop_event is not None and self._stop_event.is_set():
            raise StopSyncException

    def get_file_path(self, metavfs_entry):
        """
        System local filename
        :param metavfs_entry:
        :return:
        """
        path = metavfs_entry.path.split('/')
        return join(self.filepath, *path)

    def populate_localbox_metadata(self, path='/', parent=None):
        self._should_stop_sync()

        node = self.localbox.get_meta(path)
        getLogger(__name__).debug('populate_localbox_metadata node: %s' % node)
        modtime = node['modified_at']
        getLogger(__name__).debug('%s remote modification time: %s' % (path, modtime))
        vfsnode = MetaVFS(modtime, node['path'], node['is_dir'])
        for child in node['children']:
            self.populate_localbox_metadata(child['path'], parent=vfsnode)
        if parent is None:
            self.localbox_metadata = vfsnode
        else:
            getLogger(__name__).debug("parent %s gets child %s" % (parent, vfsnode))
            parent.add_child(vfsnode)

    def populate_filepath_metadata(self, path='/', parent=None):
        self._should_stop_sync()

        path = path.lstrip('.').rstrip("/\\")
        if path == '':
            fs_path = self.filepath
        else:
            fs_path = join(self.filepath, path)
        getLogger(__name__).info('processing "%s" transformed to "%s"' % (path, fs_path))
        is_dir = isdir(fs_path)

        path_dec = os_utils.remove_extension(path, defaults.LOCALBOX_EXTENSION)
        fs_path_dec = os_utils.remove_extension(fs_path, defaults.LOCALBOX_EXTENSION)
        if is_dir:
            modtime = os.path.getmtime(fs_path)
            vfsnode = MetaVFS(modtime, path_dec, is_dir)
            for entry in listdir(fs_path):
                self.populate_filepath_metadata(join(path, entry), parent=vfsnode)
        else:
            if not path.endswith(defaults.LOCALBOX_EXTENSION):
                if not os.path.exists(fs_path + defaults.LOCALBOX_EXTENSION):
                    modtime = os.path.getmtime(fs_path)
                else:
                    return
            else:
                if os.path.exists(fs_path_dec):
                    modtime_enc = os.path.getmtime(fs_path)
                    modtime_dec = os.path.getmtime(fs_path_dec)
                    modtime = modtime_dec if modtime_dec > modtime_enc else modtime_enc
                else:
                    modtime = os.path.getmtime(fs_path)

            vfsnode = MetaVFS(modtime, path_dec, is_dir)

        if parent is None:
            self.filepath_metadata = vfsnode
        else:
            parent.add_child(vfsnode)

    def mkdir(self, metavfs):
        localfilename = self.get_file_path(metavfs)
        makedirs(localfilename)

    def delete(self, path):
        # join(self.filepath, path[1:])
        fs_path = self.get_file_path(path)
        if isdir(fs_path):
            rmtree(fs_path)
        else:
            try:
                # remove(fs_path)
                remove(fs_path + defaults.LOCALBOX_EXTENSION)
            except OSError:
                getLogger(__name__).info("Already deleted " + fs_path)

    def download(self, path):
        contents = self.localbox.get_file(path)
        if contents is not None:
            localfilename_noext = join(self.filepath, path[1:])
            localfilename = localfilename_noext + defaults.LOCALBOX_EXTENSION
            # precreate folder if needed
            localdirname = dirname(localfilename)
            if not exists(localdirname):
                makedirs(localdirname)

            # save new encrypted file to disk
            getLogger(__name__).debug('Saving to disk: %s' % localfilename)
            localfile = open(localfilename, 'wb')
            localfile.write(contents)
            localfile.close()

            # delete old decrypted file
            if exists(localfilename_noext):
                os.remove(localfilename_noext)

            localfilepath = self.localbox_metadata.get_entry(path)
            modtime = localfilepath.modified_at
            utime(localfilename, (time(), modtime))
        else:
            getLogger(__name__).error('Failed to download %s' % path)

    @profile
    def syncsync(self):
        label = self.localbox.authenticator.label
        getLogger(__name__).info("Starting syncsync")

        # get passphrase
        getLogger(__name__).debug('waiting for passphrase, label=%s' % label)
        passphrase = LoginController().get_passphrase(label)
        while not passphrase:
            self._should_stop_sync()
            sleep(1)
            passphrase = LoginController().get_passphrase(label)

        getLogger(__name__).debug('got passphrase for label=%s' % label)

        self.localbox_metadata = None
        self.filepath_metadata = None
        self.populate_localbox_metadata(path='/', parent=None)
        self.populate_filepath_metadata(path='/', parent=None)

        full_tree = MetaVFS('0', '/', True, None)
        full_tree.add_paths(self.localbox_metadata)
        full_tree.add_paths(self.filepath_metadata)

        try:
            oldmetadata = self.filepath_metadata.load(
                OLD_SYNC_STATUS + self.name)
            full_tree.add_paths(oldmetadata)
        except (IOError, AttributeError) as error:
            getLogger(__name__).info(str(error) + " Using empty tree instead")
            oldmetadata = MetaVFS(path='/', modified_at=0)

        for metavfs in full_tree.gen():
            self._should_stop_sync()

            try:
                path = metavfs.path

                oldfile = oldmetadata.get_entry(path)
                localfile = self.filepath_metadata.get_entry(path)
                remotefile = self.localbox_metadata.get_entry(path)
                getLogger(__name__).debug(
                    "====Local %s, Remote %s, Old %s ====", localfile, remotefile, oldfile)

                # hammer time :(
                # to fixed directory deletion issue
                if localfile is None and oldfile is not None and remotefile is not None:
                    oldfile.modified_at = remotefile.modified_at

                # if remotefile == oldfile and self.get_file_path(metavfs)is None:
                if remotefile == oldfile and localfile is None:
                    getLogger(__name__).info("Deleting remote %s", path)
                    self.localbox.delete(metavfs)
                    continue
                # if localfile == oldfile and self.get_url_path(metavfs) is None:
                if localfile == oldfile and remotefile is None:
                    getLogger(__name__).info("Deleting local %s", path)
                    self.delete(metavfs)
                    continue

                newest = MetaVFS.newest(oldfile, localfile, remotefile)

                if newest == oldfile and newest is not None:
                    getLogger(__name__).info(
                        "Skipping %s because all files are older then the previous file", newest.path)
                    continue

                newest = MetaVFS.newest(localfile, remotefile)

                localpath = self.get_file_path(metavfs)
                if newest == localfile and os.path.exists(localpath):
                    if not isdir(self.get_file_path(metavfs)):
                        getLogger(__name__).info('Starting upload %s:  %s', path, localpath)
                        self.localbox.upload_file(path, localpath, passphrase)
                    elif path != '/' and path not in self.localbox_metadata.get_paths():
                        self.localbox.create_directory(path)
                    continue
                if newest == remotefile:
                    getLogger(__name__).info("%s is_dir: %s", metavfs.path, metavfs.is_dir)
                    if not metavfs.is_dir:
                        getLogger(__name__).info("Downloading %s", newest.path)
                        self.download(path)
                    else:
                        if not isdir(self.get_file_path(metavfs)):
                            self.mkdir(metavfs)

                    continue
            except Exception as error:
                getLogger(__name__).exception("Problem '%s' with file %s; continuing", error, metavfs.path)
        self.populate_filepath_metadata(path='./', parent=None)
        self.filepath_metadata.save(OLD_SYNC_STATUS + self.name)


class SyncRunner(Thread):
    """
    Thread responsible for synchronizing between the client and one server.
    """

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, syncer=None):
        Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        self.setDaemon(True)
        self.syncer = syncer
        self.lock = Lock()

    def run(self):
        """
        Function that runs one iteration of the synchronization
        """
        try:
            getLogger(__name__).info("SyncRunner " + self.name + " started")
            self.lock.acquire()
            self.syncer.syncsync()
            self.lock.release()
            getLogger(__name__).info("SyncRunner " + self.name + " finished")
        except StopSyncException:
            getLogger(__name__).fatal("SyncRunner " + self.name + " forced to finish")
            self.lock.release()

    @property
    def name(self):
        return 'th-' + self.syncer.name


    @property
    def stop_event(self):
        return self.syncer.stop_event

    @stop_event.setter
    def stop_event(self, value):
        self.syncer.stop_event = value


class MainSyncer(Thread):
    """

    """

    def __init__(self, event):
        """

        :param event: event to force synchronization
        """
        Thread.__init__(self)
        self._waitevent = event
        self._keep_running = True
        self._thread_pool = dict()
        self.daemon = True

    def run(self):
        location = SITESINI_PATH
        configparser = ConfigParser()
        configparser.read(location)
        try:
            configparser.read(SYNCINI_PATH)
            try:
                delay = int(configparser.get('sync', 'delay'))
            except (NoSectionError, NoOptionError) as error:
                getLogger(__name__).warning("%s in '%s'", error.message, SYNCINI_PATH)
                delay = 3600
            while self.keep_running:
                getLogger(__name__).debug("starting loop")
                self.waitevent.set()
                for syncer in get_syncers():
                    runner = SyncRunner(syncer=syncer)
                    getLogger(__name__).debug("starting thread %s", runner.name)
                    syncer.stop_event = Event()
                    runner.start()
                    self.thread_pool[syncer.name] = runner
                    getLogger(__name__).debug("started thread %s", runner.name)
                for runner in self.thread_pool.values():
                    getLogger(__name__).debug("joining thread %s", runner.name)
                    runner.join()
                    runner.syncer.stop_event.clear()
                    getLogger(__name__).debug("joined thread %s", runner.name)

                self.waitevent.clear()
                getLogger(__name__).debug("Cleared Event")
                if self.waitevent.wait(delay):
                    getLogger(__name__).debug("stopped waiting")
                else:
                    getLogger(__name__).debug("done waiting")
        except Exception as error:  # pylint: disable=W0703
            getLogger(__name__).exception(error)

    def sync(self):
        if not self.waitevent.is_set():
            self.waitevent.set()
        else:
            getLogger(__name__).debug("Pressing start sync whilst sync in progress")

    def stop(self, label=None):
        if label is not None:
            stop_this_threads = [self._thread_pool[label]]
        else:
            stop_this_threads = self._thread_pool.values()

        map(lambda s: s.stop_event.set(), filter(lambda s: not s.stop_event.is_set(), stop_this_threads))

    def is_running(self):
        return self.waitevent.is_set()

    @property
    def waitevent(self):
        return self._waitevent

    @property
    def keep_running(self):
        return self._keep_running

    @property
    def thread_pool(self):
        return self._thread_pool

    def remove_runner(self, label):
        try:
            getLogger(__name__).debug('Removing runner: %s' % self._thread_pool[label])
            del self._thread_pool[label]
        except KeyError:
            getLogger(__name__).debug('No runner for label: %s' % label)


def get_syncers():
    """
    returns a list of Syncers. One per configured localbox instance.
    """
    syncs_ctrl = SyncsController()

    sites = []
    for sync_item in syncs_ctrl:
        getLogger(__name__).info("Syncing %s", sync_item.label)
        try:
            url = sync_item.url
            path = sync_item.path
            direction = sync_item.direction
            label = sync_item.label
            localbox_client = LocalBox(url, label, path)

            syncer = Syncer(localbox_client, path, direction, name=sync_item.label)
            sites.append(syncer)
        except NoOptionError as error:
            getLogger(__name__).exception(error)
            string = "Skipping '%s' due to missing option '%s'" % \
                     (sync_item, error.option)
            getLogger(__name__).info(string)
        except URLError as error:
            getLogger(__name__).exception(error)
            string = "Skipping '%s' because it cannot be reached" % \
                     (sync_item)
            getLogger(__name__).info(string)

    return sites


class StopSyncException(Exception):
    pass
