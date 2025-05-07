#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import platform
from datetime import datetime
from importlib.resources import read_text

from loguru import logger
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.syntax import Syntax
from rich.console import Console
import requests

from ..exec import Runner
from .. import event_bus, Stoppable, T, __resources__
from .utils import get_safe_filename
from .blocks import CodeBlocks
from .runtime import Runtime
from .stream import StreamProcessor
from .config import get_region_api

CONSOLE_HTML_FORMAT = read_text(__resources__, "console_white.tpl")

class Task(Stoppable):
    MAX_ROUNDS = 16

    def __init__(self, tm, system_prompt, max_rounds=None):
        super().__init__()
        self.task_id = uuid.uuid4().hex
        self.log = logger.bind(src='task', id=self.task_id)

        console = Console(file=tm.console.file, record=True)
        console.gui = getattr(tm.console, 'gui', False)
        self.instruction = None
        self.console = console
        self.settings = tm.settings
        self.envs = tm.envs
        self.session = None
        self.diagnose = None
        self.max_rounds = max_rounds
        self.system_prompt = system_prompt
        self.start_time = None
        self.done_time = None
        self.code_blocks = CodeBlocks(console)
        self.stream_processor = StreamProcessor(console)
        self.runtime = Runtime(self)
        self.runner = Runner(self.runtime)

    def save(self, path):
       if self.console.record:
           self.console.save_html(path, clear=False, code_format=CONSOLE_HTML_FORMAT)

    def auto_save(self):
        instruction = self.instruction
        task = {'instruction': instruction}
        task['llm'] = self.session.history.json()
        task['envs'] = self.runtime.envs
        task['runner'] = self.runner.history

        filename = f"{self.task_id}.json"
        try:
            json.dump(task, open(filename, 'w'), ensure_ascii=False, indent=4)
        except Exception as e:
            self.log.exception('Error saving task')

        filename = f"{self.task_id}.html"
        self.save(filename)
        self.log.info('Task auto saved')
        
    def done(self):
        curname = f"{self.task_id}.json"
        jsonname = get_safe_filename(self.instruction, extension='.json')
        if jsonname and os.path.exists(curname):
            try:
                os.rename(curname, jsonname)
            except Exception as e:
                self.log.exception('Error renaming task json file')

        curname = f"{self.task_id}.html"
        htmlname = get_safe_filename(self.instruction, extension='.html')
        if htmlname and os.path.exists(curname):
            try:
                os.rename(curname, htmlname)
            except Exception as e:
                self.log.exception('Error renaming task html file')
        self.diagnose.report_code_error(self.runner.history)
        self.done_time = datetime.now()
        self.log.info('Task done', jsonname=jsonname, htmlname=htmlname)
        if self.settings.get('share_result'):
            self.sync_to_cloud()

    def process_code_reply(self, code_ids, llm=None):
        results = []
        for code_id in code_ids:
            block = self.code_blocks.get_block_by_id(code_id)
            event_bus('exec', block)
            code_block = block['content']
            self.box(f"⚡ {T("Start executing code block")}: {code_id}", code_block, lang='python', style="bold cyan", line_numbers=True)
            result = self.runner(code_block)
            result['id'] = code_id
            results.append(result)
            event_bus('result', result)

        if len(results) == 1:
            results = results[0]
        json_results = json.dumps(results, ensure_ascii=False, indent=4)
        self.box(f"✅ {T("Execution result")}", json_results, lang="json", style="bold cyan")
        self.console.rule(f"[dim white]{T("Start sending feedback")}", characters='.')
        feed_back = f"# 最初任务\n{self.instruction}\n\n# 代码执行结果反馈\n{json_results}"
        return self.chat(feed_back, name=llm)

    def print_blocks(self, blocks):
        table = Table(title=T("Code Blocks"), show_lines=True)
        table.add_column(T("ID"), justify="center", style="bold cyan", no_wrap=True)
        table.add_column(T("Language"), justify="center", style="green")
        table.add_column(T("Base ID"), style="white")
        table.add_column(T("Filename"), style="white")

        for bid, block in blocks.items():
            table.add_row(
                bid,
                block.get('language', ''),
                block.get('base_id', ''),
                block.get('filename', '')
            )
        self.console.print(table)

    def process_reply(self, content, llm=None):
        self.console.rule(f"[dim white]{T("Start parsing message")}", characters='.')
        ret = self.code_blocks.parse(content)
        errors = ret['errors']
        if errors:
            event_bus('result', errors)
            json_str = json.dumps(errors, ensure_ascii=False)
            self.box(f"✅ {T("Execution result")}", json_str, lang="json", style="bold cyan")
            self.console.rule(f"[dim white]{T("Start sending feedback")}", characters='.')
            feed_back = f"# 消息解析错误\n{json_str}"
            ret = self.chat(feed_back, name=llm)
        elif ret['exec_ids']:
            ret = self.process_code_reply(ret['exec_ids'], llm)
        else:
            ret = None
        return ret
                
    def box(self, title, content, align=None, lang=None, style=None, line_numbers=False):
        if lang:
            content = Syntax(content, lang, line_numbers=line_numbers, word_wrap=True)
        if align:
            content = Align(content, align=align)
        
        self.console.rule(Text(title, style=style), style=style)
        self.console.print(content)

    def print_summary(self, detail=False):
        history = self.session.history
        if detail:
            table = Table(title=T("Task Summary"), show_lines=True)

            table.add_column(T("Round"), justify="center", style="bold cyan", no_wrap=True)
            table.add_column(T("Time(s)"), justify="right")
            table.add_column(T("In Tokens"), justify="right")
            table.add_column(T("Out Tokens"), justify="right")
            table.add_column(T("Total Tokens"), justify="right", style="bold magenta")

            round = 1
            for row in history.get_usage():
                table.add_row(
                    str(round),
                    str(row["time"]),
                    str(row["input_tokens"]),
                    str(row["output_tokens"]),
                    str(row["total_tokens"]),
                )
                round += 1
            self._console.print("\n")
            self._console.print(table)
        summary = history.get_summary()
        if 'time' in summary:
            summarys = "| {rounds} | {time:.3f}s | Tokens: {input_tokens}/{output_tokens}/{total_tokens}".format(**summary)
        else:
            summarys = ''
        event_bus.broadcast('summary', summarys)
        self.console.print(f"\n⏹ [cyan]{T("End processing instruction")} {summarys}")

    def build_user_prompt(self, instruction):
        prompt = {'task': instruction}
        prompt['python_version'] = platform.python_version()
        prompt['platform'] = platform.platform()
        prompt['today'] = datetime.today().isoformat()
        prompt['work_dir'] = '工作目录为当前目录，默认在当前目录下创建文件'
        if getattr(self.console, 'gui', False):
            self.log.info('GUI mode')
            prompt['matplotlib'] = "我现在用的是 matplotlib 的 Agg 后端，请默认用 plt.savefig() 保存图片后用 runtime.display() 显示，禁止使用 plt.show()"
            prompt['wxPython'] = "你回复的Markdown 消息中，可以用 ![图片](图片路径) 的格式引用之前创建的图片，会显示在 wx.html2 的 WebView 中"
        else:
            prompt['TERM'] = os.environ.get('TERM')
            prompt['LC_TERMINAL'] = os.environ.get('LC_TERMINAL')
        return prompt

    def run(self, instruction, *, llm=None, max_rounds=None):
        """
        执行自动处理循环，直到 LLM 不再返回代码消息
        """
        self.log.info('Running task', instruction=instruction)
        self.box(T("Start processing instruction"), f'[red]{instruction}', style="bold green")
        if not self.start_time:
            self.start_time = datetime.now()
            self.instruction = instruction
            prompt = self.build_user_prompt(instruction)
            event_bus('task_start', prompt)
            instruction = json.dumps(prompt, ensure_ascii=False)
            system_prompt = self.system_prompt
            self.session.stream_processor = StreamProcessor(self.console)
        else:
            system_prompt = None
        rounds = 1
        max_rounds = max_rounds or self.max_rounds
        if not max_rounds or max_rounds < 1:
            max_rounds = self.MAX_ROUNDS
        response = self.chat(instruction, system_prompt=system_prompt, name=llm)
        while response and rounds <= max_rounds:
            response = self.process_reply(response.content)
            rounds += 1
            if self.is_stopped():
                self.log.info('Task stopped')
                break
        self.print_summary()
        self.auto_save()
        self.console.bell()
        self.log.info('Task done')
        
    def chat(self, prompt, system_prompt=None, name=None):
        self.console.rule(f"[dim white]{T('Sending msg to {}', self.session.name)}", characters='.')
        response = self.session.chat(prompt, system_prompt=system_prompt, name=name)
        return response

    def step(self):
        response = self.session.get_last_message()
        if not response:
            self.console.print(f"❌ {T("No context information found")}")
            return
        self.process_reply(response)

    def sync_to_cloud(self, verbose=True):
        """ Sync result
        """
        url = get_region_api('share_url', self.settings)
        
        trustoken_apikey = self.settings.get('llm', {}).get('trustoken', {}).get('api_key')
        if not trustoken_apikey:
            return False
        try:
            response = requests.post(url, json={
                'apikey': trustoken_apikey,
                'author': os.getlogin(),
                'instruction': self.instruction,
                'llm': self.session.history.json(),
                'runner': self.runner.history,
            }, verify=True, timeout=30)
        except Exception as e:
            self.log.exception('Error sync result')
            return False

        status_code = response.status_code
        if status_code in (200, 201):
            if verbose:
                self.console.print(f"[green]{T('upload success')}:", response.json())
            return response.json()

        if verbose:
            self.console.print(f"[red]{T('upload failed', status_code)}:", response.text)
        return False
