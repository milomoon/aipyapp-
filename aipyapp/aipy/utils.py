#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

from importlib.resources import read_text

from rich.panel import Panel

from .. import T, __resources__

DISCLAIMER_TEXT = read_text(__resources__, "DISCLAIMER.md")

def confirm(console, prompt, default="n", auto=None):
    if auto in (True, False):
        console.print(f"✅ {T("Auto confirm")}")
        return auto
    while True:
        response = console.input(prompt).strip().lower()
        if not response:
            response = default
        if response in ["y", "n"]:
            break
    return response == "y"

def confirm_disclaimer(console):
    console.print()
    panel = Panel.fit(DISCLAIMER_TEXT, title="[red]免责声明", border_style="red", padding=(1, 2))
    console.print(panel)

    while True:
        console.print("\n[red]是否确认已阅读并接受以上免责声明？[/red](yes/no):", end=" ")
        response = input().strip().lower()
        if response in ("yes", "y"):
            console.print("[green]感谢确认，程序继续运行。[/green]")
            return True
        elif response in ("no", "n"):
            console.print("[red]您未接受免责声明，程序将退出。[/red]")
            return False
        else:
            console.print("[yellow]请输入 yes 或 no。[/yellow]")

def get_safe_filename(input_str, extension=".html", max_length=16):
    input_str = input_str.strip()
    safe_str = re.sub(r'[\\/:*?"<>|]', '', input_str).strip()
    if not safe_str:
        return None

    name = safe_str[:max_length]
    base_name = name
    filename = f"{base_name}{extension}"
    counter = 1

    while os.path.exists(filename):
        filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return filename
