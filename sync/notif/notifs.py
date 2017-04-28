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
            cls.context = zmq.Context()
            cls.socket = cls.context.socket(zmq.PUSH)
            cls.socket.connect("tcp://127.0.0.1:8000")

        return cls.instance

    def _send(self, msg):
        self.socket.send_json(msg)

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
