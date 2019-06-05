import pickle

from logging import getLogger
try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

from sync.controllers.localbox_ctrl import SyncsController
from sync.defaults import LOCALBOX_ACCOUNT_PATH
from sync.localbox import LocalBox


class AccountController:
    def __init__(self):
        self.lst_localbox = Preferences()

    def add(self, item):
        self.lst_localbox.append(item)

    def delete(self, index, save = True):
        """
        Delete item from list by 'index'
        :param index:
        :return:
        """
        del self.lst_localbox[index]
        if save:
            self.save()

    def save(self):
        getLogger(__name__).debug('Saving account: %s' % self.lst_localbox)

        with open(LOCALBOX_ACCOUNT_PATH, 'wb') as f:
            pickle.dump(self.lst_localbox, f)

    def load(self):
        getLogger(__name__).debug('Loading preferences: %s' % self.lst_localbox)

        try:
            with open(LOCALBOX_ACCOUNT_PATH, 'rb') as f:
                self.lst_localbox = pickle.load(f)

        except IOError:
            getLogger(__name__).warn('%s does not exist' % LOCALBOX_ACCOUNT_PATH)
            self.save()

        return self.lst_localbox

    def load_invites(self):
        invite_list = []
        for item in SyncsController().load():
            try:
                localbox_client = LocalBox(url=item.url, label=item.label, path=item.path)

                result = localbox_client.get_invite_list(user=item.user)

                for invite in result:
                    invite_list.append(invite)
            except URLError:
                getLogger(__name__).exception('failed to get_share_list (%s, %s)' % (item.url, item.label))
        return invite_list

class Preferences:
    def __init__(self):
        pass

    def __str__(self):
        return '(nothing in account controller)'
