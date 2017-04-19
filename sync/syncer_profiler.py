import logging

from sync.controllers.login_ctrl import LoginController
from sync.localbox import LocalBox
from sync.syncer import Syncer

logging.getLogger('sync').setLevel(logging.WARNING)

url = 'https://box.yourlocalbox.org'
path = '/home/wilson/git-new/LinWin-PySync/lo-wilson-new/'
direction = 'potatoes'
label = 'lo-wilson'
localbox_client = LocalBox(url, label, path)

syncer = Syncer(localbox_client, path, direction, name=label)
LoginController().store_passphrase(passphrase='p123', label=label, user='wilson')


syncer.syncsync()
