#!/usr/bin/env python
#coding: utf-8

import os
import wx
import json
import wx.lib.agw.hyperlink as hl
from wx.lib.scrolledpanel import ScrolledPanel
import tomllib
import tomli_w
import io
import copy
import traceback

from .. import T

class ApiItemPanel(wx.Panel):
    """单个API配置项面板"""
    def __init__(self, parent, api_name, api_config, on_edit=None, on_delete=None):
        super().__init__(parent, style=wx.BORDER_SIMPLE)
        self.api_name = api_name
        self.api_config = api_config
        self.on_edit = on_edit
        self.on_delete = on_delete

        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        
        # 创建布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # API名称
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(self, label=f"API名称: {api_name}")
        name_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        name_sizer.Add(name_label, 1, wx.EXPAND | wx.ALL, 5)
        
        # 添加按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        edit_button = wx.Button(self, label="编辑")
        edit_button.Bind(wx.EVT_BUTTON, self.on_edit_click)
        delete_button = wx.Button(self, label="删除")
        delete_button.Bind(wx.EVT_BUTTON, self.on_delete_click)
        
        button_sizer.Add(edit_button, 0, wx.ALL, 5)
        button_sizer.Add(delete_button, 0, wx.ALL, 5)
        name_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        main_sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # API详情
        details_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 显示API KEY(s)
        envs = api_config.get('env', {})
        for key_name in envs:
            key_value = envs[key_name]
            if isinstance(key_value, list) and len(key_value) > 0:
                masked_key = self.mask_api_key(key_value[0])
                display_key = key_name
                key_text = wx.StaticText(self, label=f"{display_key}: {masked_key}")
                details_sizer.Add(key_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # 显示描述
        if 'desc' in api_config:
            desc_text = wx.StaticText(self, label=f"描述: {api_config['desc']}")
            details_sizer.Add(desc_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        main_sizer.Add(details_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        self.Layout()
    
    def mask_api_key(self, key):
        """将API密钥进行掩码处理，只显示前3位和后3位"""
        if not key or len(key) < 8:
            return key
        return key[:3] + "..." + key[-3:]
    
    def on_edit_click(self, event):
        if self.on_edit:
            self.on_edit(self.api_name, self.api_config)
    
    def on_delete_click(self, event):
        if self.on_delete:
            dlg = wx.MessageDialog(
                self, 
                f"确定要删除API '{self.api_name}' 吗？",
                "确认删除",
                wx.YES_NO | wx.ICON_QUESTION
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            
            if result == wx.ID_YES and self.on_delete:
                self.on_delete(self.api_name)


class ApiEditDialog(wx.Dialog):
    """API编辑对话框"""
    def __init__(self, parent, api_name="", api_config=None, is_new=True):
        title = "新增API" if is_new else f"编辑API: {api_name}"
        super().__init__(parent, title=title, size=(600, 500))
        
        self.is_new = is_new
        self.api_name = api_name
        self.api_config = api_config or {"desc": ""}
        
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # API名称
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(self, label="API名称:")
        self.name_input = wx.TextCtrl(self)
        if not self.is_new:
            self.name_input.SetValue(self.api_name)
            self.name_input.Enable(False)  # 编辑模式下不允许更改名称
        
        name_sizer.Add(name_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        name_sizer.Add(self.name_input, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # API环境变量标题行
        env_header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        env_label = wx.StaticText(self, label="API密钥设置:")
        add_env_button = wx.Button(self, label="添加环境变量")
        add_env_button.Bind(wx.EVT_BUTTON, self.on_add_env)
        
        env_header_sizer.Add(env_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        env_header_sizer.Add(add_env_button, 0, wx.ALIGN_CENTER_VERTICAL)
        main_sizer.Add(env_header_sizer, 0, wx.ALL, 10)
        
         # 环境变量列表
        self.env_panel = wx.ScrolledWindow(self)
        self.env_panel.SetScrollRate(0, 20)
        self.env_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        self.env_sizer = wx.BoxSizer(wx.VERTICAL)
        self.env_panel.SetSizer(self.env_sizer)
        
        # 添加已有的环境变量
        self.env_controls = []
        
        # 查找环境变量键
        env_vars = {}
        if 'env' in self.api_config and isinstance(self.api_config['env'], dict):
            for key, value in self.api_config['env'].items():
                env_vars[key] = value
        
        # 添加找到的环境变量
        for var_name, value in env_vars.items():
            self.add_env_control(var_name, value)
            
        # 如果是新建API且没有环境变量，则默认添加一个空的环境变量控件
        if self.is_new and not env_vars:
            self.add_env_control("api_key", ["填写您的API密钥", "API密钥描述"])
        
        main_sizer.Add(self.env_panel, 2, wx.EXPAND | wx.ALL, 10)  # 增加比例权重到2
        
        # 描述
        desc_sizer = wx.BoxSizer(wx.VERTICAL)
        desc_label = wx.StaticText(self, label="API描述: (支持多行文本)")
        
        # 使用更大的多行文本框
        self.desc_input = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        # 设置更大的字体和最小高度
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.desc_input.SetFont(font)
        self.desc_input.SetMinSize((-1, 100))  # 设置最小高度
        
        if 'desc' in self.api_config:
            self.desc_input.SetValue(self.api_config['desc'])
            
        # 添加提示文本
        desc_hint = wx.StaticText(self, label="提示: 描述支持多行文本，将以\"\"\"...\"\"\"格式保存")
        desc_hint.SetForegroundColour(wx.Colour(100, 100, 100))
        desc_hint.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        desc_sizer.Add(desc_label, 0, wx.ALL, 5)
        desc_sizer.Add(self.desc_input, 1, wx.EXPAND | wx.ALL, 5)
        desc_sizer.Add(desc_hint, 0, wx.LEFT | wx.BOTTOM, 5)
        
        main_sizer.Add(desc_sizer, 1, wx.EXPAND | wx.ALL, 10)
        
        # 按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_button = wx.Button(self, wx.ID_OK, "保存")
        cancel_button = wx.Button(self, wx.ID_CANCEL, "取消")
        
        button_sizer.Add(save_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        self.Layout()
        
        # 设置最小窗口大小
        self.SetMinSize((600, 500)) 
    
    def add_env_control(self, key_name="", key_value=None):
        """添加一个环境变量控制项"""
        if len(self.env_controls) >= 2:
            return
            
        if key_value is None:
            key_value = ["", "描述"]
        
        env_item = wx.Panel(self.env_panel)
        env_item.SetBackgroundColour(wx.Colour(245, 245, 245))
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 变量名
        key_name_label = wx.StaticText(env_item, label="变量名:")
        key_name_input = wx.TextCtrl(env_item, size=(150, -1))
        key_name_input.SetValue(key_name)
        
        # 值
        key_value_label = wx.StaticText(env_item, label="值:")
        key_value_input = wx.TextCtrl(env_item, size=(150, -1))
        if isinstance(key_value, list) and len(key_value) > 0:
            key_value_input.SetValue(key_value[0])
        
        # 描述
        key_desc_label = wx.StaticText(env_item, label="描述:")
        key_desc_input = wx.TextCtrl(env_item, size=(150, -1))
        if isinstance(key_value, list) and len(key_value) > 1:
            key_desc_input.SetValue(key_value[1])
        
        # 删除按钮
        delete_button = wx.Button(env_item, label="移除")
        delete_button.Bind(wx.EVT_BUTTON, lambda evt, item=env_item: self.remove_env_item(item))
        
        # 添加到布局
        item_sizer.Add(key_name_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(key_name_input, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(key_value_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(key_value_input, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(key_desc_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(key_desc_input, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        item_sizer.Add(delete_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        env_item.SetSizer(item_sizer)
        self.env_sizer.Add(env_item, 0, wx.EXPAND | wx.ALL, 5)
        
        # 添加分隔线
        separator = wx.StaticLine(self.env_panel)
        self.env_sizer.Add(separator, 0, wx.EXPAND | wx.ALL, 5)
        
        self.env_controls.append({
            'panel': env_item,
            'name': key_name_input,
            'value': key_value_input,
            'desc': key_desc_input
        })
        
        self.env_panel.Layout()
        # 确保新添加的控件可见
        self.env_panel.Scroll(0, self.env_sizer.GetSize().GetHeight())
    
    def remove_env_item(self, item):
        """移除环境变量控制项"""
        for i, ctrl in enumerate(self.env_controls):
            if ctrl['panel'] == item:
                item.Destroy()
                self.env_controls.pop(i)
                break
        
        self.env_panel.Layout()
        self.env_panel.SetupScrolling()
    
    def on_add_env(self, event):
        """添加新的环境变量"""
        if len(self.env_controls) >= 2:
            wx.MessageBox("最多只能添加两个环境变量", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        self.add_env_control()
    
    def get_api_config(self):
        """获取编辑后的API配置"""
        name = self.name_input.GetValue().strip()
        
        config = {
            "desc": self.desc_input.GetValue()  # 保留原始格式，包括换行
        }
        
        env = {}
        for ctrl in self.env_controls:
            # 获取用户输入的键名
            key_name = ctrl['name'].GetValue().strip()
            
            # 如果键名为空，则跳过
            if not key_name:
                continue
                
            key_value = ctrl['value'].GetValue().strip()
            key_desc = ctrl['desc'].GetValue().strip()
            
            env[key_name] = [key_value, key_desc]

        if env: config['env'] = env        
        return name, config


class ApiDetailsDialog(wx.Dialog):
    """API详情对话框"""
    def __init__(self, parent, api_name, api_config):
        super().__init__(parent, title=f"API详情: {api_name}", size=(500, 400))
        
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        self.api_name = api_name
        self.api_config = api_config
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建滚动面板
        scroll_panel = ScrolledPanel(self)
        scroll_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 描述
        if 'desc' in self.api_config and self.api_config['desc']:
            desc_group = wx.StaticBox(scroll_panel, label="描述")
            desc_sizer = wx.StaticBoxSizer(desc_group, wx.VERTICAL)
            
            desc_text = wx.StaticText(scroll_panel, label=self.api_config['desc'])
            desc_text.Wrap(450)  # 设置自动换行宽度
            
            desc_sizer.Add(desc_text, 0, wx.ALL | wx.EXPAND, 10)
            scroll_sizer.Add(desc_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 查找环境变量键
        envs = self.api_config.get('env')
        if envs:
            env_group = wx.StaticBox(scroll_panel, label="环境变量")
            env_sizer = wx.StaticBoxSizer(env_group, wx.VERTICAL)
            
            for i, key_name in enumerate(envs.keys()):
                key_value = envs[key_name]
                display_key = key_name
                
                env_panel = wx.Panel(scroll_panel)
                env_panel.SetBackgroundColour(wx.Colour(245, 245, 245))
                
                env_box = wx.BoxSizer(wx.VERTICAL)
                
                name_text = wx.StaticText(env_panel, label=f"变量名: {display_key}")
                name_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                
                if isinstance(key_value, list):
                    if len(key_value) > 0:
                        # 使用掩码显示API密钥
                        masked_key = key_value[0]
                        if len(masked_key) > 8:
                            masked_key = masked_key[:3] + "..." + masked_key[-3:]
                        value_text = wx.StaticText(env_panel, label=f"值: {masked_key}")
                    
                    if len(key_value) > 1 and key_value[1]:
                        desc_text = wx.StaticText(env_panel, label=f"描述: {key_value[1]}")
                        desc_text.Wrap(400)
                
                env_box.Add(name_text, 0, wx.ALL, 5)
                env_box.Add(value_text, 0, wx.ALL, 5)
                if len(key_value) > 1 and key_value[1]:
                    env_box.Add(desc_text, 0, wx.ALL, 5)
                
                env_panel.SetSizer(env_box)
                env_sizer.Add(env_panel, 0, wx.ALL | wx.EXPAND, 5)
                
                # 添加分隔线，除了最后一个
                if i < len(envs) - 1:
                    env_sizer.Add(wx.StaticLine(scroll_panel), 0, wx.EXPAND | wx.ALL, 5)
            
            scroll_sizer.Add(env_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        scroll_panel.SetSizer(scroll_sizer)
        scroll_panel.SetupScrolling()
        
        main_sizer.Add(scroll_panel, 1, wx.EXPAND | wx.ALL, 10)
        
        # 关闭按钮
        close_button = wx.Button(self, wx.ID_OK, "关闭")
        main_sizer.Add(close_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        self.Layout()


class ApiMarketDialog(wx.Dialog):
    """API市场对话框 - 列表视图"""
    def __init__(self, parent, config_manager):
        super().__init__(parent, title="API市场", size=(800, 600))
        
        self.config_manager = config_manager
        # 确保获取最新配置
        self.config_manager.reload_config()
        self.settings = config_manager.get_config()
        
        # 复制API配置
        self.api_configs = self.settings.get('api', {})
        
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        
        # 创建界面
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title_text = wx.StaticText(self, label="API市场 - 管理您的API配置")
        title_text.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(title_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # 介绍说明
        desc_text = wx.StaticText(self, label="在此处管理您的API配置，包括添加新API、查看和编辑现有API。")
        main_sizer.Add(desc_text, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        # 工具栏
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        add_button = wx.Button(self, label="添加新API")
        add_button.Bind(wx.EVT_BUTTON, self.on_add_api)
        refresh_button = wx.Button(self, label="刷新列表")
        refresh_button.Bind(wx.EVT_BUTTON, self.on_refresh)
        
        toolbar_sizer.Add(add_button, 0, wx.ALL, 5)
        toolbar_sizer.Add(refresh_button, 0, wx.ALL, 5)
        
        main_sizer.Add(toolbar_sizer, 0, wx.LEFT, 10)
        
        # 创建列表控件
        self.api_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.api_list.InsertColumn(0, "API名称", width=200)
        self.api_list.InsertColumn(1, "密钥数量", width=100)
        self.api_list.InsertColumn(2, "描述", width=450)
        
        # 添加操作提示
        help_text = wx.StaticText(self, label="提示: 右键点击API项可进行查看、编辑和删除操作")
        help_text.SetForegroundColour(wx.Colour(100, 100, 100))
        help_text.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        
        # 加载API配置到列表
        self.load_api_configs()
        
        main_sizer.Add(self.api_list, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(help_text, 0, wx.LEFT | wx.BOTTOM, 15)
        
        # 右键菜单绑定
        self.api_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)
        
        # 双击查看详情
        self.api_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        
        # 底部按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_button = wx.Button(self, label="保存并应用")
        save_button.Bind(wx.EVT_BUTTON, self.on_save)
        cancel_button = wx.Button(self, wx.ID_CANCEL, "取消")
        
        button_sizer.Add(save_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        self.Layout()
    
    def load_api_configs(self):
        """加载API配置到列表"""
        self.api_list.DeleteAllItems()
        
        if not self.api_configs:
            no_api_item = self.api_list.InsertItem(0, "暂无API配置")
            self.api_list.SetItem(no_api_item, 2, "点击\"添加新API\"按钮添加API配置")
            return
        
        idx = 0
        for api_name, api_config in self.api_configs.items():
            item = self.api_list.InsertItem(idx, api_name)
            
            env_count = len(api_config.get('env', {}))
            self.api_list.SetItem(item, 1, str(env_count))
            
            # 添加描述
            desc = api_config.get('desc', '')
            if len(desc) > 60:
                desc = desc[:57] + "..."
            self.api_list.SetItem(item, 2, desc)
            
            idx += 1
    
    def on_item_activated(self, event):
        """双击列表项查看详情"""
        idx = event.GetIndex()
        api_name = self.api_list.GetItemText(idx)
        
        if api_name in self.api_configs:
            self.show_api_details(api_name)
    
    def show_api_details(self, api_name):
        """显示API详情"""
        api_config = self.api_configs.get(api_name)
        if api_config:
            dialog = ApiDetailsDialog(self, api_name, api_config)
            dialog.ShowModal()
            dialog.Destroy()
    
    def on_right_click(self, event):
        """右键菜单"""
        if not self.api_list.GetItemCount():
            return
            
        idx = event.GetIndex()
        if idx == -1:
            return
            
        api_name = self.api_list.GetItemText(idx)
        
        # 如果是"暂无API配置"提示项，不显示菜单
        if api_name == "暂无API配置":
            return
        
        menu = wx.Menu()
        
        view_item = menu.Append(wx.ID_VIEW_DETAILS, "查看详情")
        edit_item = menu.Append(wx.ID_EDIT, "编辑")
        delete_item = menu.Append(wx.ID_DELETE, "删除")
        
        self.Bind(wx.EVT_MENU, lambda evt, name=api_name: self.show_api_details(name), view_item)
        self.Bind(wx.EVT_MENU, lambda evt, name=api_name: self.on_edit_api(name), edit_item)
        self.Bind(wx.EVT_MENU, lambda evt, name=api_name: self.on_delete_api(name), delete_item)
        
        self.PopupMenu(menu)
        menu.Destroy()
    
    def on_add_api(self, event=None):
        """添加新API"""
        dialog = ApiEditDialog(self, is_new=True)
        result = dialog.ShowModal()
        
        if result == wx.ID_OK:
            api_name, api_config = dialog.get_api_config()
            
            if not api_name:
                wx.MessageBox("API名称不能为空", "错误", wx.OK | wx.ICON_ERROR)
                return
            
            if api_name in self.api_configs:
                wx.MessageBox(f"API名称 '{api_name}' 已存在", "错误", wx.OK | wx.ICON_ERROR)
                return
            
            self.api_configs[api_name] = api_config
            self.load_api_configs()
        
        dialog.Destroy()
    
    def on_edit_api(self, api_name):
        """编辑API配置"""
        if api_name not in self.api_configs:
            return
            
        api_config = self.api_configs[api_name]
        dialog = ApiEditDialog(self, api_name, api_config, is_new=False)
        result = dialog.ShowModal()
        
        if result == wx.ID_OK:
            _, updated_config = dialog.get_api_config()
            self.api_configs[api_name] = updated_config
            self.load_api_configs()
        
        dialog.Destroy()
    
    def on_delete_api(self, api_name):
        """删除API配置"""
        if api_name not in self.api_configs:
            return
            
        dlg = wx.MessageDialog(
            self, 
            f"确定要删除API '{api_name}' 吗？",
            "确认删除",
            wx.YES_NO | wx.ICON_QUESTION
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        
        if result == wx.ID_YES:
            del self.api_configs[api_name]
            self.load_api_configs()
    
    def on_refresh(self, event):
        """刷新API列表"""
        # 重新加载配置
        self.config_manager.reload_config()
        self.settings = self.config_manager.get_config()
        
        # 重新加载API配置
        self.api_configs = self.settings.get('api', {})

        # 更新列表
        self.load_api_configs()

    def on_save(self, event):
        """保存API配置"""
        try:
            self.config_manager.update_sys_config({'api': self.api_configs})
            self.settings = self.config_manager.reload_config()
            
            # 更新父窗口的配置
            if hasattr(self.Parent, 'tm'):
                self.Parent.tm.settings = self.config_manager.get_config()
                if hasattr(self.Parent.tm, 'config'):
                    self.Parent.tm.config = self.config_manager.get_config()
            
            # 显示保存成功的消息
            wx.MessageBox("API配置已保存并应用", "成功", wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)
        except Exception as e:
            traceback.print_exc()
            wx.MessageBox(f"保存配置失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            traceback.print_exc() 