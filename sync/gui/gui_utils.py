import wx, urllib
import requests
from sys import prefix as sys_prefix
from os.path import join, exists
from sysconfig import get_path
from os import getcwd
from cStringIO import StringIO

from sync.__version__ import VERSION_STRING

MAIN_FRAME_SIZE = (650, 540)
MAIN_PANEL_SIZE = (MAIN_FRAME_SIZE[0], 350)
PASSPHRASE_DIALOG_SIZE = (500, 300)
NEW_SYNC_DIALOG_SIZE = (500, 240)
NEW_SYNC_WIZARD_SIZE = (350, 200)
NEW_SYNC_PANEL_SIZE = (NEW_SYNC_DIALOG_SIZE[0], 145)
MAIN_TITLE = 'YourLocalBox %s' % VERSION_STRING
PASSPHRASE_TITLE = 'YourLocalBox %s - Enter Passphrase' % VERSION_STRING
DEFAULT_BORDER = 10


def iconpath(png=False):
    """
    returns the path for the icon related to this widget
    """
    filename = 'localbox.png' if png else 'localbox.ico'

    ico_path = join(sys_prefix, 'localbox', filename)
    if exists(ico_path):
        return ico_path
    else:
        return join('data', 'icon', filename)


def images_path(image_name):
    """
    returns the path for the images used in the interface
    """
    path = join(sys_prefix, 'localbox', 'images', image_name)
    if exists(path):
        return path
    else:
        return join('data', 'images', image_name)


def image_from_url(image_url):
    """
    returns an image object from a url
    """
    try:
        data = urllib.urlopen(image_url).read()
        return wx.ImageFromStream(StringIO(data))
    except Exception as e:
        return wx.Image(iconpath(True), wx.BITMAP_TYPE_PNG)

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


class AddServerDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, "Add new server", size= (400,130))
        self.panel = wx.Panel(self,wx.ID_ANY)

        self.lblurl = wx.StaticText(self.panel, label="URL", pos=(20,20))
        self.server_url = wx.TextCtrl(self.panel, value="http://localhost:5000/", pos=(110,20), size=(250,-1))

        self.saveButton =wx.Button(self.panel, label="Save", pos=(200,60))
        self.closeButton =wx.Button(self.panel, label="Cancel", pos=(300,60))
        self.saveButton.Bind(wx.EVT_BUTTON, self.SaveConnString)
        self.closeButton.Bind(wx.EVT_BUTTON, self.OnQuit)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        self.Show()

    def OnQuit(self, event):
        self.result_label = None
        self.Destroy()

    def SaveConnString(self, event):
        self.result_url = self.server_url.GetValue()

        if is_valid_input(self.result_url):

            try:
                request = requests.get(self.result_url, verify=False, timeout=1).json()
                self.result_label = request.get("label")
                self.result_url = request.get("url")
                self.result_picture = request.get("image")

            except requests.exceptions.ConnectionError:
                show_error_dialog(message="Not available: \"{}\" is not responding.".format(self.result_url), title="Connection Error")
            except requests.exceptions.Timeout:
                show_error_dialog(message="Timeout : This url is not available at the moment", title="Timeout Error")
            except ValueError:
                show_error_dialog(message="Server Error : Not a valid LocalBox server", title="Server Error")
            else:
                self.Destroy()
        else:
            show_error_dialog(message="Please type the server url", title="Input Error")