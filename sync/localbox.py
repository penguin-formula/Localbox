"""
localbox client library
"""

import errno
import os
import re
import hashlib
from Crypto.Cipher.AES import MODE_CFB
from Crypto.Cipher.AES import new as AES_Key
from Crypto.Random import new as CryptoRandom
from _ssl import PROTOCOL_TLSv1_2
from base64 import b64decode
from base64 import b64encode
from logging import getLogger
from os import stat, remove
from socket import error as SocketError

from loxcommon import os_utils
from sync import defaults
from sync.auth import Authenticator, AlreadyAuthenticatedError
from sync.gpg import gpg

try:
    from urllib2 import HTTPError, URLError
    from urllib2 import Request
    from urllib2 import urlopen
    from urllib import urlencode
    from urllib import quote_plus
    from httplib import BadStatusLine
    from ConfigParser import ConfigParser
except ImportError:
    from urllib.error import HTTPError  # pylint: disable=F0401,E0611
    from urllib.parse import quote_plus  # pylint: disable=F0401,E0611
    from urllib.parse import urlencode  # pylint: disable=F0401,E0611
    from urllib.request import urlopen  # pylint: disable=F0401,E0611
    from urllib.request import Request  # pylint: disable=F0401,E0611
    from http.client import BadStatusLine  # pylint: disable=F0401,E0611
    from configparser import ConfigParser  # pylint: disable=F0401,E0611

from json import loads
from json import dumps
from ssl import SSLContext  # pylint: disable=E0611


def getChecksum(key):
    """
    returns a partial hash of the given key for differentiation in logs. May need a stronger algorithm.
    """
    checksum = hashlib.md5()
    checksum.update(key)
    return checksum.hexdigest()[:5]


class LocalBox(object):
    """
    object representing localbox
    """

    def __init__(self, url, label):
        """

        :param url:
        :param label:
        :param path: filesystem path for the LocalBox
        """
        if url[-1] != '/':
            url += "/"
        self.url = url
        self.label = label
        self._authentication_url = None
        self._authentication_url = self.get_authentication_url()
        self._authenticator = Authenticator(self._authentication_url, label)

    @property
    def authenticator(self):
        return self._authenticator

    @property
    def username(self):
        return self._authenticator.username

    def get_authentication_url(self):
        """
        return an authentication url belonging to a localbox instance.
        """
        if self._authentication_url is not None:
            return self._authentication_url
        else:
            try:
                non_verifying_context = SSLContext(PROTOCOL_TLSv1_2)
                getLogger(__name__).debug("validating localbox server: %s" % self.url)
                urlopen(self.url, context=non_verifying_context)
            except BadStatusLine as error:
                getLogger(__name__).exception(error)
                raise error
            except HTTPError as error:
                if error.code != 401:
                    raise error
                auth_header = error.headers['WWW-Authenticate'].split(' ')
                bearer = False
                for field in auth_header:
                    if bearer:
                        try:
                            entry = field.split('=', 1)
                            if entry[0].lower() == "domain":
                                return entry[1][1:-1]
                        except ValueError as error:
                            getLogger(__name__).exception(error)
                            bearer = False
                    if field.lower() == 'bearer':
                        bearer = True
        raise AlreadyAuthenticatedError()

    def _make_call(self, request):
        """
        do the actual call to the server with authentication data
        """
        request.add_header('Authorization',
                           self.authenticator.get_authorization_header())
        non_verifying_context = SSLContext(PROTOCOL_TLSv1_2)
        return urlopen(request, context=non_verifying_context)

    def get_meta(self, path=''):
        """
        do the meta call
        """
        request = Request(url=self.url + 'lox_api/meta', data=dumps({'path': path}))
        getLogger(__name__).debug('calling lox_api/meta for path: %s' % path)
        try:
            result = self._make_call(request)
            json_text = result.read()
            return loads(json_text)
        except HTTPError as error:
            if error.code == 404:
                raise InvalidLocalBoxPathError(path=path)
            else:
                getLogger(__name__).exception(error)
                raise error

    def get_file(self, path=''):
        """
        do the file call
        """
        metapath = quote_plus(path).strip('/')
        request = Request(url=self.url + "lox_api/files", data=dumps({'path': metapath}))
        webdata = self._make_call(request)
        websize = webdata.headers.get('content-length', -1)
        data = webdata.read()
        ldata = len(data)
        getLogger(__name__).info("Downloaded %s: Websize: %d, readsize: %d cryptosize: %d", path, websize, ldata,
                                 len(data))
        return data

    def create_directory(self, path):
        """
        do the create directory call
        """
        metapath = urlencode({'path': path})
        request = Request(url=self.url + 'lox_api/operations/create_folder/',
                          data=metapath)

        getLogger(__name__).debug("Creating directory: %s" % path)
        try:
            self._make_call(request)
            if path.count('/') == 1:
                create_key_and_iv(self, path)
        except HTTPError as error:
            getLogger(__name__).warning("'%s' whilst creating directory %s. %s", error, path, error.message)
            # TODO: make directory encrypted

    def delete(self, path):
        """
        do the delete call
        """
        metapath = urlencode({'path': path})
        request = Request(url=self.url + 'lox_api/operations/delete/',
                          data=metapath)
        try:
            return self._make_call(request)
        except HTTPError:
            getLogger(__name__).error("Error remote deleting '%s'", path)

    def delete_share(self, share_id):
        """
        Delete share.

        :param share_id:
        :return:
        """
        request = Request(url=self.url + 'lox_api/shares/' + str(share_id) + '/delete')
        try:
            return self._make_call(request)
        except HTTPError:
            getLogger(__name__).error("Error remote deleting share '%d'", share_id)

    def upload_file(self, path, fs_path, passphrase):
        """
        upload a file to localbox

        :param path: path relative to localbox location. eg: /some_folder/image.jpg
        :param fs_path: file system path. eg: /home/user/localbox/some_folder/image.jpg
        :param passphrase: used to encrypt file
        :return:
        """
        metapath = quote_plus(path)

        try:
            # read plain file
            stats = stat(fs_path)
            openfile = open(fs_path, 'rb')
            contents = openfile.read(stats.st_size)
            openfile.flush()

            # encrypt file
            contents = gpg.add_pkcs7_padding(contents)
            clen = len(contents)
            contents = self.encode_file(path, contents, passphrase)

            # save encrypted file
            encrypted_file = open(fs_path + defaults.LOCALBOX_EXTENSION, 'wb')
            encrypted_file.write(contents)
            encrypted_file.close()

            openfile.close()

            # remove plain file
            remove(fs_path)

            # upload encrypted file
            getLogger(__name__).info("Uploading %s: Statsize: %d, readsize: %d cryptosize: %d",
                                     fs_path, stats.st_size, clen, len(contents))

            request = Request(url=self.url + 'lox_api/files',
                              data=dumps({'contents': b64encode(contents), 'path': metapath}))

            return self._make_call(request)

        except (BadStatusLine, HTTPError, OSError) as error:
            getLogger(__name__).error('Failed to upload file: %s' % (path, error))

        return None

    def call_user(self, send_data=None):
        """
        do the user call
        """
        url = self.url + "lox_api/user"
        if send_data is None:
            request = Request(url)
        else:
            request = Request(url, data=send_data)
        return self._make_call(request)

    def call_keys(self, path, passphrase):
        """
        do the keys call

        :return: the key for symmetric encryption in the form: (key, iv)
        """
        pgp_client = gpg()
        keys_path = os_utils.get_keys_path(path)
        keys_path = quote_plus(keys_path)
        getLogger(__name__).debug("call lox_api/key on path %s = %s", path, keys_path)

        request = Request(url=self.url + 'lox_api/key/' + keys_path)
        result = self._make_call(request)

        key_data = loads(result.read())
        key = pgp_client.decrypt(b64decode(key_data['key']), passphrase)
        iv = pgp_client.decrypt(b64decode(key_data['iv']), passphrase)
        getLogger(__name__).debug("Got key %s for path %s", getChecksum(key), path)

        return key, iv

    def get_all_users(self):
        """
        gets a list from the localbox server with all users.
        """
        request = Request(url=self.url + 'lox_api/identities')
        result = self._make_call(request).read()
        return loads(result)

    def create_share(self, localbox_path, passphrase, user_list):
        """
        Share directory with users.

        :return: True if success, False otherwise
        """
        if localbox_path.startswith('/'):
            localbox_path = localbox_path[1:]
        data = dict()
        data['identities'] = user_list

        request = Request(url=self.url + 'lox_api/share_create/' + quote_plus(localbox_path), data=dumps(data))

        try:
            result = self._make_call(request).read()
            key, iv = self.call_keys(localbox_path, passphrase)

            # import public key in the user_list
            for user in user_list:
                public_key = user['public_key']
                username = user['username']

                gpg().add_public_key(self.label, username, public_key)
                self.save_key(username, localbox_path, key, iv)

            return True
        except Exception as error:
            getLogger(__name__).exception(error)
            return False

    def get_share_list(self, user):
        """
        List shares of given user.

        :return: True if success, False otherwise
        """
        request = Request(url=self.url + 'lox_api/shares/user/' + user)

        try:
            result = self._make_call(request).read()
            if result != '' and result is not None:
                return loads(result)
            else:
                return []
        except Exception as error:
            getLogger(__name__).exception(error)
            return []

    def save_key(self, user, path, key, iv):
        """
        saves an encrypted key on the localbox server

        :param path: path relative to localbox location. eg: /some_folder/image.jpg
        :param key:
        :param iv:
        :param site: localbox label
        :param user:
        :return:
        """
        cryptopath = os_utils.get_keys_path(path)
        cryptopath = quote_plus(cryptopath)

        site = self.authenticator.label

        pgpclient = gpg()
        encodedata = {
            'key': b64encode(pgpclient.encrypt(key, site, user)),
            'iv': b64encode(pgpclient.encrypt(iv, site, user)),
            'user': user
        }
        data = dumps(encodedata)
        request = Request(
            url=self.url + 'lox_api/key/' + cryptopath, data=data)
        result = self._make_call(request)
        getLogger(__name__).debug('saving key for %s', cryptopath)
        # NOTE: this is just the result of the last call, not all of them.
        # should be more robust then this
        return result

    def decode_file(self, path, filename, passphrase):
        """
        decode a file
        """
        try:
            path = path.replace('\\', '/')
            key = get_aes_key(self, path, passphrase)

            with open(filename, 'rb') as content_file:
                contents = content_file.read()
                result = key.decrypt(contents)

            return gpg.remove_pkcs7_padding(result)
        except NoKeysFoundError as error:
            getLogger(__name__).exception('Failed to decode file %s, %s', filename, error)

    def encode_file(self, path, contents, passphrase):
        """
        encode a file
        """
        key = get_aes_key(self, path, passphrase, should_create=True)
        result = key.encrypt(contents)
        return result

    def is_valid_url(self):
        getLogger(__name__).debug("validating localbox server: %s" % (self.url))
        try:
            self.get_authentication_url()
            return True
        except (URLError, BadStatusLine, ValueError,
                AlreadyAuthenticatedError) as error:
            getLogger(__name__).debug("error with authentication url thingie")
            getLogger(__name__).exception(error)
            return False
        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise  # Not error we are looking for
            getLogger(__name__).error('Failed to connect to server, maybe forgot https? %s', e)
            return False


def create_key_and_iv(localbox_client, path):
    getLogger(__name__).debug('Creating a key for path: %s', path)
    key = CryptoRandom().read(32)
    iv = CryptoRandom().read(16)
    localbox_client.save_key(localbox_client.username, path, key, iv)


def get_aes_key(localbox_client, path, passphrase, should_create=False):
    key = None
    iv = None
    try:
        key, iv = localbox_client.call_keys(path, passphrase)
    except (HTTPError, TypeError, ValueError):
        if should_create:
            getLogger(__name__).debug("path '%s' is without key, generating one.", path)
            # generate keys if they don't exist
            create_key_and_iv(localbox_client, path)
        else:
            raise NoKeysFoundError(message='No keys found for %s' % path)

    return AES_Key(key, MODE_CFB, iv, segment_size=128) if key else None


def get_localbox_path(localbox_location, filesystem_path):
    """

    >>> get_localbox_path('/home/wilson/localbox-users/wilson-90', '/home/wilson/localbox-users/wilson-90/other/inside/test.txt')
    'other/inside/test.txt'
    >>> get_localbox_path('C:\\Users\\Administrator\\Desktop\\mybox', 'C:\\Users\\Administrator\\Desktop\\mybox\\shared')
    'shared'


    :param localbox_location:
    :param filesystem_path:
    :return:
    """
    return re.sub(r'^/', '', filesystem_path.replace(localbox_location, '', 1).replace('\\', '/'))


def remove_decrypted_files():
    import os, sync.controllers.openfiles_ctrl as ctrl

    getLogger(__name__).info('removing decrypted files')
    for filename in ctrl.load():
        try:
            os.remove(filename)
        except Exception as ex:
            getLogger(__name__).error('could not remove file %s, %s' % (filename, ex))

    ctrl.save([])


class InvalidLocalboxURLError(Exception):
    """
    URL for localbox backend is invalid or is unreachable
    """
    pass


class NoKeysFoundError(Exception):
    """
    Failed to get keys for file
    """

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class InvalidLocalBoxPathError(Exception):
    """
    Invalid LocalBox pass
    """

    def __init__(self, *args, **kwargs):
        self.path = kwargs['path']

    def __str__(self):
        return '%s is not a valid LocalBox path' % self.path
