# 这是一个测试 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。


import asyncio

from EventActuator import Event, get_actuator
_actuator_instance = get_actuator()  # 确保实例的获取

from EventActuator.commands.KeyboardAndMouseOperation import register_commands
register_commands()  # 确保注册额外命令

# from FileIO import *


async def main():
    async def event_gen():
        # 使用直接导入的 Event 类
        yield Event("mouse_move", {"x": 100, "y": 200})
        yield Event("keyboard_input", {"text": "Hello World"})
        # yield Event("exit", None)
        yield Event("exit", {"end": "所有操作已完成"})  # 替换原来的 None

    _actuator_instance.bind_generator(event_gen())
    await _actuator_instance.main_loop()


if __name__ == "__main__":
    asyncio.run(main())  # 正确启动事件循环