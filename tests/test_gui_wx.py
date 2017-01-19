from __future__ import \
    absolute_import  # to avoid: RuntimeWarning: Parent module 'test' not found while handling absolute import

import unittest


class TestGuiWx(unittest.TestCase):
    def _get_frame(self):
        from sync.gui.gui_wx import Gui
        frame = Gui(None, None, None)
        self.assertIsNotNone(frame)

        return frame

    def setUp(self):
        from sync.gui.gui_wx import LocalBoxApp
        self.app = LocalBoxApp()

    def tearDown(self):
        pass


class TestLocalBoxPanel(TestGuiWx):
    """
    Test :py:class:`sync.gui.gui_wx.SyncsPanel`.

    """

    def test_del_button_no_selection(self):
        """
        Test the state (enabled / disabled) of the del button when a item is selected.

        :return:
        """
        from mock import MagicMock

        frame = self._get_frame()

        frame.panel_syncs.ctrl.GetSelectedItemCount = MagicMock(return_value=0)
        frame.panel_syncs._DoLayout()

        self.assertFalse(frame.panel_syncs.btn_del.Enabled)


class TestSharePanel(TestGuiWx):
    """
    Test :py:class:`sync.gui.gui_wx.SharePanel`.

    """

    def test_add_button_no_localbox(self):
        """
        Test the state (enabled / disabled) of the add button when there are NO LocalBoxes configured.

        :return:
        """
        from sync.controllers.localbox_ctrl import SyncsController
        from mock import MagicMock

        frame = self._get_frame()

        SyncsController.__len__ = MagicMock(return_value=0)
        frame.panel_shares._DoLayout()

        self.assertFalse(frame.panel_shares.btn_add.Enabled)

    def test_add_button_with_localbox(self):
        """
        Test the state (enabled / disabled) of the add button when there is at least one LocalBox configured.

        :return:
        """
        from sync.controllers.localbox_ctrl import SyncsController
        from mock import MagicMock

        frame = self._get_frame()

        SyncsController.__len__ = MagicMock(return_value=1)
        frame.panel_shares._DoLayout()

        self.assertTrue(frame.panel_shares.btn_add.Enabled)

    def test_del_button_no_selection(self):
        """
        Test the state (enabled / disabled) of the del button on the SharePanel when a item is selected.

        :return:
        """
        from mock import MagicMock

        frame = self._get_frame()

        frame.panel_shares.ctrl.GetSelectedItemCount = MagicMock(return_value=0)
        frame.panel_shares._DoLayout()

        self.assertFalse(frame.panel_shares.btn_del.Enabled)

    def test_del_button_with_selection(self):
        """
        Test the state (enabled / disabled) of the del button on the SharePanel when a item is selected.

        :return:
        """
        from mock import MagicMock

        frame = self._get_frame()

        frame.panel_shares.ctrl.GetSelectedItemCount = MagicMock(return_value=2)
        frame.panel_shares._DoLayout()

        self.assertTrue(frame.panel_shares.btn_del.Enabled)


if __name__ == '__main__':
    unittest.main()
