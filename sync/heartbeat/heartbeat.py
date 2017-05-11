import time
import json
from threading import Thread

import zmq

from sync.controllers.localbox_ctrl import SyncsController
from sync.notif.notifs import Notifs
from sync.notif import notifs_util


heartbeat_period = 20


class Heartbeat(Thread):
    """
    This thread monitors the status of the servers by sending heartbeat
    requests given a certain period of time. The thread also waits for explicit
    requests for heartbeat.

    TODO: Explain that the main heartbeat cycle never stops.
    """

    def __init__(self, main_syncing_thread):
        Thread.__init__(self)

        self.main_syncing_thread = main_syncing_thread

        self.running = False
        self.last_full_heartbeat = 0

        self.context = zmq.Context.instance()

    def run(self):
        # Subscribe for heartbeat requests
        self.hearthbeat_req = self.context.socket(zmq.SUB)
        self.hearthbeat_req.setsockopt(zmq.SUBSCRIBE, notifs_util.zmq_heartbeat_req)
        self.hearthbeat_req.connect(notifs_util.zmq_ipc_pub)

        # Create poller so the Subscribe receive may be timed out
        self.poller = zmq.Poller()
        self.poller.register(self.hearthbeat_req, zmq.POLLIN)

        # Keep timing of requests
        self.last_full_heartbeat = time.time()
        self.running = True

        while self.running:
            # Set time to wait
            timeout = ((self.last_full_heartbeat + heartbeat_period) - time.time()) * 1000
            if timeout < 0: timeout = 0
            socks = dict(self.poller.poll(timeout))

            # If an explicit request for a heartbeat was received...
            if self.hearthbeat_req in socks:
                contents = self.hearthbeat_req.recv()
                msg_str = notifs_util.demogrify(contents)
                msg = json.loads(msg_str)

                # If this is a request to stop
                if msg["cmd"] == "stop":
                    self.running = False
                    continue

                # Do a heartbeat
                elif msg["cmd"] == "do_heartbeat":
                    self.labelHeartbeat(msg["label"], msg['force_gui_notif'])

                # The command may still be a request for a full heartbeat
                elif msg["cmd"] == "full_heartbeat":
                    self.fullHeartbeat()

            # Else, this was a timeout and so do a full heartbeat
            else:
                self.fullHeartbeat()

    def labelHeartbeat(self, label, force_gui_notif=False):
        self.main_syncing_thread.do_heartbeat([label], force_gui_notif)

    def fullHeartbeat(self):
        self.main_syncing_thread.do_heartbeat()
        self.last_full_heartbeat = time.time()

