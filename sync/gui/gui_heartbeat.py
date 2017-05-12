"""
"""

import threading
from logging import getLogger
import json

import wx
import zmq

from sync.notif import notifs_util

NewGuiHeartbeatBind = wx.NewEventType()
EVT_NewGuiHeartbeat = wx.PyEventBinder(NewGuiHeartbeatBind, 1)

class NewGuiHeartbeatEvent(wx.PyCommandEvent):
    """
    TODO
    """

    def __init__(self, etype, eid, msg):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.msg = msg

    def getMsg(self):
        return self.msg


class GuiHeartbeat(threading.Thread):
    """
    TODO
    """

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self._parent = parent
        self.context = zmq.Context.instance()

    def run(self):
        self.notifs_sub_hearthbeat = self.context.socket(zmq.SUB)
        self.notifs_sub_hearthbeat.setsockopt(zmq.SUBSCRIBE, notifs_util.zmq_gui_heartbeat)
        self.notifs_sub_hearthbeat.connect(notifs_util.zmq_ipc_pub)

        while True:
            contents = self.notifs_sub_hearthbeat.recv()
            msg_str = notifs_util.demogrify(contents)
            msg = json.loads(msg_str)

            if "cmd" in msg and msg["cmd"] == "stop":
                break

            evt = NewGuiHeartbeatEvent(NewGuiHeartbeatBind, -1, msg)
            wx.PostEvent(self._parent, evt)
