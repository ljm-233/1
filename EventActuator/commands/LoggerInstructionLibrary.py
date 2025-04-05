"""
LoggerInstructionLibrary.py
日志记录器指令库
"""

# from typing import Callable, Awaitable, Any
import os
import asyncio
from pathlib import Path

from EventActuator import get_actuator
# from EventActuator import Event
from FilesIO import generate_log_header

_actuator_instance = get_actuator()  # 执行器实例
open_log_files = {}  # 全局文件跟踪字典 {path: {"file": file_obj, "hook": hook_func}}


# ================= 创建命令 =================
# 这个test功能作为模板 在此基础上进行添加功能
def register_commands():
    """注册所有命令到全局执行器实例"""

    @_actuator_instance.register("log_open")
    async def log_open(data: dict):
        """打开日志文件并记录句柄"""
        file_mode = data.get("mode", "a")
        hook_func = data.get("hook", None)
        absolute_header = data.get("absolute_path", True)
        raw_path = data["path"]

        # print(f"log_open: data:'absolute_path':{data['absolute_path']},data.get:{data.get('absolute_path', True)}")  # test

        # 使用统一路径解析
        path = _resolve_path(raw_path, absolute_header)

        if path in open_log_files:
            return


        # 创建目录（路径处理已统一）
        dir_path = os.path.dirname(path)
        if dir_path:  # 防止空路径报错
            os.makedirs(dir_path, exist_ok=True)

            # 打开文件并写入头部
            with open(path, file_mode, encoding="utf-8") as file_obj:
                # header_path 直接使用统一处理后的 path
                header_content = ""
                for chunk in generate_log_header(path):  # 简化逻辑，直接使用统一路径
                    header_content += str(chunk)

                file_obj.write(header_content)  # 无需额外的换行符
                file_obj.flush()

        # 保持文件打开状态（移出with块需要特殊处理）
        open_file = open(path, "a", encoding="utf-8")
        str_path = str(path.resolve())  # 使用标准化绝对路径字符串作为键
        open_log_files[str_path] = {
            "file": open_file,
            "hook": hook_func
        }
        print(f"[DEBUG] 已打开文件：{str_path}")  # 调试输出

    @_actuator_instance.register("log_close")
    async def log_close(data: dict):
        """关闭日志文件并执行钩子
        参数：
        - path: 可选，指定关闭的文件路径
        - end_marker: 可选，自定义结束标志内容
        - absolute_path: 是否使用绝对路径定位文件（需与log_open时一致）
        """
        absolute_header = data.get("absolute_path", True)
        target_path: str = data.get("path", "")
        resolved_path = _resolve_path(target_path, absolute_header) if target_path else None  # 统一路径解析逻辑

        # 获取结束标志
        end_marker = data.get("end_marker",
                              getattr(_actuator_instance, "end_msg", "\n=== Log Session Ended ===\n"))

        def _close_file(file_obj):
            """实际关闭文件的内部函数"""
            if end_marker:
                file_obj.write(f"\nend:{repr(end_marker)}\n")
                file_obj.flush()
            file_obj.close()

        if resolved_path:
            # 使用字符串形式的标准路径进行匹配
            str_path = str(resolved_path)
            if str_path in open_log_files:
                entry = open_log_files.pop(str_path)
                _close_file(entry["file"])
                if entry["hook"]:
                    if asyncio.iscoroutinefunction(entry["hook"]):
                        await entry["hook"]()
                    else:
                        entry["hook"]()
        else:
            # 关闭所有文件时直接使用现有路径格式
            for path in list(open_log_files.keys()):
                entry = open_log_files.pop(path)
                _close_file(entry["file"])
                if entry["hook"]:
                    if asyncio.iscoroutinefunction(entry["hook"]):
                        await entry["hook"]()
                    else:
                        entry["hook"]()

    @_actuator_instance.register("log_write")
    async def log_writer(data: dict):
        """写入日志内容"""
        absolute_header = data.get("absolute_path", True)
        raw_path = data["path"]

        # 统一路径解析
        resolved_path = _resolve_path(raw_path, absolute_header)
        str_path = str(resolved_path)  # 转换为字符串用于字典匹配

        if str_path in open_log_files:
            entry = open_log_files[str_path]
            file_obj = entry["file"]
            file_obj.write(f"{data['content']}\n")
            file_obj.flush()
            if data.get("terminal_output", False):
                print(f"[Event] [Logger] 日志写入:{repr(data['content'])}")
        elif data.get("terminal_output", False):
            print(f"[Error] [Logger] 文件未打开:{str_path}")

    # # 示例
    # @_actuator_instance.register("test")
    # async def test(_):
    #     pass

# ================= 根目录配置 =================
# PROJECT_ROOT = Path(__file__).parent.absolute()
PROJECT_ROOT = r"D:\python\MyScripActuator"


def _resolve_path(raw_path: str, use_absolute: bool) -> Path:
    """统一路径解析逻辑（返回Path对象）"""
    path = Path(raw_path)

    if use_absolute:
        return path.absolute()
    else:
        # 转换为相对于项目根目录的路径
        if path.is_absolute():
            # 如果用户传入绝对路径但要求相对模式，转换为项目相对路径
            try:
                return path.relative_to(PROJECT_ROOT)
            except ValueError:
                return PROJECT_ROOT / path
        return PROJECT_ROOT / path

# print(_resolve_path("logs/tests/temp-example", False))

# # 测试用例
# test_cases = [

#     (r"log/tests/", False),    # 纯相对路径
#     (r"/log/tests", False),    # 类Unix绝对路径（需转换）
#     (r"C:\log\tests", False),  # Windows绝对路径（需转换）
#     (r"log/tests", True)       # 绝对路径模式
# ]

#
# for raw, absolute in test_cases:
#     resolved = _resolve_path(raw, absolute)
#     print(f"输入: {raw:<15} 绝对模式: {str(absolute):<5} => 解析结果: {resolved}")


# # ===================== 测试代码 =====================
# async def sample_generator():
#     """示例事件生成器（模拟事件流）"""
#     # # 生成一系列测试事件
#     # yield Event("mouse_move", {"x": 100, "y": 200})
#     # await asyncio.sleep(1)  # 模拟延迟
#     #
#     # yield Event("mouse_click", None)
#     # await asyncio.sleep(0.5)
#     #
#     # yield Event("keyboard_input", {"text": "Hello World!"})
#     # await asyncio.sleep(1)
#     # #
#     # print()
#     # yield Event("get_command", {"return_type": "generator"})
#     # print()
#     # yield Event("get_command", {"return_type": "set"})
#     # print()
#     # yield Event("get_command", {"return_type": "generator", "include_help": True})
#     # print()
#     # yield Event("get_command", {"return_type": "set", "include_help": True})

#     # 打开日志文件（显示原始路径）
#     yield Event("log_open", {
#         "path": "logs/app.log",
#         "absolute_path": False,
#         # "hook":lambda: print(f"[end] {repr(_actuator_instance.end_msg)}"),
#         "hook": None,
#     })

#     # 写入日志
#     yield Event("log_write", {
#         "path": "logs/app.log",
#         "content": "User logged in",
#         "terminal_output": True,
#     })

#     # 关闭文件
#     yield Event("log_close", {"path": "logs/app.log"})

#     yield Event("exit", None)  # 结束事件流


# async def main():
#     """测试主函数"""

#     actuator = _actuator_instance  # 绑定实例

#     register_commands()  # 确保注册额外命令

#     # 绑定示例生成器
#     actuator.bind_generator(sample_generator())

#     # 启动主循环
#     await actuator.main_loop()
#     print("所有事件处理完成")


# if __name__ == "__main__":
#     # 运行测试
#     asyncio.run(main())  # 正确启动事件循环