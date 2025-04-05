import asyncio
from collections import defaultdict
from typing import Callable, Dict, List


class HookRegistry:
    def __init__(self):
        self._hooks = defaultdict(list)
        self._hook_priorities = defaultdict(dict)

    def register(self, hook_point: str, handler: Callable, priority: int = 100):
        self._hooks[hook_point].append(handler)
        self._hook_priorities[hook_point][handler] = priority
        self._hooks[hook_point].sort(
            key=lambda x: self._hook_priorities[hook_point][x],
            reverse=True
        )

    async def trigger(self, hook_point: str, context: Dict):
        for hook in self._hooks[hook_point]:
            if asyncio.iscoroutinefunction(hook):
                await hook(context)
            else:
                hook(context)

    def get_hooks(self, hook_point: str) -> List[Callable]:
        return self._hooks[hook_point].copy()