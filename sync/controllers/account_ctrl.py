import pickle

from sync.defaults import LOCALBOX_PREFERENCES_PATH


class AccountController:
    def __init__(self):
        self.lst_localbox = list()

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
        pickle.dump(self.lst_localbox, open(LOCALBOX_ACCOUNT_PATH, 'wb'))

    def load(self):
        self.lst_localbox = pickle.load(open(LOCALBOX_ACCOUNT_PATH, 'rb'))
        return self.lst_localbox


class Preferences:
    def __init__(self):
        pass
