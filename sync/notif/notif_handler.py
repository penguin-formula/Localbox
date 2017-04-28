import os
import time
from logging import getLogger
from threading import Thread, Lock, Event, Timer

import zmq


class NotifHandler(Thread):
    """
    """

    def __init__(self):
        Thread.__init__(self)

        self.runnning = False

        # For sync start and end (3xx)
        self.sync_start_delay = None
        self.sync_start_time = 0

        # For file upload (4xx)
        self.file_op_delay = None
        self.file_op_count_up = 0
        self.file_op_count_del = 0

    def run(self):
        # Start socket for pulling new notifications
        self.context = zmq.Context()
        self.consumer = self.context.socket(zmq.PULL)
        self.consumer.bind("tcp://127.0.0.1:8000")

        # Start socket to publish new processed notification
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://127.0.0.1:8001")

        getLogger(__name__).debug("notifications thread starting")

        # Loop until the thread is stopped
        self.running = True
        while self.running:
            msg = self.consumer.recv_json()
            code = msg['code']

            if code >= 100 and code < 200:
                self.handle_1xx(msg)

            elif code >= 300 and code < 400:
                self.handle_3xx(msg)

            elif code >= 400 and code < 500:
                self.handle_4xx(msg)

        getLogger(__name__).debug("notifications thread stopped")

    def _publish(self, msg):
        self.publisher.send_json(msg)

    def handle_1xx(self, msg):
        if msg['code'] == 100:
            getLogger(__name__).debug("stopping notifications thread")
            self._publish({ "cmd": "stop" })
            self.running = False

    def handle_3xx(self, msg):
        if msg['code'] == 300:
            def delay_sync_start():
                self._publish({ "title": "LocalBox", "message": "Sync Started" })

            if self.sync_start_delay is not None and self.sync_start_delay.is_alive():
                self.sync_start_delay.cancel()

            self.sync_start_delay = Timer(5, delay_sync_start)
            self.sync_start_delay.start()
            self.sync_start_time = time.time()

        elif msg['code'] == 301:
            if self.sync_start_delay is not None and self.sync_start_delay.is_alive():
                self.sync_start_delay.cancel()
                self._publish({ "title": "LocalBox", "message": "Sync Made" })

            elif time.time() > self.sync_start_time + 20:
                self._publish({ "title": "LocalBox", "message": "Sync Stopped" })

            # Else, don't show any messages

    def handle_4xx(self, msg):
        def file_op_up(file_name):
            self._publish({ "title": "LocalBox", "message": "Uploaded file {}".format(file_name) })

        def file_op_del(file_name):
            self._publish({ "title": "LocalBox", "message": "Deleted file {}".format(file_name) })

        def file_op_many_up(count):
            self._publish({ "title": "LocalBox", "message": "Uploaded {} files".format(count) })

        def file_op_many_down(count):
            self._publish({ "title": "LocalBox", "message": "Deleted {} files".format(count) })

        def file_op_changes(count):
            self._publish({ "title": "LocalBox", "message": "Changed {} files".format(count) })

        code = msg['code']

        # If nothing is waiting
        if not self.file_op_is_alive():
            if code == 400:
                self.file_op_count_up = 1
                self.file_op_count_del = 0
                self.file_op_delay = Timer(2, file_op_up, args=[msg['file_name']])
            elif code == 401:
                self.file_op_count_up = 0
                self.file_op_count_del = 1
                self.file_op_delay = Timer(2, file_op_del, args=[msg['file_name']])

        # If there are notifications in waiting
        else:
            self.file_op_delay.cancel()

            if code == 400:
                self.file_op_count_up += 1
            elif code == 401:
                self.file_op_count_del += 1

            # More then one upload and delete have been made
            if self.file_op_count_up > 0 and self.file_op_count_del > 0:
                arg = self.file_op_count_up + self.file_op_count_del
                self.file_op_delay = Timer(2, file_op_changes, args=[arg])

            # Only another upload
            elif self.file_op_count_up > 0:
                arg = self.file_op_count_up
                self.file_op_delay = Timer(2, file_op_many_up, args=[arg])

            # Only another delete
            elif self.file_op_count_del > 0:
                arg = self.file_op_count_del
                self.file_op_delay = Timer(2, file_op_many_down, args=[arg])

        # Start the wait for the notification send
        self.file_op_delay.start()

    def file_op_is_alive(self):
        return self.file_op_delay is not None and self.file_op_delay.is_alive()
