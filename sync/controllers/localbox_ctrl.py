import json
import pickle
import os.path
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
        with open(LOCALBOX_SITES_PATH, 'wb') as f:
            pickle.dump(self._list, f)

    def load(self):
        try:
            with open(LOCALBOX_SITES_PATH, 'rb') as f:
                self._list = pickle.load(f)
        except IOError as error:
            getLogger(__name__).warn('%s' % error)

        return self._list

    def get(self, other_label):
        # TODO: improve this, maybe put the sync on a map
        for sync in self._list:
            if sync.label == other_label:
                return sync

    def getLabel(self, index):
        try:
            return self._list[index].label
        except IndexError:
            return None

    def check_uniq_path(self, path):
        # Check if the path exists
        if not os.path.exists(path):
            raise PathDoesntExistsException(path)

        # The path can't be sub path of an already synchronized directory, nor
        # have a synchronized directory in it
        def check_sub_dir(path_a, path_b):
            path_a_list = os.path.realpath(path_a).split(os.path.sep)
            path_b_list = os.path.realpath(path_b).split(os.path.sep)

            for p_i, p_ele in enumerate(path_a_list):
                if p_i >= len(path_b_list):
                    return False

                if p_ele != path_b_list[p_i]:
                    return False

            return True

        for sync in self._list:
            if check_sub_dir(path, sync.path) or check_sub_dir(sync.path, path):
                raise PathColisionException(path, sync.label, sync.path)

        return True

    def check_uniq_label(self, label):
        for sync in self._list:
            if sync.label == label:
                return False

        return True

    @property
    def list(self):
        return self._list

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        self.load()
        return self._list.__len__()


class SyncItem:
    def __init__(self, label=None, url=None, status=None, path=None, direction=None, user=None, shares=None, server=None):
        self._label = label
        self._url = url
        self._status = status if status is not None else "Initializing"
        self._path = path
        self._direction = direction
        self._user = user
        self._shares = shares if shares is not None else []
        self._server = server

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
    def status(self):
        if hasattr(self, '_status'):
            return self._status
        else:
            self._status = 'Initialing'
            return self._status

    @status.setter
    def status(self, value):
        self._status = value

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

    @property
    def server(self):
        return self._server

    @server.setter
    def server(self, value):
        self._server = value

    def __str__(self):
        return json.dumps(self.__dict__)


ctrl = SyncsController()


class Server:
    '''
    Server object representation
    '''
    def __init__(self, label, picture, url):
        self._label = label
        self._picture = picture
        self._url = url

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value

    @property
    def picture(self):
        return self._picture

    @picture.setter
    def picture(self, value):
        self._picture = value

    @property
    def url(self):
        return self._url    

    @url.setter
    def url(self, value):
        self._url = value

    def __str__(self):
        return json.dumps(self.__dict__)

    def save(self):
        if not label_model.get_server_data(self.label):
            label_model.create_server_data(self)


def get_server_list():
    return [ Server(label=item[0], url=item[1], picture=item[2]) for item in label_model.get_server_data() ]

def get_localbox_list():
    """
    Get the LocalBoxes as a list of labels.

    :return: list of LocalBox labels.
    """
    return map(lambda x: x.label, SyncsController().load())


class PathDoesntExistsException(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "Path '{}' doesn't exist".format(self.path)

class PathColisionException(Exception):
    def __init__(self, path, sync_label, sync_path):
        self.path = path
        self.sync_label = sync_label
        self.sync_path = sync_path

    def __str__(self):
        return "Path '{}' collides with path '{}' of sync {}".format(
            self.path,
            self.sync_label,
            self.sync_path)
