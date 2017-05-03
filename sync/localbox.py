"""
localbox client library
"""

import errno
import hashlib
import re
import os
from _ssl import PROTOCOL_TLSv1_2
from base64 import b64decode
from base64 import b64encode
from json import dumps
from json import loads
from logging import getLogger
from os import stat
from socket import error as SocketError
from ssl import SSLContext  # pylint: disable=E0611

from Crypto.Cipher.AES import MODE_CFB
from Crypto.Cipher.AES import new as AES_Key
from Crypto.Random import new as CryptoRandom

from loxcommon import os_utils
from sync import defaults
from sync.auth import Authenticator, AlreadyAuthenticatedError
from sync.controllers.login_ctrl import LoginController
from sync.gpg import gpg
from sync.notif.notifs import Notifs

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

    def __init__(self, url, label, path):
        """

        :param url:
        :param label:
        :param path: filesystem path for the LocalBox, ex: /home/john/my_localbox
        """
        if url[-1] != '/':
            url += "/"
        self.url = url
        self.label = label
        self.path = path
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

    def _make_call(self, request, retry_count=1):
        """
        Do the actual call to the server with authentication data.

        :param request:
        :param retry_count: counts the amount of retries.
        :return:
        """
        auth_header = self.authenticator.get_authorization_header()
        getLogger(__name__).debug('_make_call: %s' % request.get_full_url())
        getLogger(__name__).debug('_make_call auth header: %s' % auth_header)
        request.add_header('Authorization', auth_header)
        non_verifying_context = SSLContext(PROTOCOL_TLSv1_2)

        try:
            return urlopen(request, context=non_verifying_context)
        except HTTPError as error:
            if hasattr(error, 'code'):
                if error.code == 401:
                    if retry_count <= defaults.MAX_AUTH_RETRIES:
                        self.authenticator.authenticate_with_client_secret()
                        return self._make_call(request, retry_count + 1)
            raise error

    def get_meta(self, path=''):
        """
        do the meta call
        """
        path_q = quote_plus(path)
        request = Request(url=self.url + 'lox_api/meta', data=dumps({'path': path_q}))
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
        Create the directory on the server.
        This also creates stores the encryption keys, if the directory is "root parent".
        "root parent" means that is a 1st level directory inside the user's localbox.

        :param path:
        :return: key, iv if directory is "root parent", else None
        """
        getLogger(__name__).debug("Creating directory: %s" % path)
        metapath = urlencode({'path': path})
        request = Request(url=self.url + 'lox_api/operations/create_folder/',
                          data=metapath)
        try:
            self._make_call(request)
            return self.create_key_and_iv(path) if path.count('/') else None, None
        except HTTPError as error:
            getLogger(__name__).warning("'%s' whilst creating directory %s. %s", error, path, error.message)

    def delete(self, localbox_path):
        """
        do the delete call
        """
        metapath = urlencode({'path': localbox_path})
        request = Request(url=self.url + 'lox_api/operations/delete/',
                          data=metapath)
        try:
            res = self._make_call(request)
            Notifs().deletedFile(os.path.basename(localbox_path))
            return res
        except HTTPError:
            getLogger(__name__).error("Error remote deleting '%s'", localbox_path)

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

    def upload_file(self, path, fs_path, passphrase, remove=True):
        """
        upload a file to localbox

        :param path: path relative to localbox location. eg: /some_folder/image.jpg
        :param fs_path: file system path. eg: /home/user/localbox/some_folder/image.jpg
        :param passphrase: used to encrypt file
        :param remove: whether or not to remove the plain text file
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
            if remove:
                getLogger(__name__).debug('Deleting old plain file: %s' % fs_path)
                os_utils.shred(fs_path)

            # upload encrypted file
            getLogger(__name__).info("Uploading %s: Statsize: %d, readsize: %d cryptosize: %d",
                                     fs_path, stats.st_size, clen, len(contents))

            request = Request(url=self.url + 'lox_api/files',
                              data=dumps({'contents': b64encode(contents), 'path': metapath}))

            res = self._make_call(request)
            Notifs().uploadedFile(os.path.basename(fs_path))
            return res

        except (BadStatusLine, HTTPError, OSError) as error:
            getLogger(__name__).error('Failed to upload file: %s, error=%s' % (path, error))

        return None

    def _call_move(self, from_path, to_path):
        """
        Call the backend service to move files within the same "root" directory.

        :param from_path:
        :param to_path:
        :return:
        """
        request = Request(url=self.url + 'lox_api/operations/move',
                          data=dumps({
                              'from_path': from_path,
                              'to_path': to_path
                          }))
        try:
            return self._make_call(request)
        except HTTPError:
            getLogger(__name__).error("Error remote moving file '%s' to'%s'", from_path, to_path)

    def move_file(self, from_file, to_file, passphrase):
        localbox_path_from_file = get_localbox_path(self.path, from_file[:-4])
        localbox_path_to_file = get_localbox_path(self.path, to_file[:-4])

        if os_utils.get_keys_path(localbox_path_from_file) == os_utils.get_keys_path(localbox_path_to_file):
            self._call_move(localbox_path_from_file, localbox_path_to_file)
        else:
            # decrypt from_file
            plain_contents = self.decode_file(localbox_path_from_file, to_file, passphrase)
            if plain_contents:
                f = open(to_file[:-4], 'wb')
                f.write(plain_contents)
                f.close()
                # encrypt decrypted contents with the new location's key.
                # upload new encrypted contents
                self.upload_file(localbox_path_to_file, to_file[:-4], passphrase)

                # remove old encrypted file
                self.delete(localbox_path_from_file)
            else:
                getLogger(__name__).error("move %s failed. Contents weren't decoded successfully." % from_file)

    def call_user(self, send_data=None):
        """
        do the user call
        """
        url = self.url + "lox_api/user"
        if send_data is None:
            request = Request(url)
        else:
            request = Request(url, data=send_data)
        try:
            response = self._make_call(request).read()
            json = loads(response)
            return json
        except HTTPError:
            return {}

    def call_keys(self, localbox_path, passphrase):
        """
        Get the encrypted (key, iv) pair stored on the server.

        :return: the key for symmetric encryption in the form: (key, iv)
        """
        if not passphrase:
            raise InvalidPassphraseError
        pgp_client = gpg()
        keys_path = os_utils.get_keys_path(localbox_path)
        keys_path = quote_plus(keys_path)
        getLogger(__name__).debug("call lox_api/key on localbox_path %s = %s", localbox_path, keys_path)

        request = Request(url=self.url + 'lox_api/key/' + keys_path)
        result = self._make_call(request)

        key_data = loads(result.read())
        key = pgp_client.decrypt(b64decode(key_data['key']), passphrase)
        iv = pgp_client.decrypt(b64decode(key_data['iv']), passphrase)
        getLogger(__name__).debug("Got key %s for localbox_path %s", getChecksum(key), localbox_path)

        return key, iv

    def get_all_users(self):
        """
        gets a list from the localbox server with all users.
        """
        request = Request(url=self.url + 'lox_api/identities')
        result = self._make_call(request).read()
        return loads(result)

    def get_identities(self, user_list=None):
        """

        """
        data = dumps(user_list) if user_list is not None else None
        request = Request(url=self.url + 'lox_api/identities', data=data)
        result = self._make_call(request).read()
        return loads(result)

    def create_share(self, localbox_path, user_list):
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

            self._add_encryption_keys(localbox_path, user_list)

            return True
        except Exception as error:
            getLogger(__name__).exception(error)
            return False

    def _add_encryption_keys(self, localbox_path, user_list):
        if localbox_path.startswith('/'):
            localbox_path = localbox_path[1:]
        key, iv = self.call_keys(localbox_path, LoginController().get_passphrase(self.label))

        # import public key in the user_list
        for user in user_list:
            public_key = user['public_key']
            username = user['username']

            gpg().add_public_key(self.label, username, public_key)
            self.save_key(username, localbox_path, key, iv)

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

    def get_share_user_list(self, share_id):
        """
        List users of a given share.

        :return: List with the users if success, empty list otherwise
        """
        request = Request(url=self.url + 'lox_api/shares/' + str(share_id))

        try:
            result = self._make_call(request).read()
            if result != '' and result is not None:
                return loads(result)
            else:
                return []
        except Exception as error:
            getLogger(__name__).exception(error)
            return []

    def edit_share_users(self, share, user_list):
        """
        List users of a given share.

        :return: True if success, False otherwise
        """
        request = Request(url=self.url + 'lox_api/shares/' + str(share.id) + '/edit',
                          data=dumps(user_list))

        try:
            self._make_call(request).read()
            user_list = self.get_identities(user_list)
            self._add_encryption_keys(share.path, user_list)
            return True
        except Exception as error:
            getLogger(__name__).exception(error)
            return False

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

        getLogger(__name__).debug('saving key for %s', cryptopath)

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
        # NOTE: this is just the result of the last call, not all of them.
        # should be more robust then this
        return result

    def do_heartbeat(self):
        """
        """
        request = Request(url=self.url + 'lox_api/heartbeat')

        result = False

        try:
            self._make_call(request)
            result = True

        except HTTPError as error:
            pass
            result = False

        return result

    def decode_file(self, path, filename, passphrase):
        """
        decode a file
        """
        try:
            path = path.replace('\\', '/')
            key = self.get_aes_key(path, passphrase)

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
        key = self.get_aes_key(path, passphrase)
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

    def create_key_and_iv(self, path):
        getLogger(__name__).debug('Creating a key for path: %s', path)
        key = CryptoRandom().read(32)
        iv = CryptoRandom().read(16)
        self.save_key(self.username, path, key, iv)

        return key, iv

    def get_aes_key(self, path, passphrase):
        try:
            key, iv = self.call_keys(path, passphrase)
        except (HTTPError, TypeError, ValueError):
            raise NoKeysFoundError(message='No keys found for %s' % path)

        # TODO: use timed cache (see cachetools.TTLCache: https://pythonhosted.org/cachetools/)
        return AES_Key(key, MODE_CFB, iv, segment_size=128) if key else None


def get_localbox_path(localbox_location, filesystem_path):
    """

    >>> get_localbox_path('/home/wilson/localbox-users/wilson-90', '/home/wilson/localbox-users/wilson-90/other/inside/test.txt')
    '/other/inside/test.txt'
    >>> get_localbox_path('C:\\Users\\Administrator\\Desktop\\mybox', 'C:\\Users\\Administrator\\Desktop\\mybox\\shared')
    '/shared'


    :param localbox_location:
    :param filesystem_path:
    :return:
    """
    return re.sub(defaults.LOCALBOX_EXTENSION + '$', '',
                  filesystem_path.replace(localbox_location, '', 1).replace('\\', '/'))


def remove_decrypted_files():
    import os, sync.controllers.openfiles_ctrl as ctrl

    getLogger(__name__).info('removing decrypted files')

    files = ctrl.load()

    if files is None:
        return

    for filename in files:
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


class InvalidPassphraseError(Exception):
    """
    Passphrase supplied is invalid.
    """
    pass
