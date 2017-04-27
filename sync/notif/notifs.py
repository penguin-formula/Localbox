import zmq


def _send(msg):
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect("tcp://127.0.0.1:8000")

    socket.send_json(msg)


def syncStarted():
    _send({ 'code': 200 })


def syncEnded():
    _send({ 'code': 201 })


def stop():
    _send({ 'code': 100 })
