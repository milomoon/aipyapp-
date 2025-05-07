#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from collections import Counter
from dataclasses import dataclass, field

from loguru import logger

@dataclass
class ChatMessage:
    role: str
    content: str
    reason: str = None
    name: str = None
    usage: Counter = field(default_factory=Counter)

class ChatHistory:
    def __init__(self):
        self.messages = []
        self._total_tokens = Counter()

    def __len__(self):
        return len(self.messages)
    
    def json(self):
        return [msg.__dict__ for msg in self.messages]
    
    def add(self, role, content):
        self.add_message(ChatMessage(role=role, content=content))

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self._total_tokens += message.usage

    def get_usage(self):
        return iter(row.usage for row in self.messages if row.role == "assistant")
    
    def get_summary(self):
        summary = {'time': 0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        summary.update(dict(self._total_tokens))
        summary['rounds'] = sum(1 for row in self.messages if row.role == "assistant")
        return summary

    def get_messages(self):
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

class Session:
    def __init__(self, manager, stream_processor=None):
        self.manager = manager
        self.client = manager.current
        self.stream_processor = stream_processor
        self.log = logger.bind(src='session')
        self.history = ChatHistory()

    @property
    def name(self):
        return self.client.name
    
    def use(self, name):
        self.client = self.manager[name]

    def chat(self, prompt, system_prompt=None, name=None):
        client = self.manager[name] if name else self.client
        start = time.time()
        response = client(self.history.get_messages(), prompt, system_prompt=system_prompt)
        if not response: 
            return None
        
        if not response.stream:
            response.parse()
        else:
            self.stream_processor(client.name, response.parse_stream())

        cm = response.message
        if cm:
            end = time.time()
            cm.name = client.name
            cm.usage['time'] = round(end - start, 3)
            if system_prompt:
                self.history.add("system", system_prompt)
            self.history.add("user", prompt)
            self.history.add_message(cm)
        return cm
    
    