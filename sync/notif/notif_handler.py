import os
from logging import getLogger
from threading import Thread, Lock, Event

import zmq


class NotifHandler(Thread):
    """
    """

    def __init__(self):
        Thread.__init__(self)

        self.runnning = False

    def run(self):
        # Start socket for pulling new notifications
        self.context = zmq.Context()
        self.consumer = self.context.socket(zmq.PULL)
        self.consumer.bind("tcp://127.0.0.1:8000")

        # start socket to publish new processed notification
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://127.0.0.1:8001")

        getLogger(__name__).debug("notifications thread starting")

        # Loop until the thread is stopped
        self.running = True
        while self.running:
            msg = self.consumer.recv_json()

            if msg['code'] == 200:
                self._publish({ "title": "LocalBox", "message": "Sync Started" })

            elif msg['code'] == 201:
                self._publish({ "title": "LocalBox", "message": "Sync Stopped" })

            elif msg['code'] == 100:
                getLogger(__name__).debug("stopping notifications thread")
                self._publish({ "cmd": "stop" })
                self.running = False

        getLogger(__name__).debug("notifications thread stopped")

    def _publish(self, msg):
        self.publisher.send_json(msg)
