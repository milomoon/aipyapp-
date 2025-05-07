#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from enum import Enum, auto
from pathlib import Path
import importlib.resources as resources
from collections import OrderedDict

from loguru import logger
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter

from . import __version__, T, set_lang
from .aipy import TaskManager
from .aipy.config import ConfigManager, CONFIG_DIR

class CommandType(Enum):
    CMD_DONE = auto()
    CMD_USE = auto()
    CMD_EXIT = auto()
    CMD_INVALID = auto()
    CMD_TEXT = auto()
    CMD_INFO = auto()

def parse_command(input_str, llms=set()):
    lower = input_str.lower()

    if lower in ("/done", "done"):
        return CommandType.CMD_DONE, None
    if lower in ("/info", "info"):
        return CommandType.CMD_INFO, None
    if lower in ("/exit", "exit"):
        return CommandType.CMD_EXIT, None
    if lower in llms:
        return CommandType.CMD_USE, input_str
    
    if lower.startswith("/use "):
        arg = input_str[5:].strip()
        if arg in llms:
            return CommandType.CMD_USE, arg
        else:
            return CommandType.CMD_INVALID, arg

    if lower.startswith("use "):
        arg = input_str[4:].strip()
        if arg in llms:
            return CommandType.CMD_USE, arg
               
    return CommandType.CMD_TEXT, input_str

def show_info(console, info):
    info['Python'] = sys.executable
    info['Python version'] = sys.version
    info['Base Prefix'] = sys.base_prefix
    table = Table(title=T("System information"), show_lines=True)

    table.add_column("参数", justify="center", style="bold cyan", no_wrap=True)
    table.add_column("值", justify="right", style="bold magenta")

    for key, value in info.items():
        table.add_row(
            key,
            value,
        )

    console.print(table)

class InteractiveConsole():
    def __init__(self, tm, console, settings):
        self.tm = tm
        self.names = tm.clients.names
        self.log = logger.bind(src='console')
        completer = WordCompleter(['/use', 'use', '/done','done', '/info', 'info'] + list(self.names['enabled']), ignore_case=True)
        self.history = FileHistory(str(Path.cwd() / settings.history))
        self.session = PromptSession(history=self.history, completer=completer)
        self.console = console
        self.style_main = Style.from_dict({"prompt": "green"})
        self.style_ai = Style.from_dict({"prompt": "cyan"})
        
    def input_with_possible_multiline(self, prompt_text, is_ai=False):
        prompt_style = self.style_ai if is_ai else self.style_main

        first_line = self.session.prompt([("class:prompt", prompt_text)], style=prompt_style)
        if not first_line.endswith("\\"):
            return first_line
        # Multi-line input
        lines = [first_line.rstrip("\\")]
        while True:
            next_line = self.session.prompt([("class:prompt", "... ")], style=prompt_style)
            if next_line.endswith("\\"):
                lines.append(next_line.rstrip("\\"))
            else:
                lines.append(next_line)
                break
        return "\n".join(lines)

    def run_task(self, task, instruction):
        try:
            task.run(instruction)
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            self.console.print_exception()

    def start_task_mode(self, task, instruction):
        self.console.print(f"{T("Enter AI mode, start processing tasks, enter Ctrl+d or /done to end the task")}", style="cyan")
        self.run_task(task, instruction)
        while True:
            try:
                user_input = self.input_with_possible_multiline(">>> ", is_ai=True).strip()
                if len(user_input) < 2: continue
            except (EOFError, KeyboardInterrupt):
                break

            cmd, arg = parse_command(user_input, self.names['enabled'])
            if cmd == CommandType.CMD_TEXT:
                self.run_task(task, arg)
            elif cmd == CommandType.CMD_DONE:
                break
            elif cmd == CommandType.CMD_USE:
                try:
                    task.session.use(arg)
                    self.console.print('[green]Ok[/green]')
                except Exception as e:
                    self.console.print(f'[red]Error: {e}[/red]')
            elif cmd == CommandType.CMD_INVALID:
                self.console.print(f'[red]Error: {arg}[/red]')

        try:
            task.done()
        except Exception as e:
            self.console.print_exception()
        self.console.print(f"{T("[Exit AI mode]")}", style="cyan")

    def run(self):
        self.console.print(f"{T("Please enter the task to be processed by AI (enter /use <following LLM> to switch, enter /info to view system information)")}", style="green")
        self.console.print(f"[cyan]{T("Default")}: [green]{self.names['default']}，[cyan]{T("Enabled")}: [yellow]{' '.join(self.names['enabled'])}")
        while True:
            try:
                user_input = self.input_with_possible_multiline(">> ").strip()
                if len(user_input) < 2:
                    continue

                cmd, arg = parse_command(user_input, self.names['enabled'])
                if cmd == CommandType.CMD_TEXT:
                    task = self.tm.new_task()
                    self.start_task_mode(task, arg)
                elif cmd == CommandType.CMD_USE:
                    try:
                        self.tm.clients.use(arg)
                        self.console.print('[green]Ok[/green]')
                    except Exception as e:
                        self.console.print(f'[red]Error: {e}[/red]')
                elif cmd == CommandType.CMD_INFO:
                    info = OrderedDict()
                    info['Config dir'] = str(CONFIG_DIR)
                    info['Work dir'] = str(self.tm.workdir)
                    info['Current LLM'] = repr(self.tm.clients.current)
                    show_info(self.console, info)
                elif cmd == CommandType.CMD_EXIT:
                    break                    
                elif cmd == CommandType.CMD_INVALID:
                    self.console.print('[red]Error[/red]')
            except (EOFError, KeyboardInterrupt):
                break

def main(args):
    console = Console(record=True)
    console.print(f"[bold cyan]🚀 Python use - AIPython ({__version__}) [[green]https://aipy.app[/green]]")
    conf = ConfigManager(args.config_dir)
    conf.check_config()
    settings = conf.get_config()

    lang = settings.get('lang')
    if lang: set_lang(lang)

    if args.fetch_config:
        conf.fetch_config()
        return

    try:
        tm = TaskManager(settings, console=console)
    except Exception as e:
        console.print_exception()
        return

    update = tm.get_update()
    if update and update.get('has_update'):
        console.print(f"[bold red]🔔 号外❗ {T("Update available")}: {update.get('latest_version')}")

    if not tm.clients:
        console.print(f"[bold red]{T("No available LLM, please check the configuration file")}")
        return
    
    if args.cmd:
        tm.new_task(args.cmd).run()
        return
    InteractiveConsole(tm, console, settings).run()
