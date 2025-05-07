#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from pathlib import Path
from collections import OrderedDict

from loguru import logger
import diff_match_patch as dmp_module

class CodeBlocks:
    def __init__(self, console):
        self.console = console
        self.blocks = OrderedDict()
        self.code_pattern = re.compile(
            r'<!--\s*Block-Start:\s*(\{.*?\})\s*-->\s*```(\w+)?\s*\n(.*?)\n```[\r\n]*<!--\s*Block-End:\s*(\{.*?\})\s*-->',
            re.DOTALL
        )
        self.line_pattern = re.compile(
            r'<!--\s*Code-(\w+):\s*(\{.*?\})\s*-->'
        )
        self.log = logger.bind(src='code_blocks')
        self.dmp = dmp_module.diff_match_patch()

    def save_block(self, block):
        if block and block.get('filename'):
            path = Path(block['filename'])
            try:
                #TODO: path check
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(block['content'])
            except Exception as e:
                self.log.error("Failed to save file", filename=block['filename'], reason=e)
                self.console.print("❌ Failed to save file", filename=block['filename'], reason=e)

    def apply_patch(self, patch_meta):
        code_id = patch_meta.get("id")
        patch_id = patch_meta.get("patch_id")
        filename = patch_meta.get("filename")

        if patch_id not in self.blocks:
            self.log.error("Patch id not found", patch_id=patch_id)
            return {'Patch id not found': {'patch_id': patch_id}}

        patch_block = self.blocks[patch_id]
        if patch_block.get('language') != 'dmp':
            self.log.error("Patch language is not dmp", patch_id=patch_id)
            return {'Patch language is not dmp': {'patch_id': patch_id}}

        base_id = patch_block.get('base_id')
        if not base_id or base_id not in self.blocks:
            self.log.error("No base id or base id not found", patch_id=patch_id)
            return {'No base id or base id not found': {'patch_id': patch_id}}

        if code_id in self.blocks:
            self.log.error("Code id already exists", code_id=code_id)
            return {'Code id already exists': {'code_id': code_id}}

        self.log.info("Applying patch", code_id=code_id, base_id=base_id, patch_id=patch_id, filename=filename)

        code = self.blocks[base_id]['content']
        patch = self.blocks[patch_id]['content']
        try:
            diff = self.dmp.patch_fromText(patch)
            new_code, _ = self.dmp.patch_apply(diff, code)
        except Exception as e:
            self.log.error("Failed to apply patch", patch_id=patch_id, base_id=base_id, reason=e)
            return {'Failed to apply patch': {'patch_id': patch_id, 'base_id': base_id, 'reason': str(e)}}
        
        block = {
            'language': self.blocks[base_id]['language'],
            'content': new_code.strip(),
            'filename': filename,
            'base_id': base_id,
            'patch_id': patch_id
        }
        self.blocks[code_id] = block
        self.save_block(block)
        return None

    def parse(self, markdown_text):
        blocks = OrderedDict()
        errors = []
        for match in self.code_pattern.finditer(markdown_text):
            start_json, lang, content, end_json = match.groups()
            try:
                start_meta = json.loads(start_json)
                end_meta = json.loads(end_json)
            except json.JSONDecodeError as e:
                self.console.print_exception(show_locals=True)
                error = {'JSONDecodeError': {'json_str': start_json, 'reason': str(e)}}
                errors.append(error)
                continue

            code_id = start_meta.get("id")
            if code_id != end_meta.get("id"):
                self.log.error("Start and end id mismatch", start_id=code_id, end_id=end_meta.get("id"))
                error = {'Start and end id mismatch': {'start_id': code_id, 'end_id': end_meta.get("id")}}
                errors.append(error)
                continue

            if code_id in blocks or code_id in self.blocks:
                self.log.error("Duplicate code id", code_id=code_id)
                error = {'Duplicate code id': {'code_id': code_id}}
                errors.append(error)
                continue

            block = {
                'language': lang,
                'content': content,
                'base_id': start_meta.get('base_id'),
                'filename': start_meta.get('filename')
            }
            blocks[code_id] = block
            self.log.info("Parsed code block", code_id=code_id, filename=block['filename'])
            self.save_block(block)

        self.blocks.update(blocks)

        exec_ids = []
        cmds = []
        line_matches = self.line_pattern.findall(markdown_text)
        for line_match in line_matches:
            cmd, json_str = line_match
            cmds.append((cmd, json_str))
            try:
                line_meta = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.log.error("Invalid JSON in Code-{cmd} block", json_str=json_str, reason=e)
                error = {f'Invalid JSON in Code-{cmd} block': {'json_str': json_str, 'reason': str(e)}}
                errors.append(error)
                continue

            error = None
            if cmd == 'Patch':
                error = self.apply_patch(line_meta)
            elif cmd == 'Exec':
                exec_id = line_meta.get("id")
                if not exec_id:
                    error = {'Code-Exec block without id': {'json_str': json_str}}
                elif exec_id not in self.blocks:
                    error = {'Code-Exec block not found': {'exec_id': exec_id}}
                else:
                    exec_ids.append(exec_id)
            else:
                error = {f'Unknown command in Code-{cmd} block': {'cmd': cmd}}

            if error:
                errors.append(error)

        return {'errors': errors, 'exec_ids': exec_ids, 'cmds': cmds, 'blocks': blocks}
    
    def get_code_by_id(self, code_id):
        try:    
            return self.blocks[code_id]['content']
        except KeyError:
            self.log.error("Code id not found", code_id=code_id)
            self.console.print("❌ Code id not found", code_id=code_id)
            return None
        
    def get_block_by_id(self, code_id):
        try:
            return self.blocks[code_id]
        except KeyError:
            self.log.error("Code id not found", code_id=code_id)
            self.console.print("❌ Code id not found", code_id=code_id)
            return None
