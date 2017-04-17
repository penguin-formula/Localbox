import pickle
from logging import getLogger

from sync.defaults import LOCALBOX_OPENFILES


def add(filename):
    getLogger(__name__).debug('adding %s to opened files' % filename)
    openfiles_list = load()
    if not openfiles_list:
        openfiles_list = list()
    if not filename in openfiles_list:
        openfiles_list.append(filename)
    save(openfiles_list)


def save(openfiles_list):
    with open(LOCALBOX_OPENFILES, 'wb') as f:
        pickle.dump(openfiles_list, f)
    getLogger(__name__).debug('saved opened files: %s' % openfiles_list)


def load():
    try:
        with open(LOCALBOX_OPENFILES, 'rb') as f:
            openfiles_list = pickle.load(f)
            getLogger(__name__).debug('found this opened files: %s' % openfiles_list)
            return openfiles_list
    except IOError:
        openfiles_list = list()
        save(openfiles_list)
        return None
