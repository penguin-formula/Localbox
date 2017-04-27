import threading
from logging import getLogger
from json import loads

import wx
import zmq

NewNotifsBind = wx.NewEventType()
EVT_NewNotifs = wx.PyEventBinder(NewNotifsBind, 1)

class NewNotifsEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, msg):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.msg = msg

    def getMsg(self):
        return self.msg


class NewNotifsThread(threading.Thread):
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

            evt = NewNotifsEvent(NewNotifsBind, -1, msg)
            wx.PostEvent(self._parent, evt)
