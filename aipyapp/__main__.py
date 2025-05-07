#!/usr/bin/env python
# coding: utf-8

import os
import sys

if "pythonw" in sys.executable.lower():
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

from loguru import logger

from .aipy.config import CONFIG_DIR

logger.remove()
logger.add(CONFIG_DIR / "aipyapp.log", format="{time:HH:mm:ss} | {level} | {message} | {extra}", level='INFO')

def parse_args():
    import argparse
    
    config_help_message = (
        f"Specify the configuration directory.\nDefaults to {CONFIG_DIR} if not provided."
    )

    parser = argparse.ArgumentParser(description="Python use - AIPython", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c", '--config-dir', type=str, help=config_help_message)
    parser.add_argument('--level', type=str, default='INFO', help="Log level")
    parser.add_argument('-p', '--python', default=False, action='store_true', help="Python mode")
    parser.add_argument('-g', '--gui', default=False, action='store_true', help="GUI mode")
    parser.add_argument('--debug', default=False, action='store_true', help="Debug mode")
    parser.add_argument('-f', '--fetch-config', default=False, action='store_true', help="login to trustoken and fetch token config")
    parser.add_argument('cmd', nargs='?', default=None, help="Task to execute, e.g. 'Who are you?'")
    args = parser.parse_args()
    logger.level(args.level)
    return args

def ensure_wxpython():
    try:
        import wx
    except:
        import subprocess

        cp = subprocess.run([sys.executable, "-m", "pip", "install", 'wxpython'])
        assert cp.returncode == 0

def mainw():
    args = parse_args()
    ensure_wxpython()
    from .gui.main import main as aipy_main
    aipy_main(args)

def main():
    args = parse_args()
    if args.python:
        from .cli_python import main as aipy_main
    elif args.gui:
        ensure_wxpython()
        from .gui.main import main as aipy_main
    else:
        from .cli_task import main as aipy_main
    aipy_main(args)

if __name__ == '__main__':
    main()
