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

    def syncHeartbeatUp(self, label):
        """
        TODO
        """

        self._send({ 'code': 302, 'label': label })

    def syncHeartbeatDown(self, label):
        """
        TODO
        """

        self._send({ 'code': 303, 'label': label })

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
        self._send({ 'code': 500, 'data_dic': data_dic })

        # Wait for the answer
        contents = self.notifs_sub.recv()
        msg_str = notifs_util.demogrify(contents)
        msg = json.loads(msg_str)

        return msg['file_name']
