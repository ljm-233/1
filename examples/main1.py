import asyncio
import os

from EventActuator import Event, Actuator
from file_manager.core.async_bridge import AsyncFileBridge
from file_manager.core.config_engine import ConfigEngine
from file_manager.hooks.registry import HookRegistry


# from file_manager import AsyncFileBridge, ConfigEngine, HookRegistry


async def main(sanitize_input=None, archive_logs=None):
    # 初始化事件执行器
    actuator = Actuator()

    # 加载配置文件
    config_engine = ConfigEngine.from_yaml("config/prod_logging.yml")
    config = config_engine.build(env_vars=os.environ)

    # 创建文件桥接器
    file_bridge = AsyncFileBridge(actuator, config)

    # 注册内置钩子
    registry = HookRegistry()
    registry.register('pre_write', sanitize_input, priority=90)
    registry.register('post_rotate', archive_logs, priority=50)

    # 绑定到事件执行器
    async with file_bridge.lifecycle():
        actuator.register_channel('file_ops', file_bridge.event_emitter())

        # 示例事件流
        async def generate_events():
            yield Event("log_open", {"app": "demo"})
            for i in range(100):
                yield Event("log_write", {
                    "message": f"Event {i}",
                    "level": "INFO"
                })
            yield Event("log_close", {"status": "normal"})

        await actuator.run(generate_events())


if __name__ == "__main__":
    asyncio.run(main())