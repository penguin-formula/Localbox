import pickle
from logging import getLogger

from sync.controllers.localbox_ctrl import SyncsController
from sync.defaults import LOCALBOX_SHARES_PATH
from sync.localbox import LocalBox
from sync.database import database_execute

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError  # pylint: disable=F0401,E0611


class SharesController(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(SharesController, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        if not hasattr(self, '_list'):
            self._logged_in = False
            self._list = list()

    def add(self, item):
        self._list.append(item)
        self.save()

    def delete(self, index, save=False):
        """
        Delete item from list by 'index'
        :param index:
        :param save:
        :return:
        """
        item = self._list[index]
        localbox_client = LocalBox(url=item.url, label=item.label)
        localbox_client.delete(item.path)
        localbox_client.delete_share(item.id)
        sql = 'delete from keys where site = ? and user != ?'
        database_execute(sql, (item.label, item.user))
        del self._list[index]
        if save:
            self.save()

    def delete_for_label(self, label):

        sql = 'delete from keys where site = ?'
        database_execute(sql, (label,))
        map(lambda i: self._list.remove(i), filter(lambda i: i.label == label, self._list))

    def save(self):
        pickle.dump(self._list, open(LOCALBOX_SHARES_PATH, 'wb'))

    def load(self):
        self._list = []
        for item in SyncsController().load():
            try:
                localbox_client = LocalBox(url=item.url, label=item.label)

                for share in localbox_client.get_share_list(user=item.user):
                    share_item = ShareItem(user=share['user'], path='/' + share['path'], url=item.url, label=item.label,
                                           id=share['id'])
                    self._list.append(share_item)
            except URLError:
                getLogger(__name__).exception('failed to get_share_list (%s, %s)' % (item.url, item.label))

        return self._list

    def get_list(self):
        return self._list

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()


class ShareItem(object):
    def __init__(self, user=None, path=None, url=None, label=None, id=None):
        self.user = user
        self.path = path
        self.url = url
        self.label = label
        self.id = id

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)
