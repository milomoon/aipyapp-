import wx
import importlib.resources as resources

from .. import __version__, T
from ..aipy.config import CONFIG_DIR

class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="关于爱派", size=(400, 300))
        
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Logo and title
        logo_panel = wx.Panel(self)
        logo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        with resources.path("aipyapp.res", "aipy.ico") as icon_path:
            icon = wx.Icon(str(icon_path), wx.BITMAP_TYPE_ICO)
            bmp = wx.Bitmap()
            bmp.CopyFromIcon(icon)
            # Scale the bitmap to a more appropriate size
            scaled_bmp = wx.Bitmap(bmp.ConvertToImage().Scale(48, 48, wx.IMAGE_QUALITY_HIGH))
            logo_sizer.Add(wx.StaticBitmap(logo_panel, -1, scaled_bmp), 0, wx.ALL | wx.ALIGN_CENTER, 5)
            
        title = wx.StaticText(logo_panel, -1, "爱派")
        title.SetFont(wx.Font(24, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        logo_sizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        logo_panel.SetSizer(logo_sizer)
        vbox.Add(logo_panel, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # Version and description
        version = wx.StaticText(self, -1, f"版本: {__version__}")
        vbox.Add(version, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        description = wx.StaticText(self, -1, "爱派是一个智能助手，可以帮助您完成各种任务。")
        vbox.Add(description, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        tm = parent.tm
        # Configuration directory
        config_dir = wx.StaticText(self, -1, f"当前配置目录: {CONFIG_DIR}")
        vbox.Add(config_dir, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        work_dir = wx.StaticText(self, -1, f"当前工作目录: {tm.workdir}")
        vbox.Add(work_dir, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        # Add flexible space to push copyright and button to bottom
        vbox.AddStretchSpacer()
        
        # Copyright and OK button at bottom
        bottom_panel = wx.Panel(self)
        bottom_sizer = wx.BoxSizer(wx.VERTICAL)
        
        copyright = wx.StaticText(bottom_panel, -1, "© 2025 爱派团队")
        bottom_sizer.Add(copyright, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        ok_button = wx.Button(bottom_panel, wx.ID_OK, "确定")
        bottom_sizer.Add(ok_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        bottom_panel.SetSizer(bottom_sizer)
        vbox.Add(bottom_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(vbox)
        self.Centre() 