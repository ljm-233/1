# 这是一个测试 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。


import asyncio
from aioconsole import ainput
from typing import Optional, AsyncGenerator
from FilesIO import get_json_processor, load_events
from EventActuator import Event, get_actuator

_actuator = get_actuator()
_processor = get_json_processor()


async def empty_generator() -> AsyncGenerator[Event, None]:
    """符合规范的初始化空生成器"""
    return
    yield  # 仅为满足类型提示  请忽略这个弱警告

async def command_handler():
    help_text = """
===== 事件流控制终端 =====
命令列表：
start <路径> [数量] - 启动事件流（可选数量限制）
pause               - 暂停事件流
resume              - 恢复事件流
clear               - 清空事件缓存
list                - 显示最近10个事件
quit                - 退出程序
"""
    print(help_text)

    while True:
        try:
            cmd = (await ainput(">>> ")).strip()
            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action == "quit":
                print("正在安全关闭...")
                # await _actuator.shutdown()
                return

            elif action == "start":
                if len(parts) < 2:
                    print("需要提供文件路径")
                    continue

                path = parts[1]
                limit = int(parts[2]) if len(parts) > 2 else None
                await handle_start(path, limit)

            elif action == "pause":
                _processor.pause_stream()
                print("事件流已暂停")

            elif action == "resume":
                _processor.resume_stream()
                print("事件流已恢复")

            elif action == "clear":
                _processor.clear_cache()
                print("缓存已清空")

            elif action == "list":
                show_recent_events()

            else:
                print(f"未知命令: {cmd}")

        except Exception as e:
            print(f"错误: {str(e)}")


async def handle_start(path: str, limit: Optional[int]):
    if _processor.is_active:
        print("正在停止当前流...")
        _processor.pause_stream()

    async def controlled_gen():
        count = 0
        async for event_dict in load_events(path):
            if limit and count >= limit:
                print(f"已达数量限制 {limit}")
                _processor.pause_stream()
                break
            yield Event(event_dict["event_type"], event_dict["data"])
            count += 1

    _actuator.bind_generator(controlled_gen())
    _processor.resume_stream()
    print(f"已启动 {path}{f' 数量限制: {limit}' if limit else ''}")


def show_recent_events():
    if _processor.cache_size == 0:
        print("缓存为空")
        return

    print("\n最近事件:")
    for idx, event in enumerate(reversed(_processor.cached_events)):
        if idx >= 10:
            break
        print(f"[{_processor.cache_size - idx}] {event['event_type']}: {event['data']}")


async def main():
    # 初始化绑定空生成器
    _actuator.bind_generator(empty_generator())

    # 启动命令处理和事件循环
    await asyncio.gather(
        _actuator.main_loop(),
        command_handler()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n安全终止程序")