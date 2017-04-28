import zmq


def _send(msg):
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect("tcp://127.0.0.1:8000")

    socket.send_json(msg)


# =============================================================================
# Thread Operations
# =============================================================================


def stop():
    _send({ 'code': 100 })


# =============================================================================
# Syncs
# =============================================================================


def syncStarted():
    _send({ 'code': 300 })


def syncEnded():
    _send({ 'code': 301 })


# =============================================================================
# File Changes
# =============================================================================


def uploadedFile(file_name):
    _send({ 'code': 400, 'file_name': file_name })


def deletedFile(file_name):
    _send({ 'code': 401, 'file_name': file_name })
