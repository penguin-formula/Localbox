from sync.database import database_execute, DatabaseError
from logging import getLogger
from gnupg import GPG
from os.path import join
from os.path import isfile
from base64 import b64encode
from base64 import b64decode

try:
    from ConfigParser import ConfigParser  # pylint: disable=F0401
    from StringIO import StringIO  # pylint: disable=F0401
except ImportError:
    from configparser import ConfigParser  # pylint: disable=F0401
    from io import StringIO

from distutils.sysconfig import project_base
from distutils.spawn import find_executable


class gpg(object):
    """
    module to wrap the gnupg library and gpg binary
    """

    def __init__(self, folder_path=None, binary_path=None):
        # ugly but working
        if binary_path is None:
            binary_path = join(project_base, "gpg", "gpg.exe")
            if not isfile(binary_path):
                binary_path = join(project_base, 'gpg')
                if not isfile(binary_path):
                    binary_path = find_executable('gpg')
                    if not isfile(binary_path):
                        raise RuntimeError('gpg not found')
        self.gpg = GPG(binary_path,     # gpgbinary
                       folder_path,     # gnupghome
                       verbose=False,
                       options=["--allow-non-selfsigned-uid"])

    def get_key(self, fingerprint, private):
        """
        returns the key belonging to the fingerprint given. if 'private' is
        True, the private key is returned. If 'private' is False, the public
        key will be returned.
        """
        key = self.gpg.export_keys(fingerprint, private, armor=False)
        return b64encode(key.encode('ISO8859-1'))

    def add_keypair(self, public_key, private_key, site, user, passphrase):
        """
        add a keypair into the gpg key database
        """
        try:
            result1 = self.gpg.import_keys(b64decode(public_key))
            result2 = self.gpg.import_keys(b64decode(private_key))
        except TypeError as error:
            getLogger(__name__).critical("add_keypair TypeError " + str(error))
        # make sure this is a key _pair_
        try:
            assert result1.fingerprints[0] == result2.fingerprints[0]
        except (IndexError, AssertionError) as error:
            getLogger(__name__).exception(
                'add_keypair IndexError/AssertionError: ' + str(error))
            return None
        fingerprint = result1.fingerprints[0]

        if self.is_passphrase_valid(passphrase=passphrase, fingerprint=fingerprint):
            old_fingerprint = self.get_fingerprint(site, user)
            if not old_fingerprint:
                sql = "INSERT INTO keys (site, user, fingerprint) VALUES (?, ?, ?)"
                database_execute(sql, (site, user, fingerprint))
            else:
                sql = "UPDATE keys SET SITE=? WHERE fingerprint=?"
                database_execute(sql, (site, old_fingerprint))
                if fingerprint != old_fingerprint:
                    getLogger(__name__).warn('updating %s fingerprint to %s' % (user, fingerprint))
            return fingerprint
        else:
            return None

    def add_public_key(self, site, user, public_key):
        """
        add a public key into the gpg key database
        """
        try:
            result1 = self.gpg.import_keys(b64decode(public_key))
            fingerprint = result1.fingerprints[0]

            sql = "INSERT INTO keys (site, user, fingerprint) VALUES (?, ?, ?)"
            database_execute(sql, (site, user, fingerprint))
            return fingerprint
        except TypeError as error:
            getLogger(__name__).critical("add_public_key TypeError " + str(error))
        except DatabaseError as error:
            getLogger(__name__).critical("add_public_key DatabaseError " + str(error))

    def is_passphrase_valid(self, passphrase, label=None, user=None, fingerprint=None):
        if not fingerprint:
            fingerprint = self.get_fingerprint(label, user)

        sign_result = self.gpg.sign("test", keyid=fingerprint, passphrase=passphrase)

        return sign_result.data != ''

    def generate(self, passphrase, site, user):
        """
        Generate a new 2048 bit GPG key and add it to the gpg manager.
        """
        data = self.gpg.gen_key_input(key_length=2048, passphrase=passphrase)
        dat = self.gpg.gen_key(data)
        fingerprint = dat.fingerprint
        sql = "INSERT INTO keys (site, user, fingerprint) VALUES (?, ?, ?);"
        database_execute(sql, (site, user, fingerprint))
        return fingerprint

    def get_fingerprint(self, site, user):
        sql = "select fingerprint from keys where site = ? and user = ?"
        result = database_execute(sql, (site, user))
        if not len(result):
            return None
        return result[0][0]

    def has_key(self, site, user):
        """
        Check whether a key is present for a certain site and user
        """
        return self.get_fingerprint(site, user) is None

    def encrypt(self, data, site, user, armor=False):
        """
        encrypt data for user at site.
        """
        fingerprint = self.get_fingerprint(site, user)
        cryptdata = self.gpg.encrypt_file(StringIO(data),
                                          fingerprint,
                                          always_trust=True,
                                          armor=armor)
        return str(cryptdata)

    def decrypt(self, data, passphrase):
        """
        decrypt data received from site.
        """
        datafile = StringIO(data)
        result = self.gpg.decrypt_file(datafile,
                                       passphrase=passphrase,
                                       always_trust=True)
        return str(result)

    @staticmethod
    def add_pkcs7_padding(contents):
        # Input strings must be a multiple of the segment size 16 bytes in length
        segment_size = 16

        # calculate how much padding is needed
        old_contents_length = len(contents)
        next_mult = old_contents_length + (segment_size - old_contents_length % segment_size)
        getLogger(__name__).debug('old contents length %s || new contents length %s' % (old_contents_length, next_mult))

        # do the padding
        padding_byte = chr(next_mult - old_contents_length)
        contents = contents.ljust(next_mult, padding_byte)

        return contents

    @staticmethod
    def remove_pkcs7_padding(contents):
        """
        Remove PKCS#7 padding bytes

        >>> gpg.remove_pkcs7_padding('some_content'.ljust(16, chr(4)))
        'some_content'

        >>> gpg.remove_pkcs7_padding('some_content')
        'some_content'

        >>> gpg.remove_pkcs7_padding('')
        ''

        :param contents:
        :return: contents without padding
        """
        if len(contents) < 1:
            getLogger(__name__).debug('contents is empty. No PKCS#7 padding removed')
            return contents

        bytes_to_remove = ord(contents[-1])  # will work up to 255 bytes

        # check if contents have valid PKCS#7 padding
        if bytes_to_remove > 1 and contents[-2] != contents[-1]:
            getLogger(__name__).debug('no PKCS#7 padding detected')
            return contents

        getLogger(__name__).debug('removing %s bytes of PKCS#7 padding' % bytes_to_remove)
        return contents[0:(len(contents) - bytes_to_remove)]


if __name__ == '__main__':
    import doctest

    doctest.testmod()
