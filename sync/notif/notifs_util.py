"""
This file declares some utilities for the communication part of the client.
"""

zmq_file_op_notif = "FILE_OP_NOTIF"
zmq_gui_notif = "GUI_NOTIF"


zmq_ipc_push = "ipc:///tmp/loxclient_i"
zmq_ipc_pub  = "ipc:///tmp/loxclient_o"


def mogrify(opt, payload):
    return opt + ' ' + payload


def demogrify(content):
    s = content.split(" ", 1)

    if len(s) == 1:
        return None

    return s[1]
