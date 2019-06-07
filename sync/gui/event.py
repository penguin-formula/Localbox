import threading
import wx

loxEVT_POPULATE = wx.NewEventType()
EVT_POPULATE = wx.PyEventBinder(loxEVT_POPULATE, 1)


class PopulateEvent(wx.PyCommandEvent):
    """
    Event to signal that a value is ready.

    """

    def __init__(self, etype, eid, value):
        """
        Creates the event object.

        """
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value

    def get_value(self):
        return self._value


class PopulateThread(threading.Thread):
    def __init__(self, parent, func):
        """

        :param parent: The gui object that should receive the value
        :param func: Function to be called to retrieve the value
        """
        threading.Thread.__init__(self)
        self._parent = parent
        self._func = func

    def run(self):
        """
        Overrides Thread.run. Don't call this directly its called internally
        when you call Thread.start().
        """
        value = self._func()
        evt = PopulateEvent(loxEVT_POPULATE, -1, value)
        wx.PostEvent(self._parent, evt)
        if hasattr(self._parent, 'btn_refresh'):
            self._parent.btn_refresh.Enable()
            self._parent.parent.loading_gif.Stop()
