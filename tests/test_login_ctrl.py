from __future__ import absolute_import

import unittest


class TestLoginController(unittest.TestCase):
    def test_store_keys(self):
        from sync.localbox import LocalBox
        from sync.controllers.login_ctrl import LoginController
        from sync.auth import Authenticator
        lox_client = LocalBox(url='https://localhost:5001', label=None)
        authenticator = Authenticator(
            authentication_url='http://localhost:5000/loauth/?redirect_uri=http%3A%2F%2Flocalhost%3A5001%2F',
            label=None
        )
        authenticator.init_authenticate('loxtest', 'p123')
        lox_client._authenticator = authenticator

        result = LoginController().store_keys(lox_client, None, None, 'p123')


if __name__ == '__main__':
    unittest.main()
