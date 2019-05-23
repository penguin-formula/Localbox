import wx
from sys import prefix as sys_prefix
from os.path import join, exists
from sysconfig import get_path
from os import getcwd

from sync.__version__ import VERSION_STRING

MAIN_FRAME_SIZE = (700, 550)
MAIN_PANEL_SIZE = (MAIN_FRAME_SIZE[0], 350)
PASSPHRASE_DIALOG_SIZE = (500, 300)
NEW_SYNC_DIALOG_SIZE = (500, 240)
NEW_SYNC_WIZARD_SIZE = (500, 100)
NEW_SYNC_PANEL_SIZE = (NEW_SYNC_DIALOG_SIZE[0], 145)
MAIN_TITLE = 'YourLocalBox %s' % VERSION_STRING
PASSPHRASE_TITLE = 'YourLocalBox %s - Enter Passphrase' % VERSION_STRING
DEFAULT_BORDER = 10


def iconpath():
    """
    returns the path for the icon related to this widget
    """
    ico_path = join(sys_prefix, 'localbox', 'localbox.ico')
    if exists(ico_path):
        return ico_path
    else:
        return join('data', 'icon', 'localbox.ico')


def images_path(image_name):
    """
    returns the path for the images used in the interface
    """
    path = join(sys_prefix, 'localbox', 'images', image_name)
    if exists(path):
        return path
    else:
        return join('data', 'images', image_name)


def is_valid_input(value):
    return value is not None and value.strip()


def show_error_dialog(message, title, standalone=False):
    if standalone:
        app = wx.App()
    wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR)


def show_confirm_dialog(parent, question, caption=_('Are you sure?')):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result


def select_directory(cwd=getcwd()):
    dialog = wx.DirDialog(None, _("Choose a file"), style=wx.DD_DEFAULT_STYLE, defaultPath=cwd,
                          pos=(10, 10))
    if dialog.ShowModal() == wx.ID_OK:
        selected_dir = dialog.GetPath()
        return selected_dir

    dialog.Destroy()


def get_user_input(title, message, frame=False):
    '''
        Creates a input field box, used to capture user data
    '''
    if not frame:
        app = wx.App()

        frame = wx.Frame(None, -1, 'win.py')
        frame.SetDimensions(0,0,200,50)

    dlg = wx.TextEntryDialog(frame, message, title)

    if dlg.ShowModal() == wx.ID_OK:
        dlg.Destroy()
        return dlg.GetValue()
    
    dlg.Destroy()


def get_user_secret_input(title, message, frame=False):
    '''
        Creates a input secret field box, used to capture secret user data
    '''
    if not frame:
        app = wx.App()

        frame = wx.Frame(None, -1, 'win.py')
        frame.SetDimensions(0,0,200,50)

    dlg = wx.PasswordEntryDialog(frame, message, title)

    if dlg.ShowModal() == wx.ID_OK:
        dlg.Destroy()
        return dlg.GetValue()
    
    dlg.Destroy()