#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import traceback
from io import StringIO

INIT_IMPORTS = """
import os
import re
import sys
import json
import time
import random
import traceback
"""

def is_json_serializable(obj):
    try:
        json.dumps(obj)  # 尝试序列化对象
        return True
    except (TypeError, OverflowError):
        return False

def diff_dicts(dict1, dict2):
    diff = {}
    for key, value in dict1.items():
        if key not in dict2 or dict2[key] != value:
            diff[key] = value
    return diff

class Runner():
    def __init__(self, runtime):
        self.runtime = runtime
        self.history = []
        self._globals = {'runtime': runtime, '__session__': {}, '__name__': '__main__', 'input': self.runtime.input}
        exec(INIT_IMPORTS, self._globals)

    def __repr__(self):
        return f"<Runner history={len(self.history)}, env={len(self.env)}>"
    
    @property
    def globals(self):
        return self._globals
    
    def __call__(self, code_str):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        sys.stdout, sys.stderr = captured_stdout, captured_stderr
        result = {}
        env = self.runtime.envs.copy()
        session = self._globals['__session__'].copy()
        gs = self._globals.copy()
        gs['__result__'] = {}
        try:
            exec(code_str, gs)
        except (SystemExit, Exception) as e:
            result['errstr'] = str(e)
            result['traceback'] = traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        s = captured_stdout.getvalue().strip()
        if s: result['stdout'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'
        s = captured_stderr.getvalue().strip()
        if s: result['stderr'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'        

        vars = gs.get('__result__')
        if vars:
            result['__result__'] = self.filter_result(vars)

        history = {'code': code_str, 'result': result}

        diff = diff_dicts(env, self.runtime.envs)
        if diff:
            history['env'] = diff
        diff = diff_dicts(gs['__session__'], session)
        if diff:
            history['session'] = diff

        self.history.append(history)
        return result

    def filter_result(self, vars):
        if isinstance(vars, dict):
            for key in vars.keys():
                if key in self.runtime.envs:
                    vars[key] = '<masked>'
                else:
                    vars[key] = self.filter_result(vars[key])
        elif isinstance(vars, list):
            vars = [self.filter_result(v) for v in vars]
        else:
            vars = vars if is_json_serializable(vars) else '<filtered>'
        return vars
    