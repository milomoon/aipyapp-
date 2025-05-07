#!/usr/bin/env python
#coding: utf-8

import os
import sys
import time
import json
import queue
import base64
import mimetypes
import traceback
import threading
import importlib.resources as resources

import wx
import wx.html2
import matplotlib
from loguru import logger
import matplotlib.pyplot as plt
from rich.console import Console
from wx.lib.newevent import NewEvent
from wx import FileDialog, FD_SAVE, FD_OVERWRITE_PROMPT
from wx.lib.agw.hyperlink import HyperLinkCtrl

from .. import __version__, T, set_lang, event_bus
from ..aipy.config import ConfigManager
from ..aipy import TaskManager
from . import TrustTokenAuthDialog, ConfigDialog, AboutDialog, CStatusBar
from .apimarket import ApiMarketDialog

ChatEvent, EVT_CHAT = NewEvent()
AVATARS = {'我': '🧑', 'BB-8': '🤖', '图灵': '🧠', '爱派': '🐙'}
TITLE = "🐙爱派，您的干活牛🐂马🐎，啥都能干！"
RESOURCES = "aipyapp.res"

matplotlib.use('Agg')

def image_to_base64(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        return None

    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        return None

    data_url = f"data:{mime_type};base64,{encoded_string}"
    return data_url

class AIPython(threading.Thread):
    def __init__(self, gui):
        super().__init__(daemon=True)
        self.gui = gui
        self.tm = gui.tm
        self._task = None
        self._busy = threading.Event()
        plt.show = self.on_plt_show
        sys.modules["matplotlib.pyplot"] = plt
        self.log = logger.bind(src='aipython')

    def has_task(self):
        return self._task is not None

    def can_done(self):
        return not self._busy.is_set() and self.has_task()

    def on_plt_show(self, *args, **kwargs):
        filename = f'{time.strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename)
        user = 'BB-8'
        content = f'![{filename}]({filename})'
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def on_display(self, image):
        user = '图灵'
        if image['path']:
            base64_data = image_to_base64(image['path'])
            content = base64_data if base64_data else image['path']
        else:
            content = image['url']

        msg = f'![图片]({content})'
        evt = ChatEvent(user=user, msg=msg)
        wx.PostEvent(self.gui, evt)

    def on_response_complete(self, msg):
        user = '图灵' #msg['llm']
        #content = f"```markdown\n{msg['content']}\n```"
        evt = ChatEvent(user=user, msg=msg['content'])
        wx.PostEvent(self.gui, evt)

    def on_summary(self, summary):
        user = '爱派'
        evt = ChatEvent(user=user, msg=f'结束处理指令 {summary}')
        wx.PostEvent(self.gui, evt)

    def on_exec(self, block):
        user = 'BB-8'
        content = f"```python\n{block['content']}\n```"
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def on_result(self, result):
        user = 'BB-8'
        content = json.dumps(result, indent=4, ensure_ascii=False)
        content = f'运行结果如下\n```json\n{content}\n```'
        evt = ChatEvent(user=user, msg=content)
        wx.PostEvent(self.gui, evt)

    def run(self):
        event_bus.register("response_stream", self.on_response_complete)
        event_bus.register("exec", self.on_exec)
        event_bus.register("result", self.on_result)
        event_bus.register("summary", self.on_summary)
        event_bus.register("display", self.on_display)
        while True:
            instruction = self.gui.get_task()
            instruction = instruction.strip()
            if instruction in ('/done', 'done'):
                if self._task:
                    self._task.done()
                    self._task = None
                else:
                    self.log.warning("没有正在进行的任务")
                wx.CallAfter(self.gui.on_task_done)
            elif instruction in ('/exit', 'exit'):
                break
            else:
                self._busy.set()
                try:
                    if not self._task:
                        self._task = self.tm.new_task()
                    self._task.run(instruction)
                except Exception as e:
                    self.log.exception('Error running task')
                finally:
                    self._busy.clear()
                wx.CallAfter(self.gui.toggle_input)

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, text_ctrl):
        super().__init__()
        self.text_ctrl = text_ctrl

    def OnDropFiles(self, x, y, filenames):
        s = json.dumps(filenames, ensure_ascii=False)
        self.text_ctrl.AppendText(s)
        return True


class ChatFrame(wx.Frame):
    def __init__(self, tm):
        super().__init__(None, title=TITLE, size=(1024, 768))
        
        self.tm = tm
        self.task_queue = queue.Queue()
        self.aipython = AIPython(self)

        self.chat_html = resources.read_text(RESOURCES, "chatroom.html")
        self.base_url = f"file://{tm.workdir / 'index.html'}"

        with resources.path(RESOURCES, "aipy.ico") as icon_path:
            icon = wx.Icon(str(icon_path), wx.BITMAP_TYPE_ICO)
            self.SetIcon(icon)

        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        self.make_menu_bar()
        self.make_panel()
        self.statusbar = CStatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusText("按 Ctrl+Enter 发送消息", 0)

        self.Bind(EVT_CHAT, self.on_chat)
        self.aipython.start()
        self.Show()
        update = self.tm.get_update()
        if update and update.get('has_update'):
            wx.CallLater(1000, self.append_message, '爱派', f"\n🔔 **号外❗** {T("Update available")}: `v{update.get('latest_version')}`")

    def make_input_panel(self, panel):
        self.container = wx.Panel(panel)
 
        self.input = wx.TextCtrl(self.container, style=wx.TE_MULTILINE)
        self.input.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.input.SetForegroundColour(wx.Colour(33, 33, 33))
        self.input.SetMinSize((-1, 60))
        self.input.SetWindowStyleFlag(wx.BORDER_SIMPLE)
        self.input.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.done_button = wx.Button(self.container, label="结束", size=(50, -1))
        self.done_button.Hide()
        self.done_button.Bind(wx.EVT_BUTTON, self.on_done)
        self.done_button.SetBackgroundColour(wx.Colour(255, 230, 230)) 
        self.send_button = wx.Button(self.container, label="发送", size=(50, -1))
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)
        self.container.Bind(wx.EVT_SIZE, self.on_container_resize)
        return self.container

    def make_input_panel2(self, panel):
        container = wx.Panel(panel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.input = wx.TextCtrl(container, style=wx.TE_MULTILINE)
        self.input.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.input.SetForegroundColour(wx.Colour(33, 33, 33))
        self.input.SetMinSize((-1, 80))
        self.input.SetWindowStyleFlag(wx.BORDER_SIMPLE)
        self.input.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        hbox.Add(self.input, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.done_button = wx.Button(container, label="结束")
        self.done_button.Hide()
        self.done_button.Bind(wx.EVT_BUTTON, self.on_done)
        self.done_button.SetBackgroundColour(wx.Colour(255, 230, 230)) 
        self.send_button = wx.Button(container, label="发送")
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)
        vbox.Add(self.done_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vbox.AddSpacer(10)
        vbox.Add(self.send_button, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        hbox.Add(vbox, 0, wx.ALIGN_CENTER)
        container.SetSizer(hbox)    
        self.container = container
        return container
    
    def make_panel(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.webview = wx.html2.WebView.New(panel)
        self.webview.SetPage(self.chat_html, self.base_url)
        self.webview.SetWindowStyleFlag(wx.BORDER_NONE)
        vbox.Add(self.webview, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        if sys.platform == 'darwin':
            input_panel = self.make_input_panel(panel)
        else:
            input_panel = self.make_input_panel2(panel)
        drop_target = FileDropTarget(self.input)
        self.input.SetDropTarget(drop_target)
        font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.input.SetFont(font)
    
        vbox.Add(input_panel, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        panel.SetSizer(vbox)
        self.panel = panel

    def make_menu_bar(self):
        menu_bar = wx.MenuBar()
        menu_bar.SetBackgroundColour(wx.Colour(240, 240, 240))
        
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_SAVE, "保存聊天记录为 HTML(&S)\tCtrl+S", "保存当前聊天记录为 HTML 文件")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "退出(&Q)\tCtrl+Q", "退出程序")
        self.Bind(wx.EVT_MENU, self.on_save_html, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)

        edit_menu = wx.Menu()
        edit_menu.Append(wx.ID_CLEAR, T("Clear chat") + "(&C)", T("Clear all messages"))
        edit_menu.AppendSeparator()
        self.ID_CONFIG = wx.NewIdRef()
        menu_item = wx.MenuItem(edit_menu, self.ID_CONFIG, T("Configuration") + "(&O)\tCtrl+O", T("Configure program parameters"))
        edit_menu.Append(menu_item)
        self.Bind(wx.EVT_MENU, self.on_config, id=self.ID_CONFIG)
        self.Bind(wx.EVT_MENU, self.on_clear_chat, id=wx.ID_CLEAR)

        # Add API配置 menu item
        self.ID_API_CONFIG = wx.NewIdRef()
        menu_item = wx.MenuItem(edit_menu, self.ID_API_CONFIG, "API配置(&A)\tCtrl+A", "配置API市场")
        edit_menu.Append(menu_item)
        self.Bind(wx.EVT_MENU, self.on_api_config, id=self.ID_API_CONFIG)

        # Add API配置 menu item
        self.ID_API_CONFIG = wx.NewIdRef()
        menu_item = wx.MenuItem(edit_menu, self.ID_API_CONFIG, "API配置(&A)\tCtrl+A", "配置API市场")
        edit_menu.Append(menu_item)
        self.Bind(wx.EVT_MENU, self.on_api_config, id=self.ID_API_CONFIG)

        task_menu = wx.Menu()
        self.task_done_menu = task_menu.Append(wx.ID_STOP, "开始新任务(&B)", "开始一个新任务")
        self.task_done_menu.Enable(False)
        self.Bind(wx.EVT_MENU, self.on_done, id=wx.ID_STOP)
        
        self.ID_STOP_TASK = wx.NewIdRef()
        self.stop_task_menu_item = task_menu.Append(self.ID_STOP_TASK, "停止任务(&S)", "停止当前任务")
        self.stop_task_menu_item.Enable(False)
        self.Bind(wx.EVT_MENU, self.on_stop_task, id=self.ID_STOP_TASK)
        
        self.ID_SHARE_TASK = wx.NewIdRef()
        self.share_task_menu_item = task_menu.Append(self.ID_SHARE_TASK, "分享任务记录(&R)", "分享当前任务记录")
        self.share_task_menu_item.Enable(False)
        self.Bind(wx.EVT_MENU, self.on_share_task, id=self.ID_SHARE_TASK)
        
        menu_bar.Append(file_menu, "文件(&F)")
        menu_bar.Append(edit_menu, "编辑(&E)")
        menu_bar.Append(task_menu, "任务(&T)")

        help_menu = wx.Menu()
        self.ID_WEBSITE = wx.NewIdRef()
        menu_item = wx.MenuItem(help_menu, self.ID_WEBSITE, "官网(&W)\tCtrl+W", "官方网站")
        help_menu.Append(menu_item)
        self.ID_FORUM = wx.NewIdRef()
        menu_item = wx.MenuItem(help_menu, self.ID_FORUM, "论坛(&W)\tCtrl+F", "官方论坛")
        help_menu.Append(menu_item)
        self.ID_GROUP = wx.NewIdRef()
        menu_item = wx.MenuItem(help_menu, self.ID_GROUP, "微信群(&G)\tCtrl+G", "官方微信群")
        help_menu.Append(menu_item)
        help_menu.AppendSeparator()
        self.ID_ABOUT = wx.NewIdRef()
        menu_item = wx.MenuItem(help_menu, self.ID_ABOUT, "关于(&A)", "关于爱派")
        help_menu.Append(menu_item)
        self.Bind(wx.EVT_MENU, self.on_open_website, id=self.ID_WEBSITE)
        self.Bind(wx.EVT_MENU, self.on_open_website, id=self.ID_FORUM)
        self.Bind(wx.EVT_MENU, self.on_open_website, id=self.ID_GROUP)
        self.Bind(wx.EVT_MENU, self.on_about, id=self.ID_ABOUT)
        menu_bar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menu_bar)

    def on_exit(self, event):
        self.task_queue.put('exit')
        self.aipython.join()
        self.Close()

    def on_done(self, event):
        self.task_queue.put('/done')

    def on_task_done(self):
        self.done_button.Hide()
        self.SetStatusText("当前任务已结束", 0)
        self.task_done_menu.Enable(False)
        self.SetTitle(TITLE)

    def on_container_resize(self, event):
        container_size = event.GetSize()
        self.input.SetSize(container_size)

        overlap = -20
        send_button_size = self.send_button.GetSize()
        button_pos_x = container_size.width - send_button_size.width + overlap
        button_pos_y = container_size.height - send_button_size.height - 10
        self.send_button.SetPosition((button_pos_x, button_pos_y))

        if self.aipython.can_done():
            done_button_size = self.done_button.GetSize()
            button_pos_x = container_size.width - done_button_size.width + overlap
            button_pos_y = 10
            self.done_button.SetPosition((button_pos_x, button_pos_y))
            self.done_button.Show()

        event.Skip()

    def on_clear_chat(self, event):
        self.webview.LoadURL(self.chat_html)

    def on_open_website(self, event):
        if event.GetId() == self.ID_WEBSITE:
            url = "https://aipy.app"
        elif event.GetId() == self.ID_FORUM:
            url = "https://d.aipy.app"
        elif event.GetId() == self.ID_GROUP:
            url = "https://d.aipy.app/d/13"
        wx.LaunchDefaultBrowser(url)

    def on_about(self, event):
        about_dialog = AboutDialog(self)
        about_dialog.ShowModal()
        about_dialog.Destroy()

    def on_save_html(self, event):
        try:
            html_content = self.webview.GetPageSource()
            self.save_html_content(html_content)
        except Exception as e:
            wx.MessageBox(f"save html error: {e}", "Error")

    def save_html_content(self, html_content):
        with FileDialog(self, "保存聊天记录为 HTML 文件", wildcard="HTML 文件 (*.html)|*.html",
                        style=FD_SAVE | FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return

            path = dialog.GetPath()
            try:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(html_content)
            except IOError:
                wx.LogError(f"无法保存文件：{path}")

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        send_shortcut = (event.ControlDown() or event.CmdDown()) and keycode == wx.WXK_RETURN

        if send_shortcut:
            self.send_message()
        else:
            event.Skip()

    def on_send(self, event):
        self.send_message()

    def get_task(self):
        return self.task_queue.get()

    def toggle_input(self):
        if self.container.IsShown():
            self.container.Hide()
            self.done_button.Hide()
            wx.BeginBusyCursor()
            self.SetStatusText("操作进行中，请稍候...", 0)
            self.task_done_menu.Enable(False)
            self.stop_task_menu_item.Enable(True)
            self.share_task_menu_item.Enable(False)
        else:
            self.container.Show()
            self.done_button.Show()
            wx.EndBusyCursor()
            self.SetStatusText("操作完成。如果开始下一个任务，请点击'结束'按钮", 0)
            self.task_done_menu.Enable(self.aipython.can_done())
            self.stop_task_menu_item.Enable(False)
            self.share_task_menu_item.Enable(True)
        self.panel.Layout()
        self.panel.Refresh()

    def send_message(self):
        text = self.input.GetValue().strip()
        if not text:
            return
        
        if not self.aipython.has_task():
            self.SetTitle(f"[当前任务] {text}")

        self.append_message('我', text)
        self.input.Clear()
        self.toggle_input()
        self.task_queue.put(text)

    def on_chat(self, event):
        user = event.user
        text = event.msg
        self.append_message(user, text)

    def append_message(self, user, text):
        avatar = AVATARS[user]
        js_code = f'appendMessage("{avatar}", "{user}", {repr(text)});'
        self.webview.RunScript(js_code)

    def on_config(self, event):
        dialog = ConfigDialog(self, self.tm.settings)
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.get_values()
            if values['timeout'] == 0:
                del values['timeout']
            self.tm.config_manager.update_sys_config(values)
        dialog.Destroy()

    def on_stop_task(self, event):
        """停止当前任务"""
        self.tm.stop_task()

    def on_share_task(self, event):
        """分享当前任务记录"""
        try:
            html_content = self.webview.GetPageSource()
            result = self.tm.diagnose.report_data(html_content, 'task_record.html')
            if result.get('success'):
                dialog = ShareResultDialog(self, result['url'])
                dialog.ShowModal()
                dialog.Destroy()
            else:
                dialog = ShareResultDialog(self, None, result.get('error'))
                dialog.ShowModal()
                dialog.Destroy()
        except Exception as e:
            dialog = ShareResultDialog(self, None, str(e))
            dialog.ShowModal()
            dialog.Destroy()

    def on_api_config(self, event):
        """打开API配置对话框"""
        dialog = ApiMarketDialog(self, self.tm.config_manager)
        dialog.ShowModal()
        dialog.Destroy()

class ShareResultDialog(wx.Dialog):
    def __init__(self, parent, url, error=None):
        super().__init__(parent, title="分享结果", size=(400, 200))
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        if error:
            # 显示错误信息
            error_text = wx.StaticText(self, label="分享失败")
            error_text.SetForegroundColour(wx.Colour(255, 0, 0))
            error_text.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            vbox.Add(error_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            
            error_msg = wx.StaticText(self, label=error)
            error_msg.Wrap(350)
            vbox.Add(error_msg, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        else:
            # 显示成功信息
            success_text = wx.StaticText(self, label="分享成功")
            success_text.SetForegroundColour(wx.Colour(0, 128, 0))
            success_text.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            vbox.Add(success_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            
            # 添加提示文本
            hint_text = wx.StaticText(self, label="点击下方链接查看任务记录：")
            vbox.Add(hint_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            
            # 添加可点击的链接
            link = HyperLinkCtrl(self, -1, "查看任务记录", URL=url)
            link.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            link.SetColours("BLUE", "BLUE", "BLUE")
            link.EnableRollover(True)
            link.SetUnderlines(False, False, True)
            vbox.Add(link, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # 添加确定按钮
        ok_button = wx.Button(self, wx.ID_OK, "确定")
        ok_button.SetBackgroundColour(wx.Colour(255, 255, 255))
        vbox.Add(ok_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        self.SetSizer(vbox)
        self.Centre()

def main(args):
    app = wx.App(False)
    conf = ConfigManager(args.config_dir)
    if conf.check_config(gui=True) == 'TrustToken':
        url = conf.get_region_api('coordinator_url')
        dialog = TrustTokenAuthDialog(coordinator_url=url)
        if dialog.fetch_token(conf.save_tt_config):
            conf.reload_config()
        else:
            return
    
    settings = conf.get_config()
    settings.gui = True
    settings.auto_install = True
    settings.auto_getenv = True
    settings.debug = args.debug

    lang = settings.get('lang')
    if lang: set_lang(lang)

    file = None if args.debug else open(os.devnull, 'w')
    console = Console(file=file, record=True)
    console.gui = True
    try:
        tm = TaskManager(settings, console=console)
    except Exception as e:
        traceback.print_exc()
        return

    tm.config_manager = conf
    ChatFrame(tm)
    app.MainLoop()
