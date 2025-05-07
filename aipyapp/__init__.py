import threading
from importlib import resources
from typing import Callable, Any, Dict, List

from loguru import logger

from .i18n import T, set_lang, get_system_language

__version__ = '0.1.28b5'

__resources__ = f'{__package__}.res'
__resources_path__ = resources.files(__resources__)

class Stoppable():
    def __init__(self):
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()
    
    def wait(self, timeout=None):
        return self._stop_event.wait(timeout)
    
    def reset(self):
        self._stop_event.clear()

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}
        self.log = logger.bind(src='eventbus')
        
    def __repr__(self):
        return repr(self._listeners)
    
    def register(self, event_name: str, handler: Callable[..., Any]):
        self._listeners.setdefault(event_name, []).append(handler)

    def broadcast(self, event_name: str, *args, **kwargs):
        for handler in self._listeners.get(event_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                self.log.exception('Error broadcasting event', event_name=event_name, handler=handler)

    def pipeline(self, event_name: str, data, **kwargs):
        for handler in self._listeners.get(event_name, []):
            try:
                data = handler(data, **kwargs)
            except Exception as e:
                self.log.exception('Error processing event', event_name=event_name, handler=handler)
        return data

    def collect(self, event_name: str, *args, **kwargs):
        try:
            ret = [handler(*args, **kwargs) for handler in self._listeners.get(event_name, [])]
        except Exception as e:
            ret = []
            self.log.exception('Error collecting event', event_name=event_name, args=args, kwargs=kwargs)
        return ret

    def __call__(self, event_name: str, *args, **kwargs):
        return self.pipeline(event_name, *args, **kwargs)

event_bus = EventBus()

__all__ = ['Stoppable', 'EventBus', 'event_bus', '__version__', 'T', 'set_lang', '__resources__', 'get_system_language']
    