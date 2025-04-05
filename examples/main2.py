# 这是一个测试 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。


import asyncio

from EventActuator import Event, get_actuator
_actuator_instance = get_actuator()  # 确保实例的获取

from EventActuator.commands.LoggerInstructionLibrary import register_commands
register_commands()  # 确保注册额外命令

from FilesIO import *

# 日志写入规则的配置
log_rules = {
    "file_name": f"example-{name_file(mode='date', suffix='.txt.log')}",
    "path": "logs/tests/",
    "terminal_output": True,  # 终端输出
    "absolute_path": False,
}

async def main():
    async def event_gen():

        # 打开日志文件（显示原始路径）
        yield Event("log_open", {
            "path": f"{log_rules.get('path', 'log/tests/')}{log_rules.get('file_name', f'temp-{name_file()}')}",  # 这里由于字符串嵌套上限 可能很难向name_file传值
            "absolute_path": False,
            # "hook":lambda: print(f"[end] {repr(_actuator_instance.end_msg)}"),
            "hook": lambda: print(f"[Logger] file closed, path: \"{log_rules.get('path', 'log/tests/')}{log_rules.get('file_name', f'temp-{name_file()}')} \""),
            "terminal_output": True,
        })

        # 写入日志
        yield Event("log_write", {
            "path": f"{log_rules.get('path', 'log/tests/')}{log_rules.get('file_name', f'temp-{name_file()}')}",
            "content": "[Event] [Login] User logged in",
            "absolute_path": False,
            "terminal_output": True,
        })

        # 关闭文件
        yield Event("log_close", {
            "path": f"{log_rules.get('path', '/log/tests')}{log_rules.get('file_name', f'temp-{name_file()}')}",
            "absolute_path": False,
        })

        yield Event("exit", None)  # 结束事件流

    _actuator_instance.bind_generator(event_gen())
    await _actuator_instance.main_loop()


if __name__ == "__main__":
    asyncio.run(main())  # 正确启动事件循环