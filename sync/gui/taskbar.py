"""
Module managing a Windows Taskbar icon
"""
try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except:
    from http.server import BaseHTTPRequestHandler, HTTPServer
from logging import getLogger
from threading import Thread, Event

import json
import pickle
import os
from os.path import exists

import sync.gui.gui_utils as gui_utils
from sync.controllers.localbox_ctrl import SyncsController
from sync.controllers.login_ctrl import LoginController
from sync.defaults import LOCALBOX_SITES_PATH
from sync.gui.gui_wx import Gui, LocalBoxApp
from sync.gui.gui_notifs import GuiNotifs, EVT_NewPopup, EVT_NewHeartbeat, EVT_NewOpenfileCtrl
from sync.__version__ import VERSION_STRING
from sync.localbox import LocalBox
from sync.notif.notifs import Notifs
import sync.controllers.openfiles_ctrl as openfiles_ctrl
from loxcommon import os_utils
from sync import defaults

try:
    import wx
except ImportError:
    getLogger(__name__).critical("Cannot import wx")

try:
    from wx import TaskBarIcon, ID_ANY, EVT_TASKBAR_LEFT_DOWN, EVT_TASKBAR_RIGHT_DOWN
except:
    from wx.adv import TaskBarIcon, EVT_TASKBAR_LEFT_DOWN, EVT_TASKBAR_RIGHT_DOWN
    from wx.stc import ID_ANY

try:
    from wx import NotificationMessage as wxNotif
except:
    from wx.adv import NotificationMessage as wxNotif

try:
    from ConfigParser import ConfigParser  # pylint: disable=F0401,E0611
    from urllib2 import URLError
except ImportError:
    from configparser import ConfigParser  # pylint: disable=F0401,E0611
    from urllib.error import URLError  # pylint: disable=F0401,W0611,E0611


class LocalBoxIcon(TaskBarIcon):
    """
    Class for managing a Windows taskbar icon
    """
    icon_path = None

    def __init__(self, main_syncing_thread, sites=None, observers=None):
        TaskBarIcon.__init__(self)
        if sites is not None:
            self.sites = sites
        else:
            self.sites = []

        if observers is not None:
            self.observers = observers
        else:
            self.observers = []

        # The purpose of this 'frame' is to keep the mainloop of wx alive
        # (which checks for living wx thingies)
        self.frame = Gui(None, main_syncing_thread.waitevent, main_syncing_thread)
        self.frame.Show(True)
        self._main_syncing_thread = main_syncing_thread

        self.gui_notif = GuiNotifs(self)
        self.gui_notif.start()

        # menu items
        self.item_start_gui = None
        self.item_sync = None
        self.item_sync_stop = None
        self.item_del = None
        self.item_close = None

        # Set the image
        self.taskbar_icon = wx.Icon(gui_utils.iconpath())

        self.SetIcon(self.taskbar_icon, gui_utils.MAIN_TITLE)

        # bind some events
        self.Bind(EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarClick)
        self.Bind(EVT_TASKBAR_RIGHT_DOWN, self.OnTaskBarClick)
        self.Bind(EVT_NewPopup, self.OnNewGuiNotifs)
        self.Bind(EVT_NewHeartbeat, self.on_new_gui_heartbeat)
        self.Bind(EVT_NewOpenfileCtrl, self.on_new_openfile_ctrl)

    def start_gui(self, event):  # pylint: disable=W0613
        """
        start the graphical user interface for configuring localbox
        """
        getLogger(__name__).debug("Starting GUI")
        self.frame.Show()
        self.frame.Raise()

    def start_sync(self, wx_event):  # pylint: disable=W0613
        """
        tell the syncer the system is ready to sync
        """
        self._main_syncing_thread.sync()

    def stop_sync(self, wx_event):
        self._main_syncing_thread.stop()

    def delete_decrypted(self, event=None):
        openfiles_ctrl.remove_all()

    def create_popup_menu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        getLogger(__name__).debug("create_popup_menu")
        menu = wx.Menu()

        # settings item
        self.item_start_gui = menu.Append(ID_ANY, _("Settings"))

        # sync item
        menu.AppendSeparator()
        if self._main_syncing_thread.is_running():
            self.item_sync = menu.Append(ID_ANY, _("Sync in progress"))
            menu.Enable(id=self.item_sync.Id, enable=False)
        else:
            self.item_sync = menu.Append(ID_ANY, _("Force Sync"))
            # only enable option if label list is not empty
            menu.Enable(id=self.item_sync.Id, enable=len(SyncsController().list) > 0)

        # stop item
        self.item_sync_stop = menu.Append(ID_ANY, _('Stop'))
        menu.Enable(id=self.item_sync_stop.Id, enable=self._main_syncing_thread.is_running())

        # delete decrypted item
        menu.AppendSeparator()
        self.item_del = menu.Append(ID_ANY, _("Delete decrypted files"))
        if not openfiles_ctrl.load():
            menu.Enable(id=self.item_del.Id, enable=False)

        # version item
        menu.AppendSeparator()
        item_version = menu.Append(ID_ANY, _("Version: %s") % VERSION_STRING)
        menu.Enable(id=item_version.Id, enable=False)

        # quit item
        menu.AppendSeparator()
        self.item_close = menu.Append(ID_ANY, _("Quit"))

        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.item_close.Id)
        self.Bind(wx.EVT_MENU, self.start_gui, id=self.item_start_gui.Id)
        self.Bind(wx.EVT_MENU, self.start_sync, id=self.item_sync.Id)
        self.Bind(wx.EVT_MENU, self.stop_sync, id=self.item_sync_stop.Id)
        self.Bind(wx.EVT_MENU, self.delete_decrypted, id=self.item_del.Id)

        return menu

    def OnTaskBarActivate(self, event):  # pylint: disable=W0613
        """required function for wxwidgets doing nothing"""
        pass

    def OnTaskBarClose(self, event):  # pylint: disable=W0613
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        self.frame.Close()
        self.delete_decrypted()

        for observer in self.observers:
            observer.stop()
            observer.join()

        Notifs().stop()

        self.Destroy()

        app = wx.GetApp()
        app.ExitMainLoop()

    def OnTaskBarClick(self, event):  # pylint: disable=W0613
        """
        Create the taskbar-click menu
        """
        menu = self.create_popup_menu()
        self.PopupMenu(menu)
        # menu.Destroy()

    def OnNewGuiNotifs(self, event):
        getLogger(__name__).debug("New GUI notif taskbar.py")
        msg = event.getMsg()
        wxNotif(msg["title"], msg["message"]).Show()

    def on_new_gui_heartbeat(self, event):
        getLogger(__name__).debug("New GUI hearbeat taskbar.py")
        msg = event.getMsg()
        self.frame.on_new_gui_heartbeat(msg)

    def on_new_openfile_ctrl(self, event):
        self.frame.on_new_openfile_ctrl()


def is_first_run():
    return not exists(LOCALBOX_SITES_PATH)


def taskbarmain(main_syncing_thread, sites=None, observers=None):
    """
    main function to run to get the taskbar started
    """
    try:
        app = LocalBoxApp(False)

        icon = LocalBoxIcon(main_syncing_thread, sites=sites, observers=observers)

        if is_first_run():
            icon.start_gui(None)

        app.MainLoop()
    except SystemExit:
        os._exit(0)
