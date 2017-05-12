"""
This module declares handles processed notifications that are sent from the
NotifHandler module to the GUI. Notifications in the GUI are handled by
declaring a thread, from class GuiNotifs, which waits on new notifications from
the NotifHandler module. When a new notification arrives, the event
EVT_NewGuiNotifs is triggered.
"""

import threading
from logging import getLogger
import json

import wx
import zmq

from sync.notif import notifs_util

NewGuiNotifsBind = wx.NewEventType()
EVT_NewGuiNotifs = wx.PyEventBinder(NewGuiNotifsBind, 1)

class NewGuiNotifsEvent(wx.PyCommandEvent):
    """
    New GUI notifications event. This event is triggered whenever new
    notifications arrive from the NotifsHandler module.

    This event has the `msg` attribute which is a dictionary like:

        { "title": "Title of Notification",
          "message": "Message of the notification"
        }

    The dictionary is accessible with method `getMsg`.
    """

    def __init__(self, etype, eid, msg):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.msg = msg

    def getMsg(self):
        return self.msg


class GuiNotifs(threading.Thread):
    """
    Thread which waits for new notifications from NotifHandler and triggers the
    event to display said notifications
    """

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self._parent = parent
        self.context = zmq.Context.instance()

    def run(self):
        self.notifs_sub_gui = self.context.socket(zmq.SUB)
        self.notifs_sub_gui.setsockopt(zmq.SUBSCRIBE, notifs_util.zmq_gui_notif)
        self.notifs_sub_gui.connect(notifs_util.zmq_ipc_pub)

        while True:
            contents = self.notifs_sub_gui.recv()
            msg_str = notifs_util.demogrify(contents)
            msg = json.loads(msg_str)

            if "cmd" in msg and msg["cmd"] == "stop":
                break

            evt = NewGuiNotifsEvent(NewGuiNotifsBind, -1, msg)
            wx.PostEvent(self._parent, evt)
