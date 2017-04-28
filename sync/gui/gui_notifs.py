"""
This module declares handles processed notifications that are sent from the
NotifHandler module to the GUI. Notifications in the GUI are handled by
declaring a thread, from class GuiNotifs, which waits on new notifications from
the NotifHandler module. When a new notification arrives, the event
EVT_NewGuiNotifs is triggered.
"""

import threading
from logging import getLogger
from json import loads

import wx
import zmq

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

    def run(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        self.socket.setsockopt(zmq.SUBSCRIBE, "")
        self.socket.connect("tcp://localhost:8001")

        while True:
            msg = self.socket.recv_json()

            if "cmd" in msg and msg["cmd"] == "stop":
                break

            evt = NewGuiNotifsEvent(NewGuiNotifsBind, -1, msg)
            wx.PostEvent(self._parent, evt)
