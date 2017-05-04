import time
import json
from threading import Thread

import zmq

from sync.controllers.localbox_ctrl import SyncsController
from sync.notif.notifs import Notifs
from sync.notif import notifs_util


heartbeat_period = 10


class Heartbeat(Thread):
    def __init__(self, main_syncing_thread):
        Thread.__init__(self)

        self.main_syncing_thread = main_syncing_thread

        self.running = False
        self.last_full_heartbeat = 0

        self.context = zmq.Context.instance()

    def run(self):
        self.hearthbeat_req = self.context.socket(zmq.SUB)
        self.hearthbeat_req.setsockopt(zmq.SUBSCRIBE, notifs_util.zmq_heartbeat_req)
        self.hearthbeat_req.connect(notifs_util.zmq_ipc_pub)

        self.poller = zmq.Poller()
        self.poller.register(self.hearthbeat_req, zmq.POLLIN)

        self.last_full_heartbeat = time.time()
        self.running = True

        while self.running:
            timeout = ((self.last_full_heartbeat + heartbeat_period) - time.time()) * 1000
            if timeout < 0: timeout = 0
            socks = dict(self.poller.poll(timeout))

            if self.hearthbeat_req in socks:
                contents = self.hearthbeat_req.recv()
                msg_str = notifs_util.demogrify(contents)
                msg = json.loads(msg_str)

                if msg["cmd"] == "stop":
                    self.running = False
                    continue

                elif msg["cmd"] == "do_heartbeat":
                    self.labelHeartbeat(msg["label"])

                elif msg["cmd"] == "full_heartbeat":
                    self.fullHeartbeat()

            else:
                self.fullHeartbeat()

    def fullHeartbeat(self):
        self.main_syncing_thread.do_heartbeat()
        self.last_full_heartbeat = time.time()

    def labelHeartbeat(self, label):
        self.main_syncing_thread.do_heartbeat([label])
