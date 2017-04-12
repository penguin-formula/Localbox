import pickle

from sync.defaults import LOCALBOX_PREFERENCES_PATH


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


class Preferences:
    def __init__(self):
        pass

    def __str__(self):
        return '(nothing in account controller)'
