#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from collections import deque

from loguru import logger

from .. import T
from .task import Task
from ..llm import ClientManager
from .config import CONFIG_DIR

from .plugin import PluginManager
from .prompt import SYSTEM_PROMPT
from .diagnose import Diagnose


class TaskManager:
    MAX_TASKS = 16

    def __init__(self, settings, console):
        self.settings = settings
        self.console = console
        self.tasks = deque(maxlen=self.MAX_TASKS)
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
        self.clients = ClientManager(settings)

    @property
    def workdir(self):
        return self._cwd

    def get_update(self, force=False):
        return self.diagnose.check_update(force)

    def use(self, name):
        self.clients.use(name)

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
                lines.append(f"### API {T("Description")}\n{desc}")

            envs = api_conf.get('env')
            if not envs:
                continue

            lines.append(f"### {T("Environment variable name and meaning")}")
            for name, (value, desc) in envs.items():
                value = value.strip()
                if not value:
                    continue
                lines.append(f"- {name}: {desc}")
                self.envs[name] = (value, desc)

        self.system_prompt = "\n".join(lines)

    def new_task(self, llm=None, max_rounds=None, system_prompt=None):
        session = self.clients.Session(name=llm)
        system_prompt = system_prompt or self.system_prompt
        max_rounds = max_rounds or self.settings.get('max_rounds')
        task = Task(self, system_prompt, max_rounds=max_rounds)
        task.session = session
        task.diagnose = self.diagnose
        self.tasks.append(task)
        self.log.info('New task created', task_id=task.task_id)
        return task
    