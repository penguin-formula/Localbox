'''
Description:

    Module for lox-client configuration. Not a class so not needed to
    instantiate throughout the application. Globally loads or saves the client
    configuration with the load() and save() functions. The configuration
    can be accessed as a dict of session settings through the variable named
    settings. Each session entry in the dict is again a dict of name/value
    pairs. At both levels all dict oprations apply.

Usage:

    import config

    config.load()
    user = config.settings['localhost']['username']
    config.settings['localhost']['username'] = 'newuser'
    config.save()
    if 'local_dir'in config.settings['localhost'].changed():
        # do something because changeing the directory
        # without flushing the cache is like 'rm -r *'

'''

import sys
import os
import ConfigParser
import collections

from lox.error import LoxError


DEFAULT = {
            "local_dir" : "",
            "lox_url" : "",
            "auth_type" : "localbox",
            "username" : "",
            "password" : "",
            "interval" : "300",
            "log_level" : "error"
          }

class SectionSettings(collections.MutableMapping):
    '''
    A dictionary that keeps track of changes
    Deletion of keys is not supported
    '''
    def __init__(self):
        '''
        Initialize with default settings
        '''
        self._store = dict()
        self._changed = set()
        self.update(dict(DEFAULT))  # use the free update to set keys
        self.confirm()

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        '''
        Keep track of changed settings
        '''
        self._store[key] = value
        self._changed.add(key)

    def __delitem__(self, key):
        pass

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def changed(self):
        '''
        Return changed settings
        '''
        return self._changed

    def confirm(self):
        '''
        Accept changed settings
        '''
        self._changed = set()

def load():
    '''
    Load the config file as the current settings,
    all previous settings are flushed
    '''
    global settings
    settings = dict()
    conf_dir = os.environ['HOME']+'/.lox'
    if not os.path.isdir(conf_dir):
        os.mkdir(conf_dir)
    if not os.path.isfile(conf_dir+"/lox-client.conf"):
        f = open(conf_dir+"/lox-client.conf",'w+')
        f.write(";empty config file")
        f.write(os.linesep)
        f.close()
    path = os.environ['HOME']+'/.lox/lox-client.conf'
    config = ConfigParser.RawConfigParser()
    config.read(path)
    for session in config.sections():
        settings[session] = SectionSettings()
        for key,value in config.items(session):
            settings[session][key] = value

def save():
    '''
    Load the current settings to the config file
    '''
    global settings
    conf_dir = os.environ['HOME']+'/.lox'
    if not os.path.isdir(conf_dir):
        os.mkdir(conf_dir)
    path = os.environ['HOME']+'/.lox/lox-client.conf'
    config = ConfigParser.RawConfigParser()
    for session,d in settings.iteritems():
        config.add_section(session)
        for item,value in d.iteritems():
            config.set(session,item,value)
    f = open(path, 'wb')
    config.write(f)
    f.close()

settings = dict()
load()

