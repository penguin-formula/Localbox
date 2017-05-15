"""
This module declares a set of functions that send new notifications to the
NotifHandler. They are just simple wrappers around the possible messages that
NotifHandler expects to see.
"""

import json

import zmq

from sync.notif import notifs_util


class Notifs(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Notifs, cls).__new__(cls)

            # Creates a zmq context and connects
            cls.context = zmq.Context.instance()
            cls.push_sock = cls.context.socket(zmq.PUSH)
            cls.push_sock.connect(notifs_util.zmq_ipc_push)

        return cls.instance

    def _send(self, msg):
        self.push_sock.send_json(msg)

    # =========================================================================
    # Thread Operations
    # =========================================================================

    def stop(self):
        """
        Tell the NotifHandler thread to stop. Used when shutting down
        """

        self._send({ 'code': 100 })

    # =========================================================================
    # Syncs
    # =========================================================================

    def syncStarted(self):
        """
        When a synchronization process starts
        """

        self._send({ 'code': 300 })

    def syncEnded(self):
        """
        When a synchronization process ends
        """

        self._send({ 'code': 301 })

    # =========================================================================
    # File Changes
    # =========================================================================

    def uploadedFile(self, file_name):
        """
        When a file is uploaded

        @param file_name The name of the uploaded file
        """

        self._send({ 'code': 400, 'file_name': file_name })

    def deletedFile(self, file_name):
        """
        When a file is deleted

        @param file_name The name of the deleted file
        """

        self._send({ 'code': 401, 'file_name': file_name })

    # =========================================================================
    # Heartbeat
    # =========================================================================

    def reqHeartbeats(self, labels, force_gui_notif=False):
        """
        Send a request to do a heartbeat right now to a specific set of labels.
        If the list of labels is empty, the heartbeat will be a full heartbeat
        """

        self._send({ 'code':            500,
                     'labels':          labels,
                     'force_gui_notif': force_gui_notif })

    def syncHeartbeatUp(self, label, force_gui_notif=False):
        """
        Notify that sync with the given label is up
        """

        self._send({ 'code': 501, 'label': label, 'force_gui_notif': force_gui_notif })

    def syncHeartbeatDown(self, label, force_gui_notif=False):
        """
        Notify that sync with the given label is down
        """

        self._send({ 'code': 502, 'label': label, 'force_gui_notif': force_gui_notif })

    # =========================================================================
    # Notification from open file controller
    # =========================================================================

    def openfilesCtrl(self):
        self._send({ 'code': 600 })

    # =========================================================================
    # Request File Operations
    # =========================================================================

    def openFileReq(self, data_dic):
        """
        Request a file of a specific box to be open. Returns the name of the
        opened file

        @param data_dic The data dictionary containing the information
        necessary to identify the file to be open
        """

        # Subscribe just for this file
        self.notifs_sub = self.context.socket(zmq.SUB)

        self.notifs_sub.setsockopt(zmq.SUBSCRIBE, notifs_util.zmq_file_op_notif)
        self.notifs_sub.connect(notifs_util.zmq_ipc_pub)

        # Send request
        self._send({ 'code': 700, 'data_dic': data_dic })

        # Wait for the answer
        contents = self.notifs_sub.recv()
        msg_str = notifs_util.demogrify(contents)
        msg = json.loads(msg_str)

        return msg['file_name']
