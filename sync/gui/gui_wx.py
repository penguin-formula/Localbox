import sys
from logging import getLogger
from json import loads

import wx, os
import wx.lib.agw.hyperlink as hl

from sync.controllers import localbox_ctrl
from sync.controllers.account_ctrl import AccountController
from sync.controllers.localbox_ctrl import SyncsController, get_localbox_list, get_server_list, Server
from sync.controllers.login_ctrl import LoginController, InvalidPassphraseError
from sync.controllers.preferences_ctrl import ctrl as preferences_ctrl
from sync.controllers.shares_ctrl import SharesController, ShareItem
import sync.controllers.openfiles_ctrl as openfiles_ctrl
from sync.defaults import DEFAULT_LANGUAGE
from sync.gui import gui_utils
from sync.gui.gui_notifs import EVT_NewHeartbeat, EVT_NewOpenfileCtrl
from sync.gui.event import EVT_POPULATE, PopulateThread
from sync.gui.gui_utils import MAIN_FRAME_SIZE, MAIN_PANEL_SIZE, \
    MAIN_TITLE, DEFAULT_BORDER, PASSPHRASE_DIALOG_SIZE, PASSPHRASE_TITLE
from sync.gui.wizard import NewSyncWizard
from sync.language import LANGUAGES, set_language
from sync.localbox import LocalBox, InvalidLocalBoxPathError, get_localbox_path, remove_decrypted_files
from sync.notif.notifs import Notifs


class LocalBoxApp(wx.App):
    """
    class that extends wx.App and only permits a single running instance.
    """

    def OnInit(self):
        """
        wx.App init function that returns False if the app is already running.
        """
        self.name = "LocalBoxApp-{}".format(wx.GetUserId())
        self.instance = wx.SingleInstanceChecker(self.name)
        if self.instance.IsAnotherRunning():
            wx.MessageBox(
                "An instance of the application is already running",
                "Error",
                wx.OK | wx.ICON_WARNING
            )
            return False
        return True

    
class Gui(wx.Frame):
    def __init__(self, parent, event, main_syncing_thread, init=True):
        super(Gui, self).__init__(parent,
                                  title=MAIN_TITLE,
                                  size=MAIN_FRAME_SIZE,
                                  style=wx.CLOSE_BOX | wx.CAPTION)

        # Attributes
        self._main_syncing_thread = main_syncing_thread
        self.event = event
        self.toolbar_panels = dict()
        self.panel_syncs = LocalboxPanel(self, event, main_syncing_thread)
        self.panel_shares = SharePanel(self)
        self.panel_account = AccountPanel(self)
        self.panel_preferences = PreferencesPanel(self)
        self.panel_bottom = BottomPanel(self)
        self.panel_line = wx.Panel(self)

        line_sizer = wx.BoxSizer(wx.VERTICAL)
        line_sizer.Add(wx.StaticLine(self.panel_line, -1), 0, wx.ALL | wx.EXPAND, border=10)
        self.panel_line.SetSizer(line_sizer)

        self.ctrl = self.panel_syncs.ctrl

        bSizer1 = wx.BoxSizer(wx.VERTICAL)
        bSizer1.Add(self.panel_line, 0, wx.EXPAND, border=10)
        bSizer1.Add(self.panel_syncs, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_shares, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_account, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_preferences, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_bottom, 0, wx.ALIGN_BOTTOM, 10)

        self.SetSizer(bSizer1)

        self.InitUI(init)

        self.show_first_panels()

        self.SetAutoLayout(True)
        self.SetSizer(bSizer1)
        self.Layout()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        if init:
            syncs = SyncsController().load()
            if syncs:
                for i in syncs:
                    PassphraseDialog(self, username=i.user, label=i.label).Show()
            else:
                NewSyncWizard(self.panel_syncs.ctrl, self.panel_syncs.event)

    def Restart(self):
        self.Hide()
        # Find a way to restart frame
        #self.__init__(None, self.event, self._main_syncing_thread, False)

        self.panel_syncs.Destroy()
        self.panel_shares.Destroy()
        self.panel_account.Destroy()
        self.panel_preferences.Destroy()
        # self.panel_bottom.Destroy()
        self.panel_line.Destroy()

        self.panel_syncs = LocalboxPanel(self, self.event, self._main_syncing_thread)
        self.panel_shares = SharePanel(self)
        self.panel_account = AccountPanel(self)
        self.panel_preferences = PreferencesPanel(self)
        self.panel_bottom = BottomPanel(self)
        self.panel_line = wx.Panel(self)

        line_sizer = wx.BoxSizer(wx.VERTICAL)
        line_sizer.Add(wx.StaticLine(self.panel_line, -1), 0, wx.ALL | wx.EXPAND, border=10)
        self.panel_line.SetSizer(line_sizer)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)
        bSizer1.Add(self.panel_line, 0, wx.EXPAND, border=10)
        bSizer1.Add(self.panel_syncs, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_shares, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_account, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_preferences, 0, wx.EXPAND, 10)
        bSizer1.Add(self.panel_bottom, 0, wx.ALIGN_BOTTOM, 10)

        self.toolbar_panels = dict()
        self.InitUI(False)

        self.show_first_panels()

        self.panel_syncs.Hide()
        self.panel_preferences.Show()
        self.ctrl = self.panel_preferences.ctrl

        self.SetAutoLayout(True)
        self.SetSizer(bSizer1)
        self.Layout()

        self.Show(True)


    def InitUI(self, init=True):

        self.add_toolbar(init)

        # icon = wx.Icon()
        # icon.CopyFromBitmap(wx.Bitmap(gui_utils.iconpath(), wx.BITMAP_TYPE_ANY))
        # self.SetIcon(icon)

    def on_close(self, event):
        self.Hide()
        #event.Veto(True)
        print "Closing now", self._main_syncing_thread
        os._exit(0)

    def _create_toolbar_label(self, label, img):
        try:
            return self.toolbar.AddCheckTool(wx.ID_ANY,
                                             label,
                                             wx.Bitmap(gui_utils.images_path(img), wx.BITMAP_TYPE_ANY))
        except TypeError:
            # wxPython 3.0.2
            return self.toolbar.AddCheckLabelTool(wx.ID_ANY,
                                                  label,
                                                  wx.Bitmap(gui_utils.images_path(img), wx.BITMAP_TYPE_ANY))

    def add_toolbar(self, init=True):
        if not init:
            self.toolbar.Destroy()

        self.toolbar = self.CreateToolBar(style=wx.TB_TEXT)

        self.toolbar.AddStretchableSpace()

        bt_toolbar_localboxes = self._create_toolbar_label(img='sync.png', label=_('Syncs'))
        bt_toolbar_shares = self._create_toolbar_label(img='share.png', label=_('Shares'))
        bt_toolbar_account = self._create_toolbar_label(img='user.png', label=_('User'))
        bt_toolbar_preferences = self._create_toolbar_label(img='preferences.png', label=_('Preferences'))

        self.toolbar.AddStretchableSpace()

        self.toolbar.Realize()

        if init:
            self.toolbar.ToggleTool(bt_toolbar_localboxes.Id, True)
        else:
            self.toolbar.ToggleTool(bt_toolbar_preferences.Id, True)

        self.toolbar_panels[bt_toolbar_localboxes.Id] = self.panel_syncs
        self.toolbar_panels[bt_toolbar_shares.Id] = self.panel_shares
        self.toolbar_panels[bt_toolbar_account.Id] = self.panel_account
        self.toolbar_panels[bt_toolbar_preferences.Id] = self.panel_preferences

        self.Bind(wx.EVT_TOOL, self.OnToolbarLocalboxesClick, id=bt_toolbar_localboxes.Id)
        self.Bind(wx.EVT_TOOL, self.OnToolbarLocalboxesClick, id=bt_toolbar_shares.Id)
        self.Bind(wx.EVT_TOOL, self.OnToolbarLocalboxesClick, id=bt_toolbar_account.Id)
        self.Bind(wx.EVT_TOOL, self.OnToolbarLocalboxesClick, id=bt_toolbar_preferences.Id)

    def show_first_panels(self):
        self.panel_syncs.Show()
        self.panel_shares.Hide()
        self.panel_account.Hide()
        self.panel_preferences.Hide()

    def hide_before_login(self):
        self.toolbar.Hide()

        self.panel_line.Hide()
        self.panel_syncs.Hide()
        self.panel_account.Hide()
        self.panel_preferences.Hide()

    def on_successful_login(self):
        self.toolbar.Show()

        self.ctrl = self.panel_syncs.ctrl

        self.panel_line.Show()
        self.panel_syncs.Show()

    def OnQuit(self, e):
        self.Close()

    def OnToolbarLocalboxesClick(self, event):
        for i in range(0, self.toolbar.GetToolsCount()):
            tool = self.toolbar.GetToolByPos(i)
            if tool.Id == event.Id:
                self.toolbar.ToggleTool(tool.Id, True)
            else:
                self.toolbar.ToggleTool(tool.Id, False)

        for item in self.toolbar_panels.items():
            if item[0] == event.Id:
                item[1].Show()
                self.ctrl = item[1].ctrl
            else:
                item[1].Hide()

        self.Layout()

    def on_new_gui_heartbeat(self, msg):
        self.panel_syncs.on_new_gui_heartbeat(msg)

    def on_new_openfile_ctrl(self):
        self.panel_syncs.on_new_openfile_ctrl()


# ----------------------------------- #
# ----       MAIN PANELS         ---- #
# ----------------------------------- #
class LoxPanel(wx.Panel):
    def __init__(self, parent=None, id=None, pos=None, size=None, style=None, name=None):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, size=MAIN_PANEL_SIZE)

        # Make widgets
        self.btn_add = wx.Button(self, label=_('Add'), size=(100, 30))
        self.btn_del = wx.Button(self, label=_('Unsync'), size=(100, 30))

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_btn_add, self.btn_add)
        self.Bind(wx.EVT_BUTTON, self.on_btn_del, self.btn_del)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_list_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_list_item_deselected)

    def _on_list_item_selected(self, wx_event):
        self.btn_del.Enable(True)

    def _on_list_item_deselected(self, wx_event):
        self.btn_del.Enable(self.ctrl.GetSelectedItemCount() > 0)


class LocalboxPanel(LoxPanel):
    """
    Custom Panel containing a ListCtrl to list the localboxes
    """

    def __init__(self, parent, event, main_syncing_thread):
        LoxPanel.__init__(self, parent, id=wx.ID_ANY, size=MAIN_PANEL_SIZE)

        # Attributes
        self._main_syncing_thread = main_syncing_thread
        self.event = event
        self.ctrl = LocalboxListCtrl(self)

        # Make widgets
        self.btn_sync = wx.Button(self, label=_('Sync'), size=(100, 30))
        self.btn_rem = wx.Button(self, label=_('Clean'), size=(100, 30))
        self.btn_ping = wx.Button(self, label=_('Refresh'), size=(100, 30))

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_btn_sync, self.btn_sync)
        self.Bind(wx.EVT_BUTTON, self.on_btn_rem, self.btn_rem)
        self.Bind(wx.EVT_BUTTON, self.on_btn_ping, self.btn_ping)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self._on_list_delete_item)
        self.Bind(wx.EVT_LIST_INSERT_ITEM, self._on_list_insert_item)
        self.Bind(wx.EVT_SHOW, self.on_show)

        # Layout
        self._DoLayout()

        # Setup
        self.ctrl.populate_list()

        self.refresh()

    def _DoLayout(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.ctrl, proportion=1, flag=wx.EXPAND)
        vbox.Add(hbox3, proportion=1, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=10)

        vbox.Add((-1, 25))

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4.Add(self.btn_sync, 0, wx.EXPAND)
        hbox4.Add(self.btn_rem, 0, wx.EXPAND)
        hbox4.Add(self.btn_ping, 0, wx.EXPAND)
        hbox4.Add((0, 0), 1, wx.EXPAND)
        hbox4.Add(self.btn_add, 0, wx.EXPAND)
        hbox4.Add(self.btn_del, 0, wx.EXPAND)
        vbox.Add(hbox4, flag=wx.ALIGN_CENTER | wx.CENTER | wx.EXPAND | wx.EAST | wx.WEST, border=10)

        vbox.Add((-1, 5))

        self.SetSizer(vbox)

        self.btn_del.Enable(False)

        self.refresh()

    def on_btn_sync(self, wx_event):
        labels_to_sync = self.ctrl.selected()
        self._main_syncing_thread.sync(labels_to_sync)

    def on_btn_rem(self, wx_event):
        remove_decrypted_files()

    def on_btn_ping(self, wx_event):
        labels_to_sync = self.ctrl.selected()
        Notifs().reqHeartbeats(labels_to_sync, force_gui_notif=True)

    def on_btn_add(self, wx_event):
        NewSyncWizard(self.ctrl, self.event)

    def on_btn_del(self, wx_event):
        """
        Callback responsible for deleting the configuration of the selected localboxes.
        It also stops the syncing thread for each label.

        :param wx_event:
        :return: None
        """
        confirm = gui_utils.show_confirm_dialog(self, "Do you really want to unsync this server?")
        if confirm:
            map(lambda l: self._main_syncing_thread.stop(l), self.ctrl.delete())

    def _on_list_delete_item(self, wx_event):
        self.btn_sync.Enable(self.ctrl.GetItemCount() > 1)

    def _on_list_insert_item(self, wx_event):
        # On windows, the event which triggers this method happens before the
        # item is added into the list. So, in here, GetItemCount will be equal
        # to 0. Since we are adding an item, we can assume that this method
        # should always be > 0, so we just enable the sync button without
        # verification.
        self.btn_sync.Enable(True)

    def on_show(self, wx_event):
        self.refresh()

    def on_new_gui_heartbeat(self, msg):
        self.ctrl.updateStatus(msg['label'], msg['online'])

    def on_new_openfile_ctrl(self):
        self._on_rem_btn_refresh()

    def refresh(self):
        self.btn_sync.Enable(self.ctrl.GetItemCount() > 0)
        self._on_rem_btn_refresh()

    def _on_rem_btn_refresh(self):
        self.btn_rem.Enable(openfiles_ctrl.load() != {})


class SharePanel(LoxPanel):
    """
    """

    def __init__(self, parent):
        LoxPanel.__init__(self, parent, id=wx.ID_ANY, size=MAIN_PANEL_SIZE)

        # Attributes
        self.ctrl = SharesListCtrl(self)
        self.ctrl_lox = SyncsController()

        # Make widgets
        self.btn_refresh = wx.Button(self, label=_('Refresh'), size=(100, 30))
        self.btn_edit = wx.Button(self, label=_('Edit'), size=(100, 30))

        self.btn_edit.Enable(False)

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_btn_refresh, self.btn_refresh)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self._on_list_delete_item)
        self.Bind(wx.EVT_LIST_INSERT_ITEM, self._on_list_insert_item)

        # Layout
        self._DoLayout()

        # Bind events
        self.Bind(wx.EVT_SHOW, self.on_show)
        self.Bind(EVT_POPULATE, self.on_populate)
        self.Bind(wx.EVT_BUTTON, self.on_btn_edit, self.btn_edit)

    def _DoLayout(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.ctrl, proportion=1, flag=wx.EXPAND)
        vbox.Add(hbox3, proportion=1, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=10)

        vbox.Add((-1, 25))

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4.Add(self.btn_refresh, 0, wx.EXPAND)
        hbox4.Add((0, 0), 1, wx.EXPAND)
        hbox4.Add(self.btn_add, 0, wx.EXPAND)
        hbox4.Add(self.btn_del, 0, wx.EXPAND)
        hbox4.Add(self.btn_edit, 0, wx.EXPAND)
        vbox.Add(hbox4, flag=wx.ALIGN_CENTER | wx.CENTER | wx.EXPAND | wx.EAST | wx.WEST, border=10)

        vbox.Add((-1, 25))

        self.btn_add.Enable(len(self.ctrl_lox) > 0)
        self.btn_del.Enable(self.ctrl.GetSelectedItemCount() > 0)
        self.btn_edit.Enable(self.ctrl.GetSelectedItemCount() > 0)

        self.SetSizer(vbox)

    def on_btn_refresh(self, wx_event):
        return #Disable for now
        #self.sync()

    def on_btn_add(self, wx_event):
        NewShareDialog(self, self.ctrl)

    def on_btn_del(self, wx_event):
        question = _('This will also delete the directory in your LocalBox and for all users. Continue?')
        if gui_utils.show_confirm_dialog(self, question):
            self.ctrl.delete()

    def on_btn_edit(self, wx_event):
        share = None
        for row in range(self.ctrl.GetItemCount()):
            if self.ctrl.IsSelected(row):
                share = self.ctrl.list[row]
                break
        ShareEditDialog(self, share)

    def _on_list_delete_item(self, wx_event):
        pass

    def _on_list_insert_item(self, wx_event):
        pass

    def on_show(self, wx_event=None):
        if self.IsShown():
            self.sync()

    def on_populate(self, wx_event):
        self.ctrl.populate(wx_event.get_value())
        self.btn_del.Enable(self.ctrl.GetSelectedItemCount() > 0)
        self.btn_edit.Enable(self.ctrl.GetSelectedItemCount() > 0)

    def _on_list_item_deselected(self, wx_event):
        super(SharePanel, self)._on_list_item_deselected(wx_event)
        self.btn_edit.Enable(self.ctrl.GetSelectedItemCount() > 0)

    def _on_list_item_selected(self, wx_event):
        super(SharePanel, self)._on_list_item_selected(wx_event)

        # Enable edit button
        user = localbox_ctrl.ctrl.get(self.ctrl.GetItem(self.ctrl.GetFirstSelected()).Text).user
        owner = self.ctrl.ctrl[self.ctrl.GetFirstSelected()].user
        self.btn_edit.Enable(self.ctrl.SelectedItemCount == 1 and owner == user)

    def sync(self):
        self.btn_refresh.Disable()
        worker = PopulateThread(self, self.ctrl.load)
        worker.start()

        #self.btn_refresh.Enable(len(self.ctrl_lox) > 0)
        self.btn_add.Enable(len(self.ctrl_lox) > 0)


class AccountPanel(wx.Panel):
    """

    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, size=MAIN_PANEL_SIZE)

        # Attributes
        self.ctrl = AccountController()

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.label_message = self.get_user_message()

        self.invite_list = self.get_share_list()

        self.action_buttons = self.get_actions_buttons()

        self.__do_layout()

        self.__set_events()

    def get_share_list(self):
        share_list = wx.ListCtrl(self, size=(700, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        share_list.InsertColumn(0, _("ID"), width=50)
        share_list.InsertColumn(1, _("Link Path"), width=300)
        share_list.InsertColumn(2, _("Owner"), width=150)
        share_list.InsertColumn(3, _("Share Status"), width=150)
        return share_list

    def on_show(self, event):
        if self.IsShown():
            self.invite_list.DeleteAllItems()

            invites = self.ctrl.load_invites()
            if len(invites) > 0:
                self.label_message.SetLabelText(_('You have {0} invitations to review.'.format(str(len(invites)))))
                for invite in invites:
                    index = self.invite_list.InsertItem(sys.maxint, str(invite['id']))
                    self.invite_list.SetItem(index, 1, str(invite['link_path']))
                    self.invite_list.SetItem(index, 2, str(invite['user']))
                    self.invite_list.SetItem(index, 3, str(invite['is_active']))
                self.invite_list.Show()
                self.btn_accept.Show()
                self.btn_decline.Show()
            else:
                self.label_message.Destroy()
                self.label_message = self.get_user_message()
                self.sizer.Add(self.label_message, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=DEFAULT_BORDER)
                self.btn_accept.Hide()
                self.btn_decline.Hide()
                self.invite_list.Hide()

    def get_user_message(self):
        username = 'User'
        for item in SyncsController().load():
            username = item.user
            break
        return wx.StaticText(self, label=_('Hello {0}, You have no pending action on your account').format(username))

    def get_actions_buttons(self):
        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_accept = wx.Button(self, label="Accept")
        self.btn_accept.Disable()
        btn_box.Add(self.btn_accept)
        self.btn_decline = wx.Button(self, label="Decline")
        self.btn_decline.Disable()
        btn_box.Add(self.btn_decline)

        return btn_box

    def __do_layout(self):
        self.sizer.Add(self.label_message, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=DEFAULT_BORDER)
        self.sizer.Add(self.invite_list, 2, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=DEFAULT_BORDER)
        self.sizer.Add(self.action_buttons, 3, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=DEFAULT_BORDER)
        self.btn_accept.Enable(self.invite_list.GetSelectedItemCount() > 0)
        self.btn_decline.Enable(self.invite_list.GetSelectedItemCount() > 0)
        self.SetSizer(self.sizer)

    def __set_events(self):
        self.Bind(wx.EVT_SHOW, self.on_show)
        self.Bind(wx.EVT_BUTTON, self.on_accept, id=self.btn_accept.Id)
        self.Bind(wx.EVT_BUTTON, self.on_decline, id=self.btn_decline.Id)
        self.invite_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_list_item_selected)
        self.invite_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_list_item_deselected)

    def _on_list_item_selected(self, wx_event):
        self.btn_accept.Enable(True)
        self.btn_decline.Enable(True)

    def _on_list_item_deselected(self, wx_event):
        self.btn_accept.Enable(self.invite_list.GetSelectedItemCount() > 0)
        self.btn_decline.Enable(self.invite_list.GetSelectedItemCount() > 0)

    def on_decline(self, wx_event):
        question = _('You are about to decline the selected share, are you sure?')
        if gui_utils.show_confirm_dialog(self, question):
            selected_invite = self.get_selected_share()
            share_control = SharesController()
            try:
                share_control.load_invites()
                share_control.delete_invite(selected_invite.Id)
            finally:
                del share_control
                self.on_show(None)

    def get_selected_share(self):
        idx = 0
        while idx > -1:
            idx = self.invite_list.GetNextSelected(-1)
            if idx > -1:
                invite = self.invite_list.GetItem(idx, 0)
                return invite

    def on_accept(self, wx_event):
        question = _('You are about to acceppt the selected share, are you sure?')
        if gui_utils.show_confirm_dialog(self, question):
            selected_invite = self.get_selected_share()
            share_control = SharesController()
            try:
                share_control.load_invites()
                share_control.accept_invite(selected_invite.Id)
            finally:
                del share_control
                self.on_show(None)


class PreferencesPanel(wx.Panel):
    """

    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, size=MAIN_PANEL_SIZE)

        # Attributes
        self.ctrl = preferences_ctrl
        self.parent = parent
        self.language_choice = wx.Choice(self, choices=list(LANGUAGES.keys()))

        self.language_choice.SetSelection(self.language_choice.FindString(
            self.ctrl.prefs.language if (self.ctrl.prefs.language is not None) else DEFAULT_LANGUAGE))

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label=_("Language")),
                  flag=wx.EXPAND | wx.ALL, border=10)
        sizer.Add(self.language_choice, flag=wx.EXPAND | wx.ALL, border=10)

        sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=10)

        self.SetSizer(sizer)

        self.language_choice.Bind(wx.EVT_CHOICE, self.OnChoice)

    def OnChoice(self, event):
        language_selected = self.language_choice.GetString(self.language_choice.GetSelection())
        getLogger(__name__).debug(
            "You selected " + language_selected + " from Choice")
        self.ctrl.prefs.language = language_selected

        set_language(preferences_ctrl.get_language_abbr())
        preferences_ctrl.save()

        self.parent.Restart()

# ----------------------------------- #
# ----       OTHER Panels        ---- #
# ----------------------------------- #
class LoginPanel(wx.Panel):
    def __init__(self, parent):
        super(LoginPanel, self).__init__(parent)

        # Attributes
        self.parent = parent
        self._username = wx.TextCtrl(self)
        self._password = wx.TextCtrl(self, style=wx.TE_PASSWORD)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(wx.StaticText(self, label=_("Username:")),
                        0, wx.ALL | wx.ALIGN_LEFT)
        input_sizer.Add(self._username, 0, wx.ALL | wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label=_("Password:")),
                        0, wx.ALL | wx.ALIGN_LEFT, border=DEFAULT_BORDER)
        input_sizer.Add(self._password, 0, wx.ALL | wx.EXPAND)

        main_sizer.Add(input_sizer, 1, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)

        self.SetSizer(main_sizer)

    def get_username(self):
        return self._username.GetValue()

    def get_password(self):
        return self._password.GetValue()


class FirstLoginPanel(wx.Panel):
    def __init__(self, parent):
        super(FirstLoginPanel, self).__init__(parent)

        # Attributes
        self.parent = parent
        self._ctrl = LoginController()
        self.login_panel = LoginPanel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.welcome_sizer = wx.BoxSizer(wx.VERTICAL)
        self.welcome_sizer.Add(wx.StaticText(self, label=_("WELCOME")), 0, wx.ALL | wx.ALIGN_CENTER)

        self.main_sizer.Add(self.welcome_sizer, 0, wx.ALL | wx.EXPAND)
        self.main_sizer.Add(self.login_panel, 0, wx.ALL | wx.EXPAND)

        self.SetSizer(self.main_sizer)

    @property
    def ctrl(self):
        return self._ctrl


class BottomPanel(wx.Panel):
    """
    Custom Panel containing buttons: "Ok", "Apply" and "Cancel"
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, size=(MAIN_PANEL_SIZE[0], 100))

        # Attributes
        self.parent = parent
        self.ctrl = AccountController()

        # Layout
        self._DoLayout()

    def _DoLayout(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add((0,5))
        main_sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=1)
        main_sizer.Add(self.get_user_message(), 0, wx.ALL | wx.EXPAND, border=1)
        self.SetSizer(main_sizer)

    def get_user_message(self):
        invites = self.ctrl.load_invites()
        if len(invites) > 0:
            label = _('You have {0} invitation(s) to review.'.format(str(len(invites))))
            self.hyperlink = hl.HyperLinkCtrl(self, -1, label=label, pos=(100, 100), URL="#")
            self.hyperlink.AutoBrowse(False)
            self.hyperlink.Bind(hl.EVT_HYPERLINK_LEFT, self.OnClickOk)
            return self.hyperlink
        else:
            username = ''
            for item in SyncsController().load():
                username = item.user
                break
            label = _('Hello {0}, You have no pending action on your account').format(username)
            return wx.StaticText(self, label=label)

    def OnClickOk(self, event):
        getLogger(__name__).debug('OkOnClick')
        # self.parent.ctrl.save()
        # self.parent.Hide()


class NewSharePanel(wx.Panel):
    def __init__(self, parent):
        super(NewSharePanel, self).__init__(parent=parent)

        # Attributes
        self.parent = parent

        self.users = None
        self.list = wx.CheckListBox(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize)
        self._selected_dir = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.btn_select_dir = wx.Button(self, label=_('Select'), size=(95, 30))
        self.btn_select_dir.Disable()
        self.choice = wx.Choice(self, choices=get_localbox_list())

        self._btn_ok = wx.Button(self, id=wx.ID_OK, label=_('Ok'))
        self._btn_close = wx.Button(self, id=wx.ID_CLOSE, label=_('Close'))

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_sel_dir = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=_('Select your LocalBox:')), 0, wx.ALL | wx.EXPAND,
                  border=DEFAULT_BORDER)
        sizer.Add(self.choice, 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        sizer.Add(wx.StaticText(self, label=_('Select directory to share:')), 0, wx.ALL | wx.EXPAND,
                  border=DEFAULT_BORDER)
        sizer_sel_dir.Add(self._selected_dir, 1)
        sizer_sel_dir.Add(self.btn_select_dir, 0)
        sizer.Add(sizer_sel_dir, 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        sizer.Add(wx.StaticText(self, label=_('Choose the users you want to share with:')), 0, wx.ALL | wx.EXPAND,
                  border=DEFAULT_BORDER)
        sizer.Add(self.list, proportion=1, flag=wx.EXPAND | wx.ALL, border=DEFAULT_BORDER)

        btn_szr = wx.StdDialogButtonSizer()

        btn_szr.AddButton(self._btn_ok)
        btn_szr.AddButton(self._btn_close)

        btn_szr.Realize()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(btn_szr, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticText(self, label=''), 0, wx.ALL | wx.EXPAND)

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.select_dir, self.btn_select_dir)
        self.Bind(wx.EVT_BUTTON, self.OnClickOk, id=self._btn_ok.Id)
        self.Bind(wx.EVT_BUTTON, self.OnClickClose, id=self._btn_close.Id)
        self.choice.Bind(wx.EVT_CHOICE, self.OnChoice)
        self.Bind(EVT_POPULATE, self.on_populate)

        self.SetSizer(main_sizer)

    def OnClickOk(self, event):
        path = self._selected_dir.GetValue()
        lox_label = self.choice.GetString(self.choice.GetSelection())

        user_list = filter(lambda x: x['username'] in self.list.CheckedStrings, self.users)
        if gui_utils.is_valid_input(path) and len(user_list) > 0:
            share_path = path.replace(self.localbox_path, '', 1)

            if self.localbox_client.create_share(localbox_path=share_path,
                                                 user_list=user_list):
                ShareItem(user=self.localbox_client.username, path=share_path, url=self.localbox_client.url,
                          label=lox_label)
                SharesController().load()  # force load to get the ids from the server
                self.parent.ctrl.populate(SharesController().get_list())
            else:
                gui_utils.show_error_dialog(
                    _('Server error creating the share, there may already be a share with this name'), _('Error'))
            self.parent.Destroy()

    def OnClickClose(self, event):
        self.parent.OnClickClose(event)

    def OnChoice(self, event):
        self.btn_select_dir.Enable()
        self.list.Clear()
        worker = PopulateThread(self, self.localbox_client.get_all_users)
        worker.start()

    def select_dir(self, wx_event):
        try:
            path = gui_utils.select_directory(cwd=self.localbox_path)
            if path:
                path = get_localbox_path(SyncsController().get(self.selected_localbox).path, path)
                if path.count('/') < 2:
                    # get meta to verify if path is a valid LocalBox path
                    # this will later problems, because for the sharing to work the files must exist in the server
                    self.localbox_client.get_meta(path)
                    self._selected_dir.SetValue(path)
                else:
                    gui_utils.show_error_dialog(_('Can only create share for root directories'), _('Error'))
                    return

        except InvalidLocalBoxPathError:
            gui_utils.show_error_dialog(_(
                'Invalid LocalBox path. Please make sure that you are selecting a directory inside LocalBox and '
                'that the directory has been uploaded. Or try a different directory.'), 'Error')

    def on_populate(self, wx_event):
        self.users = wx_event.get_value()
        map(lambda x: self.list.Append(x['username']),
            filter(lambda u: u['username'] != self.localbox_client.username, self.users))

    @property
    def localbox_client(self):
        localbox_item = localbox_ctrl.ctrl.get(self.selected_localbox)
        return LocalBox(url=localbox_item.url, label=localbox_item.label, path=localbox_item.path)

    @property
    def localbox_path(self):
        return localbox_ctrl.ctrl.get(self.localbox_client.label).path

    @property
    def selected_localbox(self):
        return self.choice.GetString(self.choice.GetSelection())


class ShareEditPanel(wx.Panel):
    def __init__(self, parent, share):
        super(ShareEditPanel, self).__init__(parent=parent)

        # Attributes
        self.parent = parent
        self.share = share

        self.list = wx.CheckListBox(self, wx.ID_ANY, wx.DefaultPosition,
                                    size=(self.GetSize()[0], 280))  # wx.DefaultSize)
        self._selected_dir = wx.TextCtrl(self, style=wx.TE_READONLY)

        self._btn_ok = wx.Button(self, id=wx.ID_OK, label=_('Ok'))
        self._btn_close = wx.Button(self, id=wx.ID_CLOSE, label=_('Close'))
        self._btn_remove = wx.Button(self, id=wx.ID_REMOVE, label=_('Remove'))
        self._btn_add = wx.Button(self, id=wx.ID_ADD, label=_('Add'))

        self._btn_remove.Enable(False)
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_sel_dir = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=_('Share:')), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        self._selected_dir.SetValue(self.share.path)
        sizer_sel_dir.Add(self._selected_dir, 1)
        sizer.Add(sizer_sel_dir, 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        sizer.Add(wx.StaticText(self, label=_('You are sharing with:')), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        sizer.Add(self.list, proportion=1, flag=wx.EXPAND | wx.ALL, border=DEFAULT_BORDER)

        sizer_list_actions = wx.BoxSizer(wx.HORIZONTAL)
        sizer_list_actions.Add(self._btn_remove)
        sizer_list_actions.Add(self._btn_add)
        sizer.Add(sizer_list_actions, proportion=1, flag=wx.EXPAND | wx.ALL,
                  border=DEFAULT_BORDER)

        btn_szr = wx.StdDialogButtonSizer()

        btn_szr.AddButton(self._btn_ok)
        btn_szr.AddButton(self._btn_close)

        btn_szr.Realize()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(btn_szr, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticText(self, label=''), 0, wx.ALL | wx.EXPAND)

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnClickOk, id=self._btn_ok.Id)
        self.Bind(wx.EVT_BUTTON, self.OnClickClose, id=self._btn_close.Id)
        self.Bind(wx.EVT_BUTTON, self.on_click_remove, id=self._btn_remove.Id)
        self.Bind(wx.EVT_BUTTON, self.on_click_add, id=self._btn_add.Id)
        self.Bind(wx.EVT_CHECKLISTBOX, self.on_check, id=self.list.Id)

        self.SetSizer(main_sizer)

        self.on_populate()

    def OnClickOk(self, event):
        self.parent.OnClickClose(event)

    def OnClickClose(self, event):
        self.parent.OnClickClose(event)

    def on_click_remove(self, wx_event):
        user_list = filter(lambda x: x not in self.list.CheckedStrings, self.list.Strings)
        self.localbox_client.edit_share_users(self.share, user_list)
        self.on_populate()

    def on_click_add(self, wx_event):
        user_list = self.list.Strings
        ShareAddUserDialog(self, self.share, user_list)

    def on_check(self, wx_event):
        self._btn_remove.Enable(len(self.list.CheckedStrings) > 0)

    def on_populate(self):
        self.list.Clear()
        result = self.localbox_client.get_share_user_list(self.share.id)
        lst = result["receivers"]
        map(lambda x: self.list.Append(x['username']), lst)

    @property
    def localbox_client(self):
        localbox_item = localbox_ctrl.ctrl.get(self.share.label)
        return LocalBox(url=localbox_item.url, label=localbox_item.label, path=localbox_item.path)


class ShareAddUserPanel(wx.Panel):
    def __init__(self, parent, share, current_share_users):
        super(ShareAddUserPanel, self).__init__(parent=parent)

        # Attributes
        self.parent = parent
        self.share = share
        self.current_share_users = current_share_users

        self.list = wx.CheckListBox(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize)

        self._btn_ok = wx.Button(self, id=wx.ID_OK, label=_('Ok'))
        self._btn_close = wx.Button(self, id=wx.ID_CLOSE, label=_('Close'))

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=_('Choose users to add to the share:')), 0, wx.ALL | wx.EXPAND,
                  border=DEFAULT_BORDER)
        sizer.Add(self.list, proportion=1, flag=wx.EXPAND | wx.ALL, border=DEFAULT_BORDER)

        btn_szr = wx.StdDialogButtonSizer()

        btn_szr.AddButton(self._btn_ok)
        btn_szr.AddButton(self._btn_close)

        btn_szr.Realize()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(btn_szr, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticText(self, label=''), 0, wx.ALL | wx.EXPAND)

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnClickOk, id=self._btn_ok.Id)
        self.Bind(wx.EVT_BUTTON, self.OnClickClose, id=self._btn_close.Id)

        self.SetSizer(main_sizer)

        self.on_populate()

    def OnClickOk(self, event):
        if len(self.list.CheckedStrings) > 0:
            users = list(set(self.list.CheckedStrings).union(set(self.current_share_users)))
            self.localbox_client.edit_share_users(self.share, users)
        self.parent.OnClickClose(event)

    def OnClickClose(self, event):
        self.parent.OnClickClose(event)

    def on_populate(self):
        self.list.Clear()
        result = self.localbox_client.get_all_users()
        all_users = [u['username'] for u in result]
        user = localbox_ctrl.ctrl.get(self.share.label).user
        map(lambda x: self.list.Append(x),
            filter(lambda x: x != user,
                   set(all_users).difference(set(self.current_share_users))))

    @property
    def localbox_client(self):
        localbox_item = localbox_ctrl.ctrl.get(self.share.label)
        return LocalBox(url=localbox_item.url, label=localbox_item.label, path=localbox_item.path)


class PasshphrasePanel(wx.Panel):
    def __init__(self, parent, username, label):
        super(PasshphrasePanel, self).__init__(parent=parent)

        self.parent = parent
        self._username = username
        self._label = label
        self._label_template = _('Hi {0}, please provide the passphrase for unlocking {1}')
        label_text = self._label_template.format(username, label)
        self.label = wx.StaticText(self, label=label_text)
        self.label.Wrap(parent.Size[0] - 50)
        self._passphrase = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self._btn_ok = wx.Button(self, id=wx.ID_OK, label=_('Ok'))
        #self._btn_close = wx.Button(self, id=wx.ID_CLOSE, label=_('Close'))

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.label, 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        sizer.Add(self._passphrase, 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)

        btn_szr = wx.StdDialogButtonSizer()

        btn_szr.AddButton(self._btn_ok)
        #btn_szr.AddButton(self._btn_close)

        btn_szr.Realize()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, border=DEFAULT_BORDER)
        main_sizer.Add(btn_szr, border=DEFAULT_BORDER)
        main_sizer.Add(wx.StaticText(self, label=''), 0, wx.ALL | wx.EXPAND)

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnClickOk, id=self._btn_ok.Id)
        #self.Bind(wx.EVT_BUTTON, self.OnClickClose, id=self._btn_close.Id)
        self._passphrase.Bind(wx.EVT_KEY_DOWN, self.OnEnter)

        self.SetSizer(main_sizer)

    def OnClickOk(self, event):
        if event.Id == self._btn_ok.Id:
            if not self._passphrase.Value:
                gui_utils.show_error_dialog(message=_('Please type a passphrase'), title=_('Error'))
                return None
            try:
                LoginController().store_passphrase(passphrase=self._passphrase.Value,
                                                   user=self._username,
                                                   label=self._label)
                self.parent.Destroy()
            except InvalidPassphraseError:
                gui_utils.show_error_dialog(message=_('Wrong passphase'), title=_('Error'))
            except Exception as err:
                getLogger(__name__).exception(err)
                gui_utils.show_error_dialog(message=_('Could not authenticate. Please contact the administrator'),
                                            title=_('Error'))

    def OnEnter(self, event):
        """"""
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN or keycode == wx.WXK_NUMPAD_ENTER:
            event.Id = self._btn_ok.Id
            return self.OnClickOk(event)
        event.Skip()

    def OnClickClose(self, event):
        self.parent.OnClickClose(event)


# ----------------------------------- #
# ----     GUI Controllers       ---- #
# ----------------------------------- #
class LocalboxListCtrl(wx.ListCtrl):
    """
    This class behaves like a bridge between the GUI components and the real syncs controller.
    """

    def __init__(self, parent):
        super(LocalboxListCtrl, self).__init__(parent,
                                               style=wx.LC_REPORT)

        self.ctrl = SyncsController()

        # Add three columns to the list
        self.InsertColumn(0, _("Label"))
        self.InsertColumn(1, _("Path"))
        self.InsertColumn(2, _("Status"))
        self.InsertColumn(3, _("URL"))

        self.SetColumnWidth(0, 100)
        self.SetColumnWidth(1, 250)
        self.SetColumnWidth(2, 100)
        self.SetColumnWidth(3, 200)

    def populate_list(self):
        """
        Read the syncs list from the controller
        """
        for item in self.ctrl.load():
            self.Append((item.label, item.path, item.status, item.url))

    def selected(self):
        idx = 0
        prev = -1
        labels_selected = []

        for i in range(self.GetSelectedItemCount()):
            idx = self.GetNextSelected(prev)
            labels_selected.append(self.ctrl.getLabel(idx))
            prev = idx

        return labels_selected

    def add(self, item):
        getLogger(__name__).debug('%s: Add item %s' % (self.__class__.__name__, item))
        self.Append((item.label, item.path, item.status, item.url))
        self.ctrl.add(item)

    def delete(self):
        """
        Delete the configuration for the selected localboxes.

        :return: the list with the labels of localboxes deleted.
        """
        idx = 0
        labels_removed = []
        while idx > -1:
            idx = self.GetNextSelected(-1)

            if idx > -1:
                getLogger(__name__).debug('%s: Delete item #%d' % (self.__class__.__name__, idx))
                self.DeleteItem(idx)
                label = self.ctrl.delete(idx)
                labels_removed.append(label)

        map(lambda l: SharesController().delete_for_label(l), labels_removed)
        self.save()
        return labels_removed

    def save(self):
        getLogger(__name__).info('%s: ctrl save()' % self.__class__.__name__)
        SharesController().save()
        self.ctrl.save()

    def updateStatus(self, label, status):
        for i in range(self.GetItemCount()):
            item_label = self.GetItemText(i, 0)
            item_text = self.GetItem(i, 2)

            if item_label == label:
                item_text.SetText("Online" if status else "Offline")
                self.SetItem(item_text)
                break

    def getServers(self):
        return get_server_list()

    def addServer(self, label, url, picture):
        server = Server(label, picture, url)
        server.save()

class LoxListCtrl(wx.ListCtrl):
    """
    This class behaves like a bridge between the GUI components and the real controller.
    """
    list = None

    def __init__(self, parent, ctrl):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        self.ctrl = ctrl

    def delete(self):
        idx = 0
        removed = []
        while idx > -1:
            idx = self.GetNextSelected(-1)

            if idx > -1:
                getLogger(__name__).debug('%s: Delete item #%d' % (self.__class__.__name__, idx))
                self.DeleteItem(idx)
                label = self.ctrl.delete(idx)
                removed.append(label)

        self.save()
        return removed

    def save(self):
        getLogger(__name__).info('%s: ctrl save()' % self.__class__.__name__)
        self.ctrl.save()

    def populate(self, lst=None):
        self.DeleteAllItems()
        self.list = lst

    def load(self):
        return self.ctrl.load()


class SharesListCtrl(LoxListCtrl):
    """
    This class behaves like a bridge between the GUI components and the real syncs controller.

    """

    def __init__(self, parent):
        super(SharesListCtrl, self).__init__(parent, SharesController())

        self.InsertColumn(0, _("Label"))
        self.InsertColumn(1, _("Owner"))
        self.InsertColumn(2, _("Path"))
        self.InsertColumn(3, _("URL"))

        self.SetColumnWidth(0, 150)
        self.SetColumnWidth(1, 150)
        self.SetColumnWidth(2, 200)
        self.SetColumnWidth(3, 400)

    def populate(self, lst=None):
        super(SharesListCtrl, self).populate(lst)
        map(lambda i: self.Append([i.label, i.user, i.path, i.url]), lst)


# ----------------------------------- #
# ----         Dialogs           ---- #
# ----------------------------------- #
class LoginDialog(wx.Dialog):
    def __init__(self, parent):
        super(LoginDialog, self).__init__(parent=parent)

        # Attributes
        self.panel = LoginPanel(self)
  
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetInitialSize()


class PassphraseDialog(wx.Dialog):
    def __init__(self, parent, username, label):
        super(PassphraseDialog, self).__init__(parent=parent,
                                               title=PASSPHRASE_TITLE,
                                               size=PASSPHRASE_DIALOG_SIZE,
                                               style=wx.CAPTION)

        # Attributes
        self.panel = PasshphrasePanel(self, username, label)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.passphrase_continue = False

        self.InitUI()

        self.Bind(wx.EVT_CLOSE, self.OnClickClose)

    def InitUI(self):
        self.main_sizer.Add(self.panel)

        self.Layout()
        self.Center()
        self.Show()

    def OnClickClose(self, wx_event):
        self.Refresh()

    @staticmethod
    def show(username, label):
        PassphraseDialog(None, username=username, label=label)


class NewShareDialog(wx.Dialog):
    def __init__(self, parent, ctrl):
        super(NewShareDialog, self).__init__(parent=parent,
                                             title=_('Create Share'),
                                             size=(500, 600),
                                             style=wx.CLOSE_BOX | wx.CAPTION)

        self.ctrl = ctrl
        # Attributes
        self.panel = NewSharePanel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.InitUI()

        self.Bind(wx.EVT_CLOSE, self.OnClickClose)

    def InitUI(self):
        self.main_sizer.Add(self.panel)

        self.Layout()
        self.Center()
        self.Show()

    def OnClickClose(self, wx_event):
        self.Destroy()


class ShareEditDialog(wx.Dialog):
    def __init__(self, parent, share):
        super(ShareEditDialog, self).__init__(parent=parent,
                                              title=_('Edit Share'),
                                              size=(500, 700),
                                              style=wx.CLOSE_BOX | wx.CAPTION)

        # Attributes
        self.panel = ShareEditPanel(self, share=share)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.InitUI()

        self.Bind(wx.EVT_CLOSE, self.OnClickClose)

    def InitUI(self):
        self.main_sizer.Add(self.panel)

        self.Layout()
        self.Center()
        self.Show()

    def OnClickClose(self, wx_event):
        self.Destroy()


class ShareAddUserDialog(wx.Dialog):
    def __init__(self, parent, share, current_share_users):
        super(ShareAddUserDialog, self).__init__(parent=parent,
                                                 title=_('Add User to Share'),
                                                 size=(500, 600),
                                                 style=wx.CLOSE_BOX | wx.CAPTION)

        # Attributes
        self.panel = ShareAddUserPanel(self, share=share, current_share_users=current_share_users)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.parent = parent

        self.InitUI()

        self.Bind(wx.EVT_CLOSE, self.OnClickClose)

    def InitUI(self):
        self.main_sizer.Add(self.panel)

        self.Layout()
        self.Center()
        self.Show()

    def OnClickClose(self, wx_event):
        self.parent.on_populate()
        self.Destroy()
