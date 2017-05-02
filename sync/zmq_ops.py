zmq_file_op_notif = "FILE_OP_NOTIF"
zmq_gui_notif = "GUI_NOTIF"


def mogrify(opt, payload):
    return opt + ' ' + payload


def demogrify(content):
    s = content.split(" ", 1)

    if len(s) == 1:
        return None

    return s[1]
