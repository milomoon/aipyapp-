#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
from abc import ABC, abstractmethod

from loguru import logger

class BaseRuntime(ABC):
    def __init__(self, envs=None):
        self.envs = envs or {}
        self.packages = set()
        self.log = logger.bind(src='runtime')

    def set_env(self, name, value, desc):
        self.envs[name] = (value, desc)

    def ensure_packages(self, *packages, upgrade=False, quiet=True):
        if not packages:
            return True

        packages = list(set(packages) - self.packages)
        if not packages:
            return True
        
        cmd = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        if quiet:
            cmd.append("-q")
        cmd.extend(packages)

        try:
            subprocess.check_call(cmd)
            self.packages.update(packages)
            return True
        except subprocess.CalledProcessError:
            self.log.error("依赖安装失败: {}", " ".join(packages))
        
        return False

    def ensure_requirements(self, path="requirements.txt", **kwargs):
        with open(path) as f:
            reqs = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return self.ensure_packages(*reqs, **kwargs)
    
    @abstractmethod
    def install_packages(self, packages):
        pass

    @abstractmethod
    def get_env(self, name, default=None, *, desc=None):
        pass
    
    @abstractmethod
    def display(self, path=None, url=None):
        pass

    @abstractmethod
    def input(self, prompt=''):
        pass