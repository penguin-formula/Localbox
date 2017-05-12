"""
This file declares some utilities for the communication part of the client.
"""


import os


zmq_file_op_notif = "FILE_OP_NOTIF"
zmq_gui_notif = "GUI_NOTIF"
zmq_gui_heartbeat = "GUI_HEARTBEAT"
zmq_heartbeat_req = "HEARTBEAT_REQ"

if os.name == "posix":
    zmq_ipc_push_bind = "ipc://push"
    zmq_ipc_pub_bind  = "ipc://pub"

    zmq_ipc_push = "ipc://push"
    zmq_ipc_pub  = "ipc://pub"

else:
    zmq_ipc_push_bind = "tcp://*:9000"
    zmq_ipc_pub_bind  = "tcp://*:9001"

    zmq_ipc_push = "tcp://localhost:9000"
    zmq_ipc_pub  = "tcp://localhost:9001"


def mogrify(opt, payload):
    return opt + ' ' + payload


def demogrify(content):
    s = content.split(" ", 1)

    if len(s) == 1:
        return None

    return s[1]
