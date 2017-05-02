"""
This module declares a set of functions that send new notifications to the
NotifHandler. They are just simple wrappers around the possible messages that
NotifHandler expects to see.
"""

import zmq


class Notifs(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Notifs, cls).__new__(cls)

            # Creates a zmq context and connects
            cls.context = zmq.Context.instance()
            cls.push_sock = cls.context.socket(zmq.PUSH)
            cls.push_sock.connect("ipc:///tmp/loxclient")

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
    # Request File Operations
    # =========================================================================

    def openFileReq(self, data_dic):
        """
        NOT IMPLEMENTED

        Request a file of a specific box to be opena

        @param data_dic The data dictionary containing the information
        necessary to identify the file to be open
        """

        self._send({ 'code': 500, 'data_dic': data_dic })
