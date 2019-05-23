import os

from sync import defaults
from sync.controllers.login_ctrl import LoginController
from sync.localbox import LocalBox
from sync.gui import gui_utils
from logging import getLogger
import sync.controllers.openfiles_ctrl as openfiles_ctrl
from loxcommon import os_utils


def open_file(data_dic):
    # Get passphrase
    passphrase = LoginController().get_passphrase(data_dic["label"])

    # Passphrases are not saved correctly!!!!
    if not passphrase:
        passphrase = gui_utils.get_user_secret_input("YourLocalBox - Enter Passphrase", "Please provide the passphrase to unlock file.")

    if not passphrase:
        gui_utils.show_error_dialog(_('No passphrase provided. aborting'), 'Error', standalone=True)
        return None

    # Stat local box instance
    localbox_client = LocalBox(data_dic["url"], data_dic["label"], "")

    # Attempt to decode the file

    # print data_dic, passphrase

    try:
        decoded_contents = localbox_client.decode_file(
            data_dic["localbox_filename"],
            data_dic["filename"],
            passphrase)

    # If there was a failure, answer wit ha 404 to state that the file doesn't exist
    except Exception, e:
        gui_utils.show_error_dialog(_('Failed to decode contents. aborting : {}').format(e), 'Error', standalone=True)
        getLogger(__name__).info('failed to decode contents. aborting : {}'.format(e))

        return None

    # If the file was decoded, write it to disk
    tmp_decoded_filename = \
        os_utils.remove_extension(data_dic["filename"],
                                  defaults.LOCALBOX_EXTENSION)

    getLogger(__name__).info('tmp_decoded_filename: %s' % tmp_decoded_filename)

    if os.path.exists(tmp_decoded_filename):
        os.remove(tmp_decoded_filename)

    localfile = open(tmp_decoded_filename, 'wb')
    localfile.write(decoded_contents)
    localfile.close()

    # Keep file in list of opened files
    openfiles_ctrl.add(tmp_decoded_filename)

    return tmp_decoded_filename
