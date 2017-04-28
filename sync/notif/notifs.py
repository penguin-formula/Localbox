"""
This module declares a set of functions that send new notifications to the
NotifHandler. They are just simple wrappers around the possible messages that
NotifHandler expects to see.
"""

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
    """
    Tell the NotifHandler thread to stop. Used when shutting down
    """

    _send({ 'code': 100 })


# =============================================================================
# Syncs
# =============================================================================


def syncStarted():
    """
    When a synchronization process starts
    """

    _send({ 'code': 300 })


def syncEnded():
    """
    When a synchronization process ends
    """

    _send({ 'code': 301 })


# =============================================================================
# File Changes
# =============================================================================


def uploadedFile(file_name):
    """
    When a file is uploaded

    @param file_name The name of the uploaded file
    """

    _send({ 'code': 400, 'file_name': file_name })


def deletedFile(file_name):
    """
    When a file is deleted

    @param file_name The name of the deleted file
    """

    _send({ 'code': 401, 'file_name': file_name })
