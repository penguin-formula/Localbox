"""
Authentication module for LocalBox/loauth
"""
from _ssl import PROTOCOL_TLSv1_2
from json import loads
from time import time

from .database import database_execute
from logging import getLogger
from ssl import SSLContext  # pylint: disable=E0611
try:
    from httplib import BadStatusLine
except:
    from http.client import BadStatusLine

try:
    from urllib import urlencode  # pylint: disable=E0611
    from urllib2 import urlopen, HTTPError, URLError
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen  # pylint: disable=F0401,E0611
    from urllib.parse import urlencode  # pylint: disable=F0401,E0611
    from urllib.error import HTTPError  # pylint: disable=F0401,E0611
    from urllib.error import URLError  # pylint: disable=F0401,E0611
from random import randint

# Time to take away from the expiration date before reauthenticating
# If zero, reauthentication will only happen when the token has expired
# If nonzero, it will reauthenticate EXPIRATION_LEEWAY seconds before
# expiration
EXPIRATION_LEEWAY = 5


def generate_client_id():
    """
    generate a client id
    """
    return 'id' + str(randint(1, 1000000000))


def generate_client_secret():
    """
    generate a client secret
    """
    return 'secret' + str(randint(1, 1000000000))


class Authenticator(object):
    """
    class implementing the authentication code
    """

    def __init__(self, authentication_url, label):
        self.authentication_url = authentication_url
        self.label = label
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.expires = 0
        self.scope = None
        self.username = None

        self.refresh_token = None
        self.load_client_data()

    def save_client_data(self):
        """
        Save the client credentials for the localbox identified by the label in
        the database
        """
        sql = "insert into sites (site, user, client_id, client_secret) " \
              "values (?, ?, ?, ?);"
        database_execute(
            sql, (self.label, self.username, self.client_id, self.client_secret))

    def load_client_data(self):
        """
        Get client data belonging to the localbox identified by label
        """
        sql = "select client_id, client_secret, user from sites where site = ?;"
        result = database_execute(sql, (self.label,))
        if result != [] and result is not None:
            getLogger(__name__).debug("loading client data for label: %s" % self.label)
            self.client_id = result[0][0]
            self.client_secret = result[0][1]
            self.username = result[0][2]
            return True
        return False

    def has_client_credentials(self):
        """
        check whether client credentials are available for this host
        """
        if self.client_id is not None and self.client_secret is not None:
            return True
        else:
            return False

    def init_authenticate(self, username, password):
        """
        Do initial authentication with the resource owner password credentials
        """
        if (self.client_id is not None) or (self.client_secret is not None):
            getLogger(__name__).info("init authenticate data")
            getLogger(__name__).info(self.client_id)
            getLogger(__name__).info(self.client_secret)
            getLogger(__name__).info("end init authenticate data")
            raise AuthenticationError("Do not call init_authenticate w"
                                      "hen client_id and client_secret"
                                      " are already set")
        self.username = username
        self.client_id = generate_client_id()
        self.client_secret = generate_client_secret()
        authdata = {'grant_type': 'password', 'username': username,
                    'password': password, 'client_id': self.client_id,
                    'client_secret': self.client_secret}
        try:
            self._call_authentication_server(authdata)
            if self.access_token is not None:
                getLogger(__name__).debug("Authentication Successful. "
                                          "Saving Client Data")
                self.save_client_data()
                return True
        except (URLError) as error:
            getLogger(__name__).exception(error)
            raise error
        # clear credentials on failure
        self.client_id = None
        self.client_secret = None
        return False

    def authenticate_with_client_secret(self):
        """
        Do authentication with the client credentials.
        """
        if (self.client_id is None) or (self.client_secret is None):
            raise AuthenticationError("Cannot authenticate on client c"
                                      "redentials without client_id an"
                                      "d client_secret")
        authdata = {'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret}
        self._call_authentication_server(authdata)

    def authenticate_with_password(self, username, password):
        """
        Do initial authentication with the resource owner password credentials
        """
        if self.client_id is None or self.client_secret is None:
            self.client_id = generate_client_id()
            self.client_secret = generate_client_secret()
            getLogger(__name__).debug('Created new credentials, cliend_id=%s' % self.client_id)

        self.username = username

        authdata = {'grant_type': 'password',
                    'username': username,
                    'password': password,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret}

        try:
            self._call_authentication_server(authdata)
            if self.access_token is not None:
                getLogger(__name__).debug('Authentication Successful. Saving Client Data')
                self.save_client_data()
                return True
        except (HTTPError, URLError) as error:
            if hasattr(error, 'code') and error.code != 401:   # HTTP Error 401: Unauthorized
                raise error
        # clear credentials on failure
        self.client_id = None
        self.client_secret = None
        return False

    def is_authenticated(self):
        try:
            if self.has_client_credentials():
                is_authenticated = True
            else:
                is_authenticated = False
        except AlreadyAuthenticatedError():
            is_authenticated = True

        getLogger(__name__).debug("is_authenticated: %s" % is_authenticated)

        return is_authenticated

    def _call_authentication_server(self, authdata):
        """
        function responsible for the actual call to the authentication
        server and assignment of token data
        """
        request_data = urlencode(authdata).encode('utf-8')
        try:
            getLogger(__name__).debug('calling authentication server: %s' % self.authentication_url)
            non_verifying_context = SSLContext(PROTOCOL_TLSv1_2)
            http_request = urlopen(self.authentication_url, request_data,
                                   context=non_verifying_context, timeout=5)
            json_text = http_request.read().decode('utf-8')
            json = loads(json_text)
            self.access_token = json.get('access_token')
            self.refresh_token = json.get('refresh_token')
            self.scope = json.get('scope')
            self.expires = time() + json.get('expires_in', 0) - EXPIRATION_LEEWAY
        except (HTTPError, URLError, BadStatusLine) as error:
            getLogger(__name__).debug('HTTPError when calling '
                                      'the authentication server')
            getLogger(__name__).debug(str(error))
            if hasattr(error, 'code') and error.code == 400:
                getLogger(__name__).debug('Authentication Problem')
                raise AuthenticationError('Invalid credentials')
            else:
                getLogger(__name__).debug('Other (connection) Problem')
                raise error

    def get_authorization_header(self):
        """
        Returns the Authorization header for authorizing against the
        LocalBox server proper.
        """
        if self.access_token is None and self.client_id is None and self.client_secret is None:
            raise AuthenticationError('Please authenticate with resource owner credentials first')
        if time() > self.expires:
            getLogger(__name__).debug("Token expired. Reauthenticating")
            self.authenticate_with_client_secret()
        return 'Bearer ' + self.access_token


class AuthenticationError(Exception):
    """
    Custom error class to signify problems in authentication
    """
    pass


class AlreadyAuthenticatedError(Exception):
    """
    authentication has already been done error.
    """
    pass
