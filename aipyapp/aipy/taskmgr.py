#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path

from loguru import logger

from .i18n import T
from .task import Task
from .llm import LLM
from .config import CONFIG_DIR
from .runner import Runner
from .plugin import PluginManager
from .prompt import SYSTEM_PROMPT
from .diagnose import Diagnose

class TaskManager:
    def __init__(self, settings, console):
        self.settings = settings
        self.console = console
        self.task = None
        self.envs = {}
        self.log = logger.bind(src='taskmgr')
        
        self.config_files = settings._loaded_files
        self.system_prompt = f"{settings.system_prompt}\n{SYSTEM_PROMPT}"
        plugin_dir = CONFIG_DIR / 'plugins'
        self.plugin_manager = PluginManager(plugin_dir)
        self.plugin_manager.load_plugins()
        if settings.workdir:
            workdir = Path.cwd() / settings.workdir
            workdir.mkdir(parents=True, exist_ok=True)
            os.chdir(workdir)
            self._cwd = workdir
        else:
            self._cwd = Path.cwd()

        self._init_environ()
        self._init_api()
        self.diagnose = Diagnose.create(settings)
        self.runner = Runner(settings, console, envs=self.envs)
        self.llm = LLM(settings, console, system_prompt=self.system_prompt)
        
    @property
    def workdir(self):
        return str(self._cwd)

    def get_update(self, force=False):
        return self.diagnose.check_update(force)

    @property
    def busy(self):
        return self.task is not None

    def use(self, name):
        ret = self.llm.use(name)
        self.console.print('[green]Ok[/green]' if ret else '[red]Error[/red]')
        return ret

    def done(self):
        if not self.task:
            return
        self.log.info('Done task', task_id=self.task.task_id)   
        self.diagnose.report_code_error(self.runner.history)
        self.task.done()
        self.task = None

    def save(self, path):
        if self.task:  
            self.task.save(path)

    def _init_environ(self):
        envs = self.settings.get('environ', {})
        for name, value in envs.items():
            os.environ[name] = value

    def _init_api(self):
        api = self.settings.get('api')
        if not api:
            return
        lines = [self.system_prompt]
        for api_name, api_conf in api.items():
            lines.append(f"## {api_name} API")
            desc = api_conf.get('desc')
            if desc: 
                lines.append(f"### API {T('description')}\n{desc}")

            envs = api_conf.get('env')
            if not envs:
                continue

            lines.append(f"### {T('env_description')}")
            for name, (value, desc) in envs.items():
                value = value.strip()
                if not value:
                    continue
                lines.append(f"- {name}: {desc}")
                self.envs[name] = (value, desc)

        self.system_prompt = "\n".join(lines)

    def new_task(self, instruction, llm=None, max_rounds=None, system_prompt=None):
        if llm and not self.llm.use(llm):
            return None
        
        system_prompt = system_prompt or self.system_prompt
        max_rounds = max_rounds or self.settings.get('max_rounds')
        task = Task(instruction, system_prompt=system_prompt, max_rounds=max_rounds)
        task.console = self.console
        task.llm = self.llm
        task.runner = self.runner
        self.task = task
        self.log.info('New task created', task_id=task.task_id)
        return task
    
    def __call__(self, instruction, llm=None, max_rounds=None, system_prompt=None):
        if self.task:
            self.task.run(instruction=instruction, llm=llm, max_rounds=max_rounds)
        else:
            task = self.new_task(instruction, llm=llm, max_rounds=max_rounds, system_prompt=system_prompt)
            self.task = task
            task.run()
        
    def stop_task(self):
        if self.task:
            self.log.info('Stopping task')
            self.task.stop()
            self.llm.stop()
