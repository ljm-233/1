"""
MyScripActuator 包入口文件
初始化时自动注册内置命令
"""

from .core import Actuator, Event, get_actuator, _actuator_instance
from .commands import basic  # 导入即完成注册

__all__ = ['Actuator', 'Event', 'get_actuator', 'commands']
__version__ = '0.2.0'

# 初始化时自动注册的验证
assert 'sleep' in _actuator_instance.commands, "内置命令注册失败"