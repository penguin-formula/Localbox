import pickle
from logging import getLogger
from os.path import exists, isfile

from loxcommon import os_utils
from sync.defaults import LOCALBOX_OPENFILES
from sync.notif.notifs import Notifs


def add(filename):
    getLogger(__name__).debug('adding %s to opened files' % filename)
    openfiles_list = load()
    if not openfiles_list or isinstance(openfiles_list, list):
        openfiles_list = dict()
    if not filename in openfiles_list and exists(filename):
        openfiles_list[filename] = os_utils.hash_file(filename)
    save(openfiles_list)
    Notifs().openfilesCtrl()


def remove(filesystem_path):
    openfiles_list = load()
    if filesystem_path in openfiles_list.keys():
        del openfiles_list[filesystem_path]
        save(openfiles_list)
    elif isfile(filesystem_path):
        getLogger(__name__).error('%s was not found in the list of opened files' % filesystem_path)
    Notifs().openfilesCtrl()


def save(openfiles_list):
    with open(LOCALBOX_OPENFILES, 'wb') as f:
        pickle.dump(openfiles_list, f)
    getLogger(__name__).debug('saved opened files: %s' % openfiles_list)


def load():
    try:
        with open(LOCALBOX_OPENFILES, 'rb') as f:
            old_openfiles_list = pickle.load(f)
            getLogger(__name__).debug('found this opened files: %s' % old_openfiles_list)
            openfiles_list = {k: v for k, v in old_openfiles_list.items() if exists(k)}
    except (IOError, AttributeError) as ex:
        getLogger(__name__).error(ex)
        openfiles_list = dict()

    save(openfiles_list)
    return openfiles_list


def remove_all(*args, **kwargs):
    getLogger(__name__).info('removing all decrypted files')
    remove_these = filter(lambda fp: os_utils.shred(fp), load())
    map(lambda fp: remove(fp), remove_these)


def get_hash(filesystem_path):
    try:
        return load()[filesystem_path]
    except KeyError:
        return None
