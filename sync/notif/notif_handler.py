import os
import time
import json
from logging import getLogger
from threading import Thread, Lock, Event, Timer

import zmq

import config
from sync.open_file import open_file
from sync.notif import notifs_util


class NotifHandler(Thread):
    """
    The NotifHandler is the central module that handles all the notifications
    in the LoxClient. This module runs in it's own thread and wait for any new
    notification to come. The module processes the incoming notifications and
    chooses what to send and where it sends it.

    For example, if 3 notifications for file uploading and 2 notifications for
    file deletion arrive at roughly the same time, this module will send a
    single notification to the GUI stating the "5 files changed" in order not
    to send to many notifications to the user.

    The module may send notifications to GUI or to the backend server.
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

        # For heartbeats (5xx)
        self.heartbeat_delay = None
        self.label_online = {}

        # ZeroMQ context for sockets
        self.context = zmq.Context.instance()

    def run(self):
        # Start socket for pulling new notifications
        self.in_notifs = self.context.socket(zmq.PULL)
        self.in_notifs.bind(notifs_util.zmq_ipc_push_bind)

        # Start socket to publish new processed notification
        self.out_notifs = self.context.socket(zmq.PUB)
        self.out_notifs.bind(notifs_util.zmq_ipc_pub_bind)

        getLogger(__name__).debug("notifications thread starting")

        # Loop until the thread is stopped
        self.running = True
        while self.running:
            msg = self.in_notifs.recv_json()
            code = msg['code']

            if code >= 100 and code < 200:
                self.handle_1xx(msg)

            elif code >= 300 and code < 400:
                self.handle_3xx(msg)

            elif code >= 400 and code < 500:
                self.handle_4xx(msg)

            elif code >= 500 and code < 600:
                self.handle_5xx(msg)

            elif code >= 600 and code < 700:
                self.handle_6xx(msg)

            elif code >= 700 and code < 800:
                self.handle_7xx(msg)

        getLogger(__name__).debug("notifications thread stopped")

    def _publish(self, opt, msg):
        """
        Publish to sockets which subscribed to what is given by opt. This is
        the general publishing method
        """

        msg_str = json.dumps(msg)
        contents = notifs_util.mogrify(opt, msg_str)
        self.out_notifs.send(contents)

    def _publish_gui_notif_popup(self, msg):
        """
        Publishes a notification for the GUI to display a popup. These
        notifications are always shown by the GUI and should be seen by the
        user
        """

        msg_to_send = msg.copy()
        msg_to_send["type"] = "popup"
        self._publish(notifs_util.zmq_gui_notif, msg_to_send)

    def _publish_gui_notif_heartbeat(self, msg):
        """
        Every time the GUI needs to be notified about a heartbeat event, this
        message is published
        """

        msg_to_send = msg.copy()
        msg_to_send["type"] = "heartbeat"
        self._publish(notifs_util.zmq_gui_notif, msg_to_send)

    def _publish_gui_notif_openfile_ctrl(self, msg):
        """
        When a file is added or removed from the open file controller, this
        message is published
        """

        msg_to_send = msg.copy()
        msg_to_send["type"] = "openfile_ctrl"
        self._publish(notifs_util.zmq_gui_notif, msg_to_send)

    def _publish_file_op_notif(self, msg):
        """
        Only when a process requests a file to be opened
        """

        self._publish(notifs_util.zmq_file_op_notif, msg)

    def _publish_heartbeat_req(self, msg):
        """
        A process requested a specific heartbeat
        """

        self._publish(notifs_util.zmq_heartbeat_req, msg)

    # =========================================================================
    # Thread Operations
    # =========================================================================

    def handle_1xx(self, msg):
        if msg['code'] == 100:
            getLogger(__name__).debug("stopping notifications thread")
            self._publish(notifs_util.zmq_gui_notif, { "type": "cmd", "cmd": "stop" })
            self._publish_heartbeat_req({ "cmd": "stop" })
            self.running = False

    # =========================================================================
    # Syncs
    # =========================================================================

    def handle_3xx(self, msg):
        code = msg['code']

        if code == 300:
            def delay_sync_start():
                self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Sync Started" })

            if self.sync_start_delay is not None and self.sync_start_delay.is_alive():
                self.sync_start_delay.cancel()

            self.sync_start_delay = Timer(config.sync_timer, delay_sync_start)
            self.sync_start_delay.start()
            self.sync_start_time = time.time()

        elif code == 301:
            if self.sync_start_delay is not None and self.sync_start_delay.is_alive():
                self.sync_start_delay.cancel()
                self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Sync Made" })

            elif time.time() > self.sync_start_time + config.sync_delay:
                self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Sync Stopped" })

            # Else, don't show any messages

    # =========================================================================
    # File Changes
    # =========================================================================

    def handle_4xx(self, msg):
        def file_op_up(file_name):
            self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Uploaded file {}".format(file_name) })

        def file_op_del(file_name):
            self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Deleted file {}".format(file_name) })

        def file_op_many_up(count):
            self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Uploaded {} files".format(count) })

        def file_op_many_down(count):
            self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Deleted {} files".format(count) })

        def file_op_changes(count):
            self._publish_gui_notif_popup({ "title": "LocalBox", "message": "Changed {} files".format(count) })

        code = msg['code']

        # If nothing is waiting
        if not self._file_op_is_alive():
            if code == 400:
                self.file_op_count_up = 1
                self.file_op_count_del = 0
                self.file_op_delay = self._start_file_op_timer(file_op_up, [msg['file_name']])
            elif code == 401:
                self.file_op_count_up = 0
                self.file_op_count_del = 1
                self.file_op_delay = self._start_file_op_timer(file_op_del, [msg['file_name']])

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
                self.file_op_delay = self._start_file_op_timer(file_op_changes, [arg])

            # Only another upload
            elif self.file_op_count_up > 0:
                arg = self.file_op_count_up
                self.file_op_delay = self._start_file_op_timer(file_op_many_up, [arg])

            # Only another delete
            elif self.file_op_count_del > 0:
                arg = self.file_op_count_del
                self.file_op_delay = self._start_file_op_timer(file_op_many_down, [arg])

    def _start_file_op_timer(self, op, args):
        timer = Timer(config.file_changes_timer, op, args=args)
        timer.start()
        return timer

    def _file_op_is_alive(self):
        return self.file_op_delay is not None and self.file_op_delay.is_alive()

    # =========================================================================
    # Heartbeat
    # =========================================================================

    def handle_5xx(self, msg):
        code = msg['code']

        # Heartbeats were requested
        if code == 500:
            labels = msg["labels"]
            force_gui_notif = msg["force_gui_notif"]

            # If no labels were given, do a full heartbeat request
            if len(labels) == 0:
                msg_s = { "cmd": "full_heartbeat", "force_gui_notif": force_gui_notif }
                self._publish_heartbeat_req(msg_s)

            # Else, do heartbeat only to a few syncs
            else:
                for label in labels:
                    msg_s = { "cmd": "do_heartbeat", "label": label, "force_gui_notif": force_gui_notif }
                    self._publish_heartbeat_req(msg_s)

        # Heartbeat for a given sync returned an online status
        elif code == 501:
            label = msg["label"]
            force_gui_notif = msg["force_gui_notif"]

            def gui_h():
                self._publish_gui_notif_heartbeat({ "label": label, "online": True })

            def gui_n():
                message = "Sync \"{}\" is Online".format(label)
                self._publish_gui_notif_popup({ "title": "LocalBox", "message": message })

            # If the sync of the given label was offline, then set it to be online and notify user
            if label not in self.label_online:
                self.label_online[label] = True
                gui_h()
                gui_n()

            # Else, notify only if the force_gui_notif was set to true
            else:
                if force_gui_notif:
                    gui_n()

                gui_h()

        # Heartbeat for a given sync returned an offline status
        elif code == 502:
            label = msg["label"]
            force_gui_notif = msg["force_gui_notif"]

            def gui_n():
                self._publish_gui_notif_heartbeat({ "label": label, "online": False })

            def gui_h():
                message = "Sync \"{}\" is Offline".format(label)
                self._publish_gui_notif_popup({ "title": "LocalBox", "message": message })

            if label not in self.label_online or self.label_online[label]:
                self.label_online[label] = False
                gui_h()
                gui_n()

            else:
                if force_gui_notif:
                    gui_h()

                gui_n()


    # =========================================================================
    # Notification from open file controller
    # =========================================================================

    def handle_6xx(self, msg):
        if msg['code'] == 600:
            self._publish_gui_notif_openfile_ctrl({})

    # =========================================================================
    # Request File Operations
    # =========================================================================

    def handle_7xx(self, msg):
        if msg['code'] == 700:
            file_name = open_file(msg['data_dic'])
            self._publish_file_op_notif({'file_name': file_name})
