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

        # For sync start and end
        self.sync_start_delay = None
        self.sync_start_time = 0

        # For file upload
        self.file_upload_delay = None
        self.file_upload_count = 0

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

            if msg['code'] == 100:
                getLogger(__name__).debug("stopping notifications thread")
                self._publish({ "cmd": "stop" })
                self.running = False

            elif msg['code'] == 300:
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

            elif msg['code'] == 400:
                def delay_file_upload(file_name):
                    self._publish({ "title": "LocalBox", "message": "Uploaded file {}".format(file_name) })

                def delay_file_upload_many(count):
                    self._publish({ "title": "LocalBox", "message": "Uploaded {} files".format(count) })

                if self.file_upload_delay is not None and self.file_upload_delay.is_alive():
                    self.file_upload_delay.cancel()

                    self.file_upload_count += 1
                    self.file_upload_delay = Timer(2, delay_file_upload_many, args=[self.file_upload_count])
                    self.file_upload_delay.start()

                else:
                    self.file_upload_delay = Timer(2, delay_file_upload, args=[msg['file_name']])
                    self.file_upload_delay.start()
                    self.file_upload_count = 1

        getLogger(__name__).debug("notifications thread stopped")

    def _publish(self, msg):
        self.publisher.send_json(msg)
