"""异步桥接核心"""


import asyncio
import copy
import hashlib
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from sys import platform
from typing import AsyncGenerator

import yaml

from EventActuator import Event
from file_manager.core.config_engine import ConfigEngine


@dataclass
class FileEvent:
    operation: str
    payload: dict
    timestamp: float = field(default_factory=time.time)


class AsyncFileBridge:
    def __init__(self, actuator, config):
        self.actuator = actuator
        self.config = config
        self._event_queue = asyncio.Queue(maxsize=1000)
        self._active = True

    async def event_emitter(self) -> AsyncGenerator[Event, None]:
        while self._active or not self._event_queue.empty():
            batch = []
            try:
                while len(batch) < self.config['batch_size']:
                    batch.append(await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=self.config['flush_interval']
                    ))
            except asyncio.TimeoutError:
                pass

            if batch:
                yield Event(
                    event_type=self.config['channel'],
                    data={
                        'operations': batch,
                        'metadata': self._collect_metadata()
                    }
                )

    async def emit_operation(self, op: str, payload: dict):
        await self._event_queue.put(FileEvent(op, payload))

    @asynccontextmanager
    async def lifecycle(self):
        self._active = True
        try:
            yield self
        finally:
            await self._flush_remaining()

    def _collect_metadata(self):
        return {
            'session_id': self.actuator.session_id,
            'host': platform.node(),
            'checksum': hashlib.md5(str(self.config).encode()).hexdigest()
        }


def deep_update(target: dict, source: dict) -> dict:
    """
    递归合并源字典到目标字典，保留嵌套结构
    Args:
        target: 目标字典（默认配置）
        source: 源字典（用户自定义配置）
    Returns:
        合并后的新字典（不会修改原始目标字典）
    """
    # 创建目标字典的深拷贝，避免修改原始数据
    merged = copy.deepcopy(target)

    for key, value in source.items():
        # 如果当前键的值是字典，且目标中已有该键且也是字典，则递归合并
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = deep_update(merged[key], value)
        else:
            # 直接覆盖非字典类型或新键
            merged[key] = copy.deepcopy(value)
    return merged

# 1. 合并列表（需定制）
# 如果需要合并列表而不是覆盖，可以扩展函数：
#
# def deep_update(target, source):
#     merged = copy.deepcopy(target)
#     for key, value in source.items():
#         if key not in merged:
#             merged[key] = copy.deepcopy(value)
#         else:
#             if isinstance(value, dict):
#                 merged[key] = deep_update(merged[key], value)
#             elif isinstance(value, list):
#                 merged[key] = merged[key] + value  # 合并列表
#             else:
#                 merged[key] = value
#     return merged


# 加载和解析配置文件
def load_configuration(config_path: str, env_overrides: dict = None) -> dict:
    """加载并解析配置文件

    Args:
        config_path: 配置文件路径
        env_overrides: 可覆盖配置的环境变量字典

    Returns:
        解析后的配置字典
    """
    path = Path(config_path)

    # 检查文件存在性
    if not path.exists():
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    # 读取文件内容
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yml', '.yaml']:
            config = yaml.safe_load(f)
        elif path.suffix == '.json':
            config = json.load(f)
        else:
            raise ValueError("不支持的配置文件格式")

    # 应用环境变量替换
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = replace_env_vars(v)
        elif isinstance(obj, str) and obj.startswith('{env:'):
            var_name = obj[5:-1]
            return os.environ.get(var_name, '')
        return obj

    config = replace_env_vars(config)

    # 合并环境变量覆盖
    if env_overrides:
        config = deep_update(config, env_overrides)

    # 基本路径处理
    if 'base_dir' in config:
        base = Path(config['base_dir']).expanduser().resolve()
        config['base_dir'] = str(base)
        base.mkdir(parents=True, exist_ok=True)

    return config

    # 可选的扩展实现部分
    # 添加动态模板引擎（示例）
    #     from jinja2 import Template
    #     with open(config_path) as f:
    #         raw_content = f.read()
    #     rendered = Template(raw_content).render(env=os.environ)
    #     config = yaml.safe_load(rendered)
    #
    #     # 添加配置版本迁移
    #     if '__version__' in config:
    #         migrate_config(config)
    #
    #     # 添加Schema验证（示例使用Pydantic）
    #     from pydantic import BaseModel
    #     class ConfigSchema(BaseModel):
    #         file_manager: dict
    #         monitoring: dict | None
    #
    #     validated_config = ConfigSchema(**config).dict()
    #
    #     # 添加缓存机制
    #     if not hasattr(load_configuration, 'cache'):
    #         load_configuration.cache = {}
    #
    #     file_hash = hashlib.md5(path.read_bytes()).hexdigest()
    #     if file_hash in load_configuration.cache:
    #         return load_configuration.cache[file_hash]
    #
    #     load_configuration.cache[file_hash] = validated_config
    #     return validated_config


# 初始化文件管理器
async def setup_file_manager(actuator):
    # 读取配置文件
    config = load_configuration("config/log_manager.yml")

    # 创建配置引擎实例
    config_engine = ConfigEngine(
        template_path="templates/log_template.json",
        env_vars=os.environ
    )

    # 构建运行时配置
    runtime_config = config_engine.build(config['file_manager'])

    # 创建异步文件桥接器
    file_bridge = AsyncFileBridge(
        actuator=actuator,
        config=runtime_config
    )

    # 绑定到事件执行器
    actuator.register_adapter(
        adapter_type="file",
        instance=file_bridge,
        channel=config['file_manager']['channel']
    )

    # 启动后台任务
    async with actuator.create_task_group() as tg:
        tg.create_task(file_bridge.event_generator())
        tg.create_task(file_bridge.config_watcher())

    return file_bridge