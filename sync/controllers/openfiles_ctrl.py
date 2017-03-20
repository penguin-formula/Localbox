import pickle
from logging import getLogger

from os.path import exists

from loxcommon import os_utils
from sync.defaults import LOCALBOX_OPENFILES


def add(filename):
    getLogger(__name__).debug('adding %s to opened files' % filename)
    openfiles_list = load()
    if not openfiles_list:
        openfiles_list = list()
    if not filename in openfiles_list:
        openfiles_list.append(filename)
    save(openfiles_list)


def remove(filesystem_path):
    openfiles_list = load()
    if filesystem_path in openfiles_list:
        os_utils.shred(filesystem_path)
        openfiles_list.remove(filesystem_path)
        save(openfiles_list)
    else:
        getLogger(__name__).error('%s was not found in the list of opened files' % filesystem_path)


def save(openfiles_list):
    pickle.dump(openfiles_list, open(LOCALBOX_OPENFILES, 'wb'))
    getLogger(__name__).debug('saved opened files: %s' % openfiles_list)


def load():
    try:
        with open(LOCALBOX_OPENFILES, 'rb') as f:
            old_openfiles_list = pickle.load(f)
            openfiles_list = list()
            getLogger(__name__).debug('found this opened files: %s' % old_openfiles_list)
            for opened_file in old_openfiles_list:
                if exists(opened_file):
                    openfiles_list.append(opened_file)
    except IOError:
        openfiles_list = list()

    save(openfiles_list)
    return openfiles_list
