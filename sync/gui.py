from Tkinter import Tk
from Tkinter import Frame
from Tkinter import Label
from Tkinter import Entry
from Tkinter import Button
import tkFileDialog
from ttk import Combobox
from Tkinter import END
from ConfigParser import ConfigParser
from ConfigParser import NoOptionError
from os.path import isdir
from os.path import exists
from os.path import dirname
from os import makedirs
from logging import getLogger
from threading import Event

from .auth import Authenticator
from .auth import AuthenticationError
from .database import database_execute
from .defaults import SITESINI_PATH
from .localbox import LocalBox
from .defaults import LOCALE_PATH
from gettext import translation

class ConfigError(Exception):
    pass


class UsernameAndPasswordAsker(Tk):
    def __init__(self, authenticator, translator, parent=None):
        Tk.__init__(self, parent)
        self.title("Authentication Data")
        self.authenticator = authenticator

        Label(self, text="username").grid(row=0, column=0)
        self.username = Entry(self)
        self.username.grid(row=0, column=1)
        Label(self, text="password").grid(row=1, column=0)
        self.password = Entry(self, show="*")
        self.password.grid(row=1, column=1)
        self.button = Button(master=self, text="OK",
                             command=self.stop_window)
        self.button.grid(row=2)
        self.lock = Event()

    def stop_window(self):
        if self.authenticator.init_authenticate(self.username.get(),
                                                self.password.get()):
            self.lock.set()
            self.destroy()
        else:
            # TODO: window saying authentication failed
            pass

    def __call__(self):
        self.mainloop()


class Gui(Tk):
    def __init__(self, parent=None, configparser=None):
        Tk.__init__(self, parent)
        #todo: more languages stuff
        self.language =  translation('localboxsync', localedir=LOCALE_PATH, languages=['nl'], fallback=True)
        self.configs = []
        self.button = Button(text=self.language.lgettext("add localbox"),
                             command=self.add_new)
        self.button.grid(row=0, column=0)
        self.configparser = configparser
        self.lift()

    def add_entries(self, dataentryframe):
        self.configs.append(dataentryframe)
        position = len(self.configs)
        dataentryframe.grid(row=position, column=0)

    def add_new(self):
        dataentry = DataEntry(self, '', '', '', '', self.configparser, '')
        self.add_entries(dataentry)


def get_entry_fields(parent, text, value, row):
    label = Label(text=text, master=parent, justify="left")
    label.grid(column=0, row=row)
    entry = Entry(master=parent)
    entry.insert(0, value)
    entry.grid(column=1, row=row)
    return entry


class DataEntry(Frame):
    def getfile(self):
        result = tkFileDialog.askdirectory()
        self.local_path.delete(0, END)
        self.local_path.insert(0, result)

    def __init__(self, master=None, name=None, url=None, localdir=None,
                 direction=None, config=None, passphrase=None):
        Frame.__init__(self, master=master, relief="raised", borderwidth=2)
        self.master = master
        self.eventwindow = None
        self.direction = direction
        self.configparser = config
        self.orig_name = name
        self.site_name = get_entry_fields(self, master.language.lgettext("name box"), name, 0)
        self.localbox_url = get_entry_fields(self, master.language.lgettext("localbox url"), url, 1)
        self.local_path = get_entry_fields(self, master.language.lgettext("local path"), localdir, 2)
        self.passphrase = get_entry_fields(self, master.language.lgettext("passphrase"), passphrase, 3)
        self.lpbutton = Button(master=self, text=master.language.lgettext("folder select"),
                               command=self.getfile)
        self.lpbutton.grid(column=2, row=2)

        label = Label(text=master.language.lgettext("Up/Down/Sync"), master=self)
        label.grid(column=0, row=4)
        self.sync_direction = Combobox(master=self)
        self.sync_direction['values'] = ['up', 'down', 'sync']
        self.sync_direction.grid(column=1, row=4)

        self.savebutton = Button(master=self, text=master.language.lgettext("save"), command=self.save)
        self.savebutton.grid(row=5, column=2)
        self.authbutton = Button(master=self, text=master.language.lgettext("authenticeer"),
                                 command=self.authenticate)
        self.authbutton.grid(row=5, column=1)

    def save(self):
        try:
            if self.site_name.get() != self.orig_name:
                if (self.configparser.sections() is not None and
                        self.site_name.get() in self.configparser.sections()):
                    raise ConfigError("There is already a site with that name")
            if not isdir(self.local_path.get()):
                raise ConfigError("Share path needs to be a directory")
            if not self.sync_direction.get() in ['up', 'down', 'sync']:
                raise ConfigError("Direction needs to be up, down or sync")

            if self.site_name.get() != self.orig_name:
                self.configparser.remove_section(self.orig_name)
                self.configparser.add_section(self.site_name.get())
                if self.orig_name in self.configparser.sections():
                    sql = "update sites set site=? where site=?;"
                    database_execute(sql, (self.site_name.get(), self.orig_name))
                self.orig_name = self.site_name.get()

            self.configparser.set(self.site_name.get(), 'url',
                                  self.localbox_url.get())
            self.configparser.set(self.site_name.get(), 'path',
                                  self.local_path.get())
            self.configparser.set(self.site_name.get(), 'direction',
                                  self.sync_direction.get())
            self.configparser.set(self.site_name.get(), 'passphrase',
                                  self.passphrase.get())
            sitesini = SITESINI_PATH
            if not exists(dirname(sitesini)):
                makedirs(dirname(sitesini))
            with open(sitesini, 'wb') as configfile:
                self.configparser.write(configfile)
            self.eventwindow = Tk()
            self.eventwindow.title(self.master.language.lgettext("successwindowtitle"))
            conflabel = Label(text=self.master.language.lgettext("config safe success text"), master=self.eventwindow)
            conflabel.grid(row=0, column=0)
            confbutton = Button(master=self.eventwindow, text=self.master.language.lgettext("closebutton"),
                                command=self.close_exception_window)
            confbutton.grid(row=1, column=0)
        except ConfigError as error:
            self.eventwindow = Tk()
            self.eventwindow.title(self.master.language.lgettext("error"))
            Label(text=error.message, master=self.eventwindow).grid(row=0, column=0)
            errorbutton = Button(master=self.eventwindow, text=self.master.language.lgettext("close"),
                                 command=self.close_exception_window)
            errorbutton.grid(row=1, column=0)

    def close_exception_window(self):
        self.eventwindow.destroy()

    def authenticate(self):
        localbox = LocalBox(self.localbox_url.get())
        authurl = localbox.get_authentication_url()
        authenticator = Authenticator(authurl, self.site_name.get())
        if not authenticator.has_client_credentials():
            credentials = UsernameAndPasswordAsker(authenticator, self.language)
            credentials.__call__()
            credentials.lock.wait()
            # Show username/password field
            if authenticator.init_authenticate(credentials.username.get(),
                                               credentials.password.get()):
                print "succes"
            else:
                print "failure"
        else:
            try:
                authenticator.authenticate()
                print "credentials seem valid"
            except AuthenticationError:
                print "your credentials are invalidated"


def main():
    location = SITESINI_PATH

    configparser = ConfigParser()
    configparser.read(location)
    gui = Gui(configparser=configparser)
    gui.title(gui.language.lgettext('settingstitle'))
    sites = []
    for section in configparser.sections():
        try:
            dictionary = {'name': section,
                          'url': configparser.get(section, 'url'),
                          'path': configparser.get(section, 'path'),
                          'direction': configparser.get(section, 'direction')}
            sites.append(dictionary)
            passphrase = configparser.get(section, 'passphrase')
            dataentry = DataEntry(gui, section, dictionary['url'],
                                  dictionary['path'], dictionary['direction'],
                                  configparser, passphrase=passphrase)
            gui.add_entries(dataentry)

        except NoOptionError as error:
            string = "Skipping LocalBox '%s' due to missing option '%s'" % (section, error.option)
            getLogger('gui').debug(string)
    gui.mainloop()

if __name__ == "__main__":
    main()
