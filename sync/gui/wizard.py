import json
import errno
import wx, os

try:
    from wx.wizard import Wizard, WizardPageSimple, EVT_WIZARD_BEFORE_PAGE_CHANGED, EVT_WIZARD_PAGE_CHANGING
except:
    from wx.adv import Wizard, WizardPageSimple, EVT_WIZARD_BEFORE_PAGE_CHANGED, EVT_WIZARD_PAGE_CHANGING

try:
    from httplib import BadStatusLine
except:
    from http.client import BadStatusLine

from logging import getLogger

try:
    from urllib2 import URLError
except:
    from urllib.error import URLError
from socket import error as SocketError

import sync.gui.gui_utils as gui_utils
import sync.auth as auth
from sync.controllers.localbox_ctrl import SyncsController, SyncItem
from sync.controllers.localbox_ctrl import PathDoesntExistsException, PathColisionException
from sync.controllers.login_ctrl import LoginController
from sync.localbox import LocalBox


class NewSyncWizard(Wizard):
    def __init__(self, sync_list_ctrl, event):
        Wizard.__init__(self, None, -1, _('Add new sync'))

        # Attributes
        self.pubkey = None
        self.privkey = None
        self.event = event
        self.localbox_client = None
        self.ctrl = sync_list_ctrl
        self.username = None
        self.path = None
        self.box_label = None

        self.page1 = NewSyncInputsWizardPage(self)
        self.page2 = LoginWizardPage(self)
        self.page_ask_passphrase = PassphraseWizardPage(self)
        self.page_new_passphrase = NewPassphraseWizardPage(self)

        WizardPageSimple.Chain(self.page1, self.page2)
        WizardPageSimple.Chain(self.page2, self.page_ask_passphrase)

        # self.FitToPage(self.page1)
        self.SetPageSize(gui_utils.NEW_SYNC_WIZARD_SIZE)

        self.RunWizard(self.page1)

        self.Destroy()


class NewSyncInputsWizardPage(WizardPageSimple):
    def __init__(self, parent):
        """Constructor"""
        WizardPageSimple.__init__(self, parent)

        # Attributes
        self.parent = parent
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._label = wx.TextCtrl(self)
        self._url = wx.TextCtrl(self)
        self._selected_dir = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.btn_select_dir = wx.Button(self, label=_('Select'), size=(95, 30))

        # Layout
        self._DoLayout()

        self.Bind(wx.EVT_BUTTON, self.select_localbox_dir, self.btn_select_dir)
        self.Bind(EVT_WIZARD_BEFORE_PAGE_CHANGED, self.is_authenticated)
        self.Bind(EVT_WIZARD_PAGE_CHANGING, self.validate_new_sync_inputs)

    def is_authenticated(self, event):

        if event.GetDirection():
            # going forwards
            getLogger(__name__).debug('Checking if is already authenticated for: %s' % self.label)
            if self.parent.localbox_client and self.parent.localbox_client.authenticator.is_authenticated():
                WizardPageSimple.Chain(self.parent.page1, self.parent.page_ask_passphrase)

    def _DoLayout(self):
        sizer = wx.FlexGridSizer(3, 3, 10, 10)

        sizer.Add(wx.StaticText(self, label=_("Label:")),
                  1, wx.ALIGN_RIGHT)
        sizer.Add(self._label, 0, wx.EXPAND)
        sizer.AddGrowableCol(1)
        sizer.Add(wx.StaticText(self.parent, label=''))

        sizer.Add(wx.StaticText(self, label=_("URL:")),
                  0, wx.ALIGN_RIGHT)
        sizer.Add(self._url, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label=''))

        sizer.Add(wx.StaticText(self, label=_("Path:")),
                  0, wx.ALIGN_RIGHT)
        sizer.Add(self._selected_dir, 0, wx.EXPAND)
        sizer.Add(self.btn_select_dir, 0, wx.EXPAND)

        self._sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, border=10)

        self.SetSizer(self._sizer)

    def select_localbox_dir(self, event):
        dialog = wx.DirDialog(None, _("Choose a file"), style=wx.DD_DEFAULT_STYLE, defaultPath=os.getcwd(),
                              pos=(10, 10))
        if dialog.ShowModal() == wx.ID_OK:
            self._selected_dir.SetValue(dialog.GetPath())

        dialog.Destroy()

    def validate_new_sync_inputs(self, event):
        # step 1
        label = self.label
        url = self.url
        path = self.path

        # Validate the inputs
        if not gui_utils.is_valid_input(label):
            gui_utils.show_error_dialog(message=_('%s is not a valid label') % label, title=_('Invalid Label'))
            event.Veto()
            return

        if not gui_utils.is_valid_input(url):
            gui_utils.show_error_dialog(message=_('%s is not a valid URL') % url, title=_('Invalid URL'))
            event.Veto()
            return

        if not gui_utils.is_valid_input(path):
            gui_utils.show_error_dialog(message=_('%s is not a valid path') % path, title=_('Invalid Path'))
            event.Veto()
            return

        # Check if the label of the directory are already in the Syncs
        if not SyncsController().check_uniq_label(label):
            gui_utils.show_error_dialog(message=_('Label "%s" already exists') % label, title=_('Invalid Label'))
            event.Veto()
            return

        try:
            SyncsController().check_uniq_path(path)

        except PathDoesntExistsException as e:
            msg = _("Path '{}' doesn't exist").format(e.path)

            gui_utils.show_error_dialog(message=msg, title=_('Invalid Path'))

            event.Veto()
            return

        except PathColisionException as e:
            msg = _("Path '{}' collides with path '{}' of sync {}").format(
                e.path, e.sync_label, e.sync_path)

            gui_utils.show_error_dialog(message=msg, title=_('Path Collision'))
            event.Veto()
            return

        # Create a localbox instance
        # TODO: Errors in here need to be clarified
        try:
            self.parent.localbox_client = LocalBox(url, label)

        except (URLError, BadStatusLine, ValueError,
                auth.AlreadyAuthenticatedError) as error:
            getLogger(__name__).debug("error with authentication url thingie")
            getLogger(__name__).exception(error)

            gui_utils.show_error_dialog(message=_('Can\'t authenticate with given username and password.'), title=_('Can\'t authenticate.'))
            event.Veto()
            return

        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise  # Not error we are looking for
            getLogger(__name__).error('Failed to connect to server, maybe forgot https? %s', e)
            event.Veto()
            return

        self.parent.box_label = label
        self.parent.path = path

    @property
    def path(self):
        return self._selected_dir.GetValue()

    @property
    def label(self):
        return self._label.GetValue().encode()

    @property
    def url(self):
        return self._url.GetValue().encode()


class LoginWizardPage(WizardPageSimple):
    def __init__(self, parent):
        WizardPageSimple.__init__(self, parent)

        # Attributes
        self.parent = parent
        self.is_authenticated = False
        self._username = wx.TextCtrl(self)
        self._password = wx.TextCtrl(self, style=wx.TE_PASSWORD)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer = main_sizer

        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(wx.StaticText(self, label=_("Username:")),
                        0, wx.ALL | wx.ALIGN_LEFT)
        input_sizer.Add(self._username, 0, wx.ALL | wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label=_("Password:")),
                        0, wx.ALL | wx.ALIGN_LEFT, border=gui_utils.DEFAULT_BORDER)
        input_sizer.Add(self._password, 0, wx.ALL | wx.EXPAND)

        main_sizer.Add(input_sizer, 1, wx.ALL | wx.EXPAND, border=gui_utils.DEFAULT_BORDER)

        self.already_authenticated_sizer = wx.BoxSizer(wx.VERTICAL)
        self._label_already_authenticated = wx.StaticText(self, label='')
        self.already_authenticated_sizer.Add(self._label_already_authenticated, 1, wx.ALL | wx.EXPAND,
                                             border=gui_utils.DEFAULT_BORDER)

        self.Bind(EVT_WIZARD_BEFORE_PAGE_CHANGED, self.call_password_authentication)
        # self.Bind(EVT_WIZARD_BEFORE_PAGE_CHANGED, self.should_login)
        # self.Bind(EVT_WIZARD_PAGE_CHANGING, self.passphrase_page)

        self.layout_inputs()

    def passphrase_page(self, event):
        getLogger(__name__).debug('EVT_WIZARD_BEFORE_PAGE_CHANGED')

        if event.GetDirection():
            response = self.parent.localbox_client.call_user()
            result = json.loads(response.read())

            if 'private_key' in result and 'public_key' in result:
                getLogger(__name__).debug("private key and public key found")

                self.SetNext(self.parent.page_ask_passphrase)

                self.parent.privkey = result['private_key']
                self.parent.pubkey = result['public_key']
            else:
                getLogger(__name__).debug("private key or public key not found")
                getLogger(__name__).debug(str(result))
                WizardPageSimple.Chain(self, self.parent.page_new_passphrase)

    def layout_inputs(self):
        self.already_authenticated_sizer.ShowItems(show=False)
        self.main_sizer.ShowItems(show=True)
        self.SetSizer(self.main_sizer)

    def should_login(self, event):
        getLogger(__name__).debug('should_login: EVT_WIZARD_BEFORE_PAGE_CHANGED')

        if self.parent.localbox_client.authenticator.is_authenticated():
            self.is_authenticated = True
            self._label_already_authenticated.SetLabel(
                _("Already authenticated for: %s. Skipping authentication with password.") % self.parent.box_label)
            self.SetSizer(self.already_authenticated_sizer)
            self.already_authenticated_sizer.ShowItems(show=True)
            self.main_sizer.ShowItems(show=False)
        else:
            self.is_authenticated = False
            self.layout_inputs()

        self.Layout()

    def call_password_authentication(self, event):
        getLogger(__name__).debug("authenticating... - direction: %s", event.GetDirection())

        if event.GetDirection():
            # going forwards
            if not self.is_authenticated:
                if gui_utils.is_valid_input(self.username) and gui_utils.is_valid_input(self.password):
                    try:
                        success = self.parent.localbox_client.authenticator.authenticate_with_password(
                            self.username,
                            self.password)
                    except Exception as error:
                        success = False
                        getLogger(__name__).exception(
                            'Problem authenticating with password: %s-%s' % (error.__class__, error))

                    if success:
                        self.passphrase_page(event)
                    else:
                        title = _('Error')
                        error_msg = _("Username/Password incorrect")

                        gui_utils.show_error_dialog(message=error_msg, title=title)
                        event.Veto()
                else:
                    event.Veto()

    @property
    def username(self):
        return self._username.GetValue()

    @property
    def password(self):
        return self._password.GetValue()


class PassphraseWizardPage(WizardPageSimple):
    def __init__(self, parent):
        WizardPageSimple.__init__(self, parent)

        # Attributes
        self.parent = parent
        self._label = wx.StaticText(self, label=_('Give Passphrase'))
        self._entry_passphrase = wx.TextCtrl(self, style=wx.TE_PASSWORD)

        # Layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(self._label, 0, flag=wx.EXPAND | wx.ALL)
        input_sizer.Add(self._entry_passphrase, 0, flag=wx.EXPAND | wx.ALL)

        main_sizer.Add(input_sizer, 1, flag=wx.EXPAND | wx.ALL, border=gui_utils.DEFAULT_BORDER)

        self.SetSizer(main_sizer)
        self.Layout()

        self.Bind(EVT_WIZARD_PAGE_CHANGING, self.store_keys)

    @property
    def passphrase(self):
        return self._entry_passphrase.GetValue()

    def store_keys(self, event):
        try:
            if event.GetDirection():
                # going forward
                if gui_utils.is_valid_input(self.passphrase):
                    getLogger(__name__).debug("storing keys")

                    if not LoginController().store_keys(localbox_client=self.parent.localbox_client,
                                                        pubkey=self.parent.pubkey,
                                                        privkey=self.parent.privkey,
                                                        passphrase=self.passphrase):
                        gui_utils.show_error_dialog(message=_('Wrong passphase'), title=_('Error'))
                        event.Veto()
                        return

                    self.add_new_sync_item()
                else:
                    event.Veto()
        except Exception as err:
            getLogger(__name__).exception('Error storing keys %s' % err)

    def add_new_sync_item(self):
        item = SyncItem(url=self.parent.localbox_client.url,
                        label=self.parent.box_label,
                        direction='sync',
                        path=self.parent.path,
                        user=self.parent.localbox_client.authenticator.username)
        self.parent.ctrl.add(item)
        self.parent.ctrl.save()
        self.parent.event.set()
        getLogger(__name__).debug("new sync saved")


class NewPassphraseWizardPage(PassphraseWizardPage):
    def __init__(self, parent):
        WizardPageSimple.__init__(self, parent)

        # Attributes
        self.parent = parent
        self._label = wx.StaticText(self, label=_("New Passphrase"))
        self._entry_passphrase = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self._label_repeat = wx.StaticText(self, label=_('Repeat passphrase'))
        self._entry_repeat_passphrase = wx.TextCtrl(self, style=wx.TE_PASSWORD)

        # Layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(self._label, 0, flag=wx.EXPAND | wx.ALL)
        input_sizer.Add(self._entry_passphrase, 0, flag=wx.EXPAND | wx.ALL)
        input_sizer.Add(self._label_repeat, 0, flag=wx.EXPAND | wx.ALL)
        input_sizer.Add(self._entry_repeat_passphrase, 0, flag=wx.EXPAND | wx.ALL)

        main_sizer.Add(input_sizer, 1, flag=wx.EXPAND | wx.ALL, border=gui_utils.DEFAULT_BORDER)

        self.SetSizer(main_sizer)
        self.Layout()

        self.Bind(EVT_WIZARD_BEFORE_PAGE_CHANGED, self.store_keys)

    @property
    def repeat_passphrase(self):
        return self._entry_repeat_passphrase.GetValue()

    def store_keys(self, event):
        if event.GetDirection():
            if self._entry_repeat_passphrase.IsShown() and self.passphrase != self.repeat_passphrase:
                gui_utils.show_error_dialog(message=_('Passphrases are not equal'), title=_('Error'))
                event.Veto()
                return

            super(NewPassphraseWizardPage, self).store_keys(event)
