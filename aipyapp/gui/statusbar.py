import os
import sys
import subprocess
import wx

from .. import T

class CStatusBar(wx.StatusBar):
    def __init__(self, parent):
        super().__init__(parent, style=wx.STB_DEFAULT_STYLE)
        self.parent = parent
        self.SetFieldsCount(3)
        self.SetStatusWidths([-1, 30, 80])

        self.tm = parent.tm
        self.current_llm = self.tm.clients.names['default']
        self.enabled_llm = list(self.tm.clients.names['enabled'])
        self.menu_items = self.enabled_llm
        self.radio_group = []

        self.folder_button = wx.StaticBitmap(self, -1, wx.ArtProvider.GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_MENU))
        self.folder_button.Bind(wx.EVT_LEFT_DOWN, self.on_open_work_dir)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.SetStatusText(f"{self.current_llm} ▾", 2)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)

    def on_size(self, event):
        rect = self.GetFieldRect(1)
        self.folder_button.SetPosition((rect.x + 5, rect.y + 2))
        event.Skip()

    def on_click(self, event):
        rect = self.GetFieldRect(2)
        if rect.Contains(event.GetPosition()):
            self.show_menu()

    def show_menu(self):
        self.current_menu = wx.Menu()
        self.radio_group = []
        for label in self.menu_items:
            item = wx.MenuItem(self.current_menu, wx.ID_ANY, label, kind=wx.ITEM_RADIO)
            self.current_menu.Append(item)
            self.radio_group.append(item)
            self.Bind(wx.EVT_MENU, self.on_menu_select, item)
            if label == self.current_llm:
                item.Check()
        rect = self.GetFieldRect(2)
        pos = self.ClientToScreen(rect.GetBottomLeft())
        self.PopupMenu(self.current_menu, self.ScreenToClient(pos))

    def on_menu_select(self, event):
        item = self.current_menu.FindItemById(event.GetId())
        label = item.GetItemLabel()
        if self.tm.use(label):
            self.current_llm = label
            self.SetStatusText(f"{label} ▾", 2)
        else:
            wx.MessageBox(f"LLM {label} 不可用", "警告", wx.OK|wx.ICON_WARNING)

    def on_open_work_dir(self, event):
        """打开工作目录"""
        work_dir = self.tm.workdir
        if os.path.exists(work_dir):
            if sys.platform == 'win32':
                os.startfile(work_dir)
            elif sys.platform == 'darwin':
                subprocess.call(['open', work_dir])
            else:
                subprocess.call(['xdg-open', work_dir])
        else:
            wx.MessageBox(T('Work directory does not exist'), T("Error"), wx.OK | wx.ICON_ERROR) 