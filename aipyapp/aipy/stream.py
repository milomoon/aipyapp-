#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from loguru import logger
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.console import Console
from rich.markdown import Markdown

from .. import event_bus, T

class LineReceiver(list):
    def __init__(self):
        super().__init__()
        self.buffer = ""

    @property
    def content(self):
        return '\n'.join(self)
    
    def feeds(self, data: str):
        self.buffer += data
        new_lines = []

        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.append(line)
            new_lines.append(line)

        return new_lines
    
    def feed(self, data: str):
        line = None
        self.buffer += data
        if '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.append(line)
        return line

class LiveManager:
    def __init__(self, console, name):
        self.live = None
        self.name = name
        self.console = console
        self.lr = None
        self.title = None
        self.response_panel = None
        self.full_response = None

    def __enter__(self):
        self.lr = LineReceiver()
        self.title = f"{self.name} {T("reply")}"
        self.live = Live(auto_refresh=False, vertical_overflow='visible', transient=True)
        self.live.__enter__()
        status = self.console.status(f"[dim white]{self.name} {T("is thinking hard, please wait 6-60 seconds")}...", spinner='runner')
        response_panel = Panel(status, title=self.title, border_style="blue")
        self.live.update(response_panel, refresh=True)
        return self

    def feed(self, content):
        if not content: return
        lines = self.lr.feeds(content)
        if not lines: return
        
        content = '\n'.join(lines)
        event_bus.broadcast('response_stream', {'llm': self.name, 'content': content})

        full_response = self.lr.content
        try:
            md = Markdown(full_response)
            response_panel = Panel(md, title=self.title, border_style="green")
        except Exception:
            text = Text(full_response)
            response_panel = Panel(text, title=self.title, border_style="yellow")
        self.live.update(response_panel, refresh=True)
        self.response_panel = response_panel
        self.full_response = full_response
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lr.buffer:
            self.feed('\n')
        #if self.response_panel: self.console.print(self.response_panel)
        self.live.__exit__(exc_type, exc_val, exc_tb)

class LiveBlock:
    def __init__(self, console, language=None, delay=0.05):
        self.language = language
        self.delay = delay
        self.live = None
        self.lines = []
        self.console = console
        self.content = None
        self.log = logger.bind(src='live')
        self.log.info("LiveBlock initialized", language=self.language, delay=self.delay)

    def start(self):
        if not self.live:
            if getattr(self.console, 'gui', False):
                console = Console(quiet=True)
            else:
                console = None
            self.live = Live(auto_refresh=False, vertical_overflow="crop", console=console)
            self.live.__enter__()

    def stop(self):
        if self.live:
            self.live.__exit__(None, None, None)
            self.live = None
            if self.content:
                segments = self.console.render(self.content)
                self.console._record_buffer.extend(segments)

    def reset(self, language=None):
        self.language = language
        self.lines = []
        self.stop()
        self.start()

    def update(self, line):
        if not self.live:
            self.start()
        self.lines.append(line)
        content = '\n'.join(self.lines)
        if self.language:
            syntax = Syntax(content, self.language, theme="monokai", line_numbers=False, word_wrap=True)
        else:
            syntax = Markdown(content)
        self.live.update(syntax, refresh=True)
        time.sleep(self.delay)
        self.content = syntax

class BlockManager:
    def __init__(self, console, name):
        self.name = name
        self.console = console
        self.log = logger.bind(src='block')
        self.live = None

    def is_aipy_tag(self, line):
        return line.startswith("<!-- Block-") or line.startswith("<!-- Code-")

    def process(self, tokens):
        live = LiveBlock(self.console)
        lr = LineReceiver()
        for token in tokens:
            line = lr.feed(token)
            if not line or self.is_aipy_tag(line):
                continue

            event_bus.broadcast('response_stream', {'llm': self.name, 'content': line})

            if line.startswith('````python'):
                live.reset(language="python")
            elif line.startswith('````'):
                live.reset()
            else:
                live.update(line)

        if lr.buffer and not self.is_aipy_tag(lr.buffer):
            self.log.info("Updating live block", buffer=lr.buffer)
            live.update(lr.buffer)
            event_bus.broadcast('response_stream', {'llm': self.name, 'content': lr.buffer})
        live.stop()

class StreamProcessor:
    def __init__(self, console):
        self.console = console

    def get_processor(self, name):
        return BlockManager(self.console, name)

    def __call__(self, name, tokens):
        self.console.rule(f"[bold yellow]{name} {T('reply')}", style="bold yellow")
        self.get_processor(name).process(tokens)
        