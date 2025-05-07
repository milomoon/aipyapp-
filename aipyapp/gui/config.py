#!/usr/bin/env python
#coding: utf-8

import os
import wx
from wx import DirDialog, FD_SAVE, FD_OVERWRITE_PROMPT
from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN, FS_LEFT, FS_RIGHT, FS_CENTRE, FS_READONLY

from .. import T

class ConfigDialog(wx.Dialog):
    def __init__(self, parent, settings):
        super().__init__(parent, title=T("Configuration"), size=(500, 450))
        
        self.settings = settings
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Main panel with content
        main_panel = wx.Panel(self)
        main_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        main_vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Work directory group
        work_dir_box = wx.StaticBox(main_panel, -1, T("Work Directory"))
        work_dir_box.SetBackgroundColour(wx.Colour(245, 245, 245))
        work_dir_sizer = wx.StaticBoxSizer(work_dir_box, wx.VERTICAL)
        
        work_dir_panel = wx.Panel(main_panel)
        work_dir_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        work_dir_inner_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.work_dir_text = wx.TextCtrl(work_dir_panel, -1, settings.workdir, style=wx.TE_READONLY)
        self.work_dir_text.SetBackgroundColour(wx.Colour(255, 255, 255))
        work_dir_inner_sizer.Add(self.work_dir_text, 1, wx.ALL | wx.EXPAND, 5)
        
        browse_button = wx.Button(work_dir_panel, -1, T("Browse..."))
        browse_button.SetBackgroundColour(wx.Colour(255, 255, 255))
        browse_button.Bind(wx.EVT_BUTTON, self.on_browse_work_dir)
        work_dir_inner_sizer.Add(browse_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        work_dir_panel.SetSizer(work_dir_inner_sizer)
        work_dir_sizer.Add(work_dir_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # Add hint about creating new directory
        hint_text = wx.StaticText(main_panel, -1, T("You can create a new directory in the file dialog"))
        hint_text.SetForegroundColour(wx.Colour(128, 128, 128))
        work_dir_sizer.Add(hint_text, 0, wx.LEFT | wx.BOTTOM, 5)
        
        main_vbox.Add(work_dir_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Settings group
        settings_box = wx.StaticBox(main_panel, -1, T("Settings"))
        settings_box.SetBackgroundColour(wx.Colour(245, 245, 245))
        settings_sizer = wx.StaticBoxSizer(settings_box, wx.VERTICAL)
        
        # Max tokens slider
        tokens_panel = wx.Panel(main_panel)
        tokens_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        tokens_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        tokens_label = wx.StaticText(tokens_panel, -1, T("Max Tokens") + ":")
        tokens_sizer.Add(tokens_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.tokens_slider = wx.Slider(tokens_panel, -1, 
                                     settings.get('max_tokens', 8192),
                                     minValue=64,
                                     maxValue=128*1024,
                                     style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.tokens_slider.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.tokens_slider.SetTickFreq(1000)
        self.tokens_slider.SetForegroundColour(wx.Colour(0, 0, 0))
        tokens_sizer.Add(self.tokens_slider, 1, wx.ALL | wx.EXPAND, 5)
        
        self.tokens_text = wx.StaticText(tokens_panel, -1, str(self.tokens_slider.GetValue()))
        tokens_sizer.Add(self.tokens_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        tokens_panel.SetSizer(tokens_sizer)
        settings_sizer.Add(tokens_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # Timeout slider
        timeout_panel = wx.Panel(main_panel)
        timeout_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        timeout_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        timeout_label = wx.StaticText(timeout_panel, -1, T("Timeout (seconds)") + ":")
        timeout_sizer.Add(timeout_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.timeout_slider = wx.Slider(timeout_panel, -1, 
                                      int(settings.get('timeout', 0)),
                                      minValue=0,
                                      maxValue=120,
                                      style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.timeout_slider.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.timeout_slider.SetTickFreq(30)
        self.timeout_slider.SetForegroundColour(wx.Colour(0, 0, 0))
        timeout_sizer.Add(self.timeout_slider, 1, wx.ALL | wx.EXPAND, 5)
        
        self.timeout_text = wx.StaticText(timeout_panel, -1, str(self.timeout_slider.GetValue()))
        timeout_sizer.Add(self.timeout_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        timeout_panel.SetSizer(timeout_sizer)
        settings_sizer.Add(timeout_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # Max rounds slider
        rounds_panel = wx.Panel(main_panel)
        rounds_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        rounds_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        rounds_label = wx.StaticText(rounds_panel, -1, T("Max Rounds") + ":")
        rounds_sizer.Add(rounds_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.rounds_slider = wx.Slider(rounds_panel, -1,
                                     settings.get('max_rounds', 16),
                                     minValue=1,
                                     maxValue=64,
                                     style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.rounds_slider.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.rounds_slider.SetTickFreq(8)
        self.rounds_slider.SetForegroundColour(wx.Colour(0, 0, 0))
        rounds_sizer.Add(self.rounds_slider, 1, wx.ALL | wx.EXPAND, 5)
        
        self.rounds_text = wx.StaticText(rounds_panel, -1, str(self.rounds_slider.GetValue()))
        rounds_sizer.Add(self.rounds_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        rounds_panel.SetSizer(rounds_sizer)
        settings_sizer.Add(rounds_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        main_vbox.Add(settings_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        main_panel.SetSizer(main_vbox)
        vbox.Add(main_panel, 1, wx.EXPAND)
        
        # Buttons panel at bottom
        button_panel = wx.Panel(self)
        button_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        ok_button = wx.Button(button_panel, wx.ID_OK, T("OK"))
        ok_button.SetBackgroundColour(wx.Colour(255, 255, 255))
        ok_button.SetMinSize((100, 30))
        cancel_button = wx.Button(button_panel, wx.ID_CANCEL, T('Cancel'))
        cancel_button.SetBackgroundColour(wx.Colour(255, 255, 255))
        cancel_button.SetMinSize((100, 30))
        
        button_sizer.Add(ok_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)
        
        button_panel.SetSizer(button_sizer)
        vbox.Add(button_panel, 0, wx.ALL | wx.ALIGN_CENTER | wx.BOTTOM, 20)
        
        # Bind events
        self.tokens_slider.Bind(wx.EVT_SLIDER, self.on_tokens_slider)
        self.timeout_slider.Bind(wx.EVT_SLIDER, self.on_timeout_slider)
        self.rounds_slider.Bind(wx.EVT_SLIDER, self.on_rounds_slider)
        
        self.SetSizer(vbox)
        self.Centre()
        
    def on_browse_work_dir(self, event):
        with DirDialog(self, T("Select work directory"), 
                      defaultPath=self.work_dir_text.GetValue(),
                      style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.work_dir_text.SetValue(dlg.GetPath())
    
    def on_tokens_slider(self, event):
        value = self.tokens_slider.GetValue()
        self.tokens_text.SetLabel(str(value))
    
    def on_timeout_slider(self, event):
        value = self.timeout_slider.GetValue()
        self.timeout_text.SetLabel(str(value))
    
    def on_rounds_slider(self, event):
        value = self.rounds_slider.GetValue()
        self.rounds_text.SetLabel(str(value))
    
    def get_values(self):
        return {
            'workdir': self.work_dir_text.GetValue(),
            'max_tokens': int(self.tokens_slider.GetValue()),
            'timeout': float(self.timeout_slider.GetValue()),
            'max_rounds': int(self.rounds_slider.GetValue())
        }

if __name__ == '__main__':
    class TestSettings:
        def __init__(self):
            self.workdir = os.getcwd()
            self._settings = {
                'max-tokens': 2000,
                'timeout': 30.0,
                'max-rounds': 10
            }
        
        def get(self, key, default=None):
            return self._settings.get(key, default)
        
        def __setitem__(self, key, value):
            self._settings[key] = value
        
        def save(self):
            print("Settings saved:", self._settings)
    
    app = wx.App(False)
    settings = TestSettings()
    dialog = ConfigDialog(None, settings)
    if dialog.ShowModal() == wx.ID_OK:
        values = dialog.get_values()
        print("New settings:", values)
    dialog.Destroy()
    app.MainLoop() 