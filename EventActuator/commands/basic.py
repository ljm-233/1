"""
内置命令模块
导入时自动注册到执行器实例
"""
from ctypes import cast
from typing import Dict

from EventActuator.core import get_actuator
import asyncio

__version__ = 0.0  # 这个库估计并不会更新版本 但是导入的时候没事情干

_actuator_instance = get_actuator()

def basic_command_version(printing=True):
    if printing:
        print(f"basic_command_lib version:{__version__}")

# ================= 内置命令 =================
# 通过装饰器注册内置命令
@_actuator_instance.register("sleep")
async def _sleep(data):  # 移除self参数
    """正确参数签名：只接收data"""
    await asyncio.sleep(data["sleep"])  # 使用异步sleep
    print(f"已休眠 {data['duration']} 秒")

@_actuator_instance.register("exit")
async def handle_exit(data):
    """传递退出事件，清理资源，并停止执行器"""
    # 防止不存在变量
    if not _actuator_instance.end_msg:
        _actuator_instance.end_msg = "0"

    # 参数验证
    if data is None:
        data = {"end": _actuator_instance.end_msg}
    elif data["end"]:
        data["end"] = _actuator_instance.end_msg

    # 安全获取结束信息 避免遇到未能处理的未知情况
    end_msg = data.get("end", "0")

    # 调用停止执行功能的函数 或是改成直接修改运行状态self.running的也行
    _actuator_instance.stop()
    print(f"[END]: {end_msg}")

    # # 可选清理操作
    # pyautogui.moveTo(0, 0)  # 示例：重置鼠标位置

@_actuator_instance.register("get_command")
async def handle_commands(data):
    """修复后的命令信息处理器"""
    # 参数提取与验证
    return_type = data.get("return_type", "generator")
    include_help = data.get("include_help", False)

    # 获取命令信息
    try:
        cmds_info = _actuator_instance.get_commands_info(
            return_type=return_type,
            include_help=include_help
        )
    except ValueError as e:
        print(f"[ERROR] 参数错误: {str(e)}")
        return

    # 统一处理逻辑
    print("\n=== 命令列表 ===")
    if return_type == 'generator':
        # 处理生成器类型
        for cmd in cmds_info['commands']:
            print(f"- {cmd}")
    else:
        # 处理集合类型
        for cmd in sorted(cmds_info['commands']):
            print(f"- {cmd}")

    # 处理帮助信息
    if include_help:
        help_info = cast(Dict[str, str], cmds_info['help'])  # 类型断言明确help字段是字典
        # 运行时安全性：cast 不会改变实际运行行为，只是类型提示，需确保代码逻辑实际返回的是字典
        print("\n=== 帮助信息 ===")
        for cmd, help_text in help_info.items():  # 关键修复点  # 不再有警告
            print(f"{cmd}: {help_text or '无帮助信息'}")
