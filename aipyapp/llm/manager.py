#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

from loguru import logger

from .base_openai import OpenAIBaseClient
from .client_ollama import OllamaClient
from .client_claude import ClaudeClient
from .session import Session
from .. import Stoppable, event_bus, T

class OpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'
    PARAMS = {'stream_options': {'include_usage': True}}

class GeminiClient(OpenAIBaseClient): 
    BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/'
    MODEL = 'gemini-2.5-pro-exp-03-25'
    PARAMS = {'stream_options': {'include_usage': True}}

class DeepSeekClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.deepseek.com'
    MODEL = 'deepseek-chat'

class GrokClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.x.ai/v1/'
    MODEL = 'grok-3-mini'
    PARAMS = {'stream_options': {'include_usage': True}}

class TrustClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.trustoken.ai/v1'
    MODEL = 'auto'
    PARAMS = {'stream_options': {'include_usage': True}}

class AzureOpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'

    def __init__(self, config):
        super().__init__(config)
        self._end_point = config.get('endpoint')

    def usable(self):
        return super().usable() and self._end_point
    
    def _get_client(self):
        from openai import AzureOpenAI
        return AzureOpenAI(azure_endpoint=self._end_point, api_key=self._api_key, api_version="2024-02-01")

CLIENTS = {
    "openai": OpenAIClient,
    "ollama": OllamaClient,
    "claude": ClaudeClient,
    "gemini": GeminiClient,
    "deepseek": DeepSeekClient,
    'grok': GrokClient,
    'trust': TrustClient,
    'azure': AzureOpenAIClient
}

class ClientManager(object):
    def __init__(self, settings):
        self.clients = {}
        self.default = None
        self.current = None
        self._last = None
        self.log = logger.bind(src='client_manager')
        self.init_clients(settings)

    def _init_client(self, config):
        proto = config.get("type", "openai")

        client = CLIENTS.get(proto.lower())
        if not client:
            self.log.error('Unsupported LLM provider', proto=proto)
            return None
        return client(config)
    
    def init_clients(self, settings):
        names = defaultdict(set)
        for name, config in settings.llm.items():
            if not config.get('enable', True):
                names['disabled'].add(name)
                continue

            try:
                client = self._init_client(config)
            except Exception as e:
                self.log.exception('Error creating LLM client', name=name, config=config)
                names['error'].add(name)
                continue
            
            if not client or not client.usable():
                names['disabled'].add(name)
                self.log.error('LLM client not usable', name=name, config=config)
                continue

            names['enabled'].add(name)
            client.name = name
            self.clients[name] = client

            if config.get('default', False) and not self.default:
                self.default = client
                names['default'] = name

        if not self.default:
            name = list(self.clients.keys())[0]
            self.default = self.clients[name]
            names['default'] = name

        self.current = self.default
        self.names = names

    def __len__(self):
        return len(self.clients)
    
    def __repr__(self):
        return f"Current: {'default' if self.current == self.default else self.current}, Default: {self.default}"

    def __contains__(self, name):
        return name in self.clients

    def __getitem__(self, name):
        return self.clients[name]
    
    @property
    def enabled(self):
        return self.names['enabled']
    
    @property
    def last(self):
        return self._last.name if self._last else None
    
    def use(self, name):
        self.current = self[name]

    def get_client(self, name, default=None):
        return self.clients.get(name, default)
    
    def Session(self, name=None):
        client = self[name] if name else self.current
        session = Session(self)
        session.client = client
        return session
