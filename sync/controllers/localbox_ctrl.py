import json
import pickle
from logging import getLogger

import sync.models.label_model as label_model
from sync.defaults import LOCALBOX_SITES_PATH


class SyncsController(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(SyncsController, cls).__new__(cls)
        return cls.instance

    def __init__(self, lazy_load=False):

        if not hasattr(self, '_list'):
            self._list = list()
            if not lazy_load:
                self.load()

    def add(self, item):
        self._list.append(item)

    def delete(self, index, save=False):
        """
        Delete item from list by 'index'
        :param index:
        :return:
        """
        label = self._list[index].label
        label_model.delete_client_data(label)
        del self._list[index]
        if save:
            self.save()
        return label

    def save(self):
        pickle.dump(self._list, open(LOCALBOX_SITES_PATH, 'wb'))

    def load(self):
        try:
            self._list = pickle.load(open(LOCALBOX_SITES_PATH, 'rb'))
        except IOError as error:
            getLogger(__name__).warn('%s' % error)

        return self._list

    def get(self, other_label):
        # TODO: improve this, maybe put the sync on a map
        for sync in self._list:
            if sync.label == other_label:
                return sync

    @property
    def list(self):
        return self._list

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()


class SyncItem:
    def __init__(self, label=None, url=None, path=None, direction=None, user=None, shares=None):
        self._label = label
        self._url = url
        self._path = path
        self._direction = direction
        self._user = user
        self._shares = shares if shares is not None else []

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        self._direction = value

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    def __str__(self):
        return json.dumps(self.__dict__)


ctrl = SyncsController()


def get_localbox_list():
    """
    Get the LocalBoxes as a list of labels.

    :return: list of LocalBox labels.
    """
    return map(lambda x: x.label, SyncsController().load())
