import asyncio
import json
import os
import datetime
import aiofiles
from ast import literal_eval
from collections import deque
from os import PathLike
from typing import Generator, Dict, Union, Optional, AsyncGenerator, Callable, Any, Deque
from datetime import datetime


# __all__ = ["get_files", "name_file", "generate_log_header", "check_directory", ]
__all__ = ['JSONEventProcessor', 'get_json_processor', 'load_events']

def get_files(
        directory: Union[str, PathLike[str]],
        max_depth: int = 2,
        absolute: bool = False
) -> Generator[Dict[str, Union[str, None]], None, None]:
    """
    遍历指定目录下的文件和文件夹，生成包含信息的字典生成器

    :param directory: 要遍历的根目录路径（支持字符串或PathLike对象）
    :param max_depth: 最大嵌套层数（默认2层）
    :param absolute: 是否返回绝对路径（默认False返回相对路径）
    :yield: 包含path、name、suffix和Disk（Windows）的字典
    """
    # 类型安全处理输入路径
    safe_directory = str(directory)
    start_directory = os.path.abspath(safe_directory)
    is_windows = os.name == 'nt'

    for root, dirs, files in os.walk(start_directory):
        # 计算当前路径信息
        current_path = os.path.abspath(root)
        rel_path = os.path.relpath(current_path, start_directory)

        # 计算当前深度
        current_depth = 0 if rel_path == '.' else len(rel_path.split(os.path.sep))

        # 深度控制逻辑
        if current_depth > max_depth:
            del dirs[:]  # 阻止继续深入遍历
            continue

        # 处理子目录
        for dir_name in dirs[:]:  # 使用副本遍历
            # 构建安全路径并处理类型
            subdir_path = os.path.join(root, dir_name)
            safe_subdir = str(subdir_path)  # 强制转换为字符串

            # 计算绝对路径和盘符
            abs_subdir_path = os.path.abspath(safe_subdir)
            drive, path_part = os.path.splitdrive(abs_subdir_path)

            # 构造返回路径
            if absolute:
                path = path_part if is_windows else abs_subdir_path
            else:
                path = os.path.relpath(abs_subdir_path, start_directory)

            # 统一路径分隔符
            normalized_path = path.replace(os.sep, '/')

            # 构建条目
            entry = {
                'path': normalized_path,
                'name': dir_name,
                'suffix': 'folder'
            }
            if is_windows:
                entry['Disk'] = drive
            yield entry

        # 处理文件
        for filename in files:
            # 构建安全路径
            full_path = os.path.join(root, filename)
            safe_full_path = str(full_path)  # 强制类型转换

            # 计算绝对路径和盘符
            abs_full_path = os.path.abspath(safe_full_path)
            drive, path_part = os.path.splitdrive(abs_full_path)

            # 构造返回路径
            if absolute:
                path = path_part if is_windows else abs_full_path
            else:
                path = os.path.relpath(abs_full_path, start_directory)

            # 统一路径分隔符
            normalized_path = path.replace(os.sep, '/')

            # 分割文件名和后缀
            if '.' in filename:
                name_part, suffix_part = filename.split('.', 1)
            else:
                name_part = filename
                suffix_part = None

            # 构建条目
            entry = {
                'path': normalized_path,
                'name': name_part,
                'suffix': suffix_part
            }
            if is_windows:
                entry['Disk'] = drive
            yield entry


# # 使用示例
# if __name__ == "__main__":
#     # 默认日期格式 + 后缀
#     print(name_file(suffix="log"))  # 输出类似：07-15_14-30.log
#
#     # 自定义日期格式
#     print(name_file("date", file_name="%Y%m%d", suffix="data"))  # 类似：20230715.data
#
#     # 序号模式带后缀
#     print(name_file("number", suffix=".txt"))  # file_0001.txt
#     print(name_file("number", suffix="bak"))   # file_0002.bak
#
#     # 直接命名模式
#     print(name_file("name", file_name='"report"', suffix="pdf"))  # report.pdf
#     print(name_file("name", file_name="'data'", suffix="csv"))    # data.csv
#
#     # 无效后缀处理
#     print(name_file(suffix=123))  # 忽略后缀 → 07-15_14-30  # 这段是用于测试错误情况的，IDE会有弱警告很正常
#     print(name_file(suffix=True)) # 忽略 → 07-15_14-30


_NAMED_COUNTERS = {}  # 全局计数器存储字典

def name_file(
        mode: str = "date",
        counter_name: str = "NAMED_NUM",
        file_name: Optional[str] = None,
        suffix: Union[bool, str] = False
) -> Optional[str]:
    """
    多功能文件名生成函数

    :param mode: 生成模式 - date/number/name
    :param counter_name: 计数器名称（仅number模式有效）
    :param file_name: 格式字符串（date模式）或带引号文件名（name模式）
    :param suffix: 文件后缀（字符串类型自动处理点号）
    :return: 生成的文件名 或 None
    """
    # 初始化
    base_name = None  # 决定基础名称 并防止后续设计忘记添加未定义错误的处理

    # 日期模式改进
    if mode == "date":
        fmt = "%m-%d_%H-%M"  # 默认格式
        if file_name:
            fmt = file_name  # 直接使用字符串，分类try

        # 尝试生成格式
        try:
            # 严格捕获格式错误
            base_name = datetime.now().strftime(fmt)
        except ValueError as ve:
            # 格式无效时回退默认格式
            print(f"Invalid format {fmt}, using default. Error: {ve}")
            base_name = datetime.now().strftime("%m-%d_%H-%M")

    # 序号模式
    elif mode == "number":
        if counter_name not in _NAMED_COUNTERS:
            _NAMED_COUNTERS[counter_name] = 0
        _NAMED_COUNTERS[counter_name] += 1
        base_name = f"file_{_NAMED_COUNTERS[counter_name]:04d}"

    # 直接命名模式改进
    elif mode == "name":
        if not file_name:
            return None

        try:
            # 精确捕获字面量解析错误
            parsed_name = literal_eval(file_name)
            if not isinstance(parsed_name, str):
                return None
            base_name = parsed_name
        except (SyntaxError, ValueError) as se:
            # 明确记录解析错误
            print(f"Invalid filename literal: {file_name}. Error: {se}")
            return None

    # 处理无效模式
    else:
        return base_name  # 原设计是直接返回None 但是这会导致初始化base_name时候的变量未使用

    # 处理后缀
    if isinstance(suffix, str):
        suffix = suffix.strip()
        if suffix:
            # 自动补全点号
            if not suffix.startswith("."):
                suffix = f".{suffix}"
            base_name += suffix

    return base_name


# if __name__ == '__main__':
#     # Windows测试
#     print("Windows测试：")
#     for item in get_files('D:\python\MyScripActuator\saves', max_depth=2, absolute=True):
#         print(item)
#
#     # # Linux测试
#     # print("\nLinux测试：")
#     # for item in get_files('/home/user/docs', absolute=False):
#     #     print(item)


def generate_log_header(file_path, absolute_path=True, date: (bool, str) = False, date_format="%m-%d_%H-%M"):
    """
    生成日志文件的开头内容

    :param file_path: 判断日志文件是否存在 避免日志内容不准确
    :param absolute_path: 是否是绝对路径
    :param date: 需要填入的日期
    :param date_format: 日期格式 用于统一调用格式 非必要不要改
    :return:
    """
    # 处理文件路径并生成第一行内容
    # line1 = None
    if absolute_path:
        # 尝试作为绝对路径
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            line1 = abs_path
        else:
            # 尝试作为项目根目录下的相对路径（假设项目根目录为当前工作目录）
            project_root = os.getcwd()
            combined_path = os.path.join(project_root, file_path)
            combined_abs_path = os.path.abspath(combined_path)
            if os.path.exists(combined_abs_path):
                line1 = combined_abs_path
            else:
                return  # 无法生成第一行，生成器结束
    else:
        # 直接作为相对路径处理
        if os.path.exists(file_path):
            line1 = file_path
        else:
            return  # 无法生成第一行，生成器结束

    # 生成第二行内容
    line2 = "\n"
    if isinstance(date, str):
        try:
            # 尝试解析日期字符串（示例支持ISO格式和自定义格式）
            # 尝试常见格式，如ISO 8601
            dt = datetime.fromisoformat(date)
            formatted_date = dt.strftime(date_format)
            line2 = f"{formatted_date}\n"
        except ValueError:
            # 尝试其他格式，例如dateutil解析器可处理更多格式（需安装python-dateutil）
            # 此处简化处理，可根据需求扩展
            pass

    # 第三行暂时固定换行
    line3 = "\n"

    # 以生成器形式返回各行内容
    yield f"{line1}\n"
    yield line2
    yield line3


# print("a")
# # 示例1：绝对路径存在，date为有效日期字符串
# gen = generate_log_header(r"D:\python\MyScripActuator\saves\test\help.txt", date="2023-10-05T14:30:00")
# for line in gen:
#     print(line, end='')
#
# print("b")
# # 示例2：相对路径存在，date无效
# gen = generate_log_header(r"D:\python\MyScripActuator\saves\test\help.txt", absolute_path=False, date="123")
# for line in gen:
#     print(line, end='')
#
# print("c")
# # 示例3：路径不存在，生成器无输出
# gen = generate_log_header("nonexistent.log")
# print(list(gen))  # 输出空列表


def check_directory(path: str, absolute_path: bool = False, create_if_missing: bool = False) -> bool:
    """全局目录检测函数"""
    # 路径解析
    if not absolute_path:
        base_dir = os.getcwd()
        full_path = os.path.normpath(os.path.join(base_dir, path.lstrip("/")))
    else:
        full_path = path

    # 检查/创建目录
    if os.path.exists(full_path):
        return os.path.isdir(full_path)

    if create_if_missing:
        try:
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Directory creation failed: {str(e)}")
            return False
    return False


# ================= 超级json读取器 =================

# ================= 内置静态功能 =================
def _process_raw_event(raw: Dict) -> Dict:
    """统一事件处理逻辑（静态方法优化）"""
    if "type" not in raw:
        raise ValueError("Missing required 'type' field in event")

    return {
        "event_type": raw["type"],
        "data": {k: v for k, v in raw.items() if k != "type"}
    }


# ================= 全局单例 =================
_json_processor_instance = None  # 暂时不需要直接创建实例


# ================= 解析器类 =================
class JSONEventProcessor:
    def __init__(self):
        self._file_lock = asyncio.Lock()
        self._event_cache: Deque = deque()
        self._hooks = []
        self._active = True

    async def stream_events(self, path: str) -> AsyncGenerator[Dict[str, Any], None]:
        """核心流式事件生成方法

        Args:
            path: JSON文件路径

        Yields:
            标准化事件字典（包含event_type和data两个键）

        功能特点：
            - 异步文件锁保证文件读取原子性
            - 自动转换原始JSON事件结构
            - 实时缓存和钩子触发
            - 支持流暂停/恢复控制
        """
        # 使用异步锁确保同一时间只有一个协程读取文件
        async with self._file_lock:  # 🔒 防止多个消费者同时读取文件

            # 异步打开文件（使用aiofiles实现真正的异步IO）
            async with aiofiles.open(path, 'r') as f:  # 📂 非阻塞文件操作

                # 加载并解析JSON数据
                raw_data = json.loads(await f.read())  # ⏳ 异步等待文件读取完成

                # 遍历原始事件数据
                for raw_event in raw_data:  # 🔄 逐个处理事件

                    # 检查流控制状态
                    if not self._active:  # ⏸️ 暂停状态检测
                        await self._wait_for_resume()  # ⏳ 等待恢复

                    # 处理原始事件格式
                    processed = self._process_raw_event(raw_event)  # 🛠️ 标准化转换
                    if not processed:
                        continue

                    # 生成事件（核心产出点）
                    yield processed  # 🚀 产出事件到调用方

                    # 更新缓存并触发钩子
                    self._event_cache.append(processed)  # 💾 存入缓存
                    await self._trigger_hooks()  # 📡 通知所有监听者

    # ================= 内置功能 =================
    @staticmethod
    def _process_raw_event(raw: Dict) -> Dict:
        """统一事件处理逻辑"""
        if "type" not in raw:
            raise ValueError("Missing required 'type' field in event")

        return {
            "event_type": raw["type"],
            "data": {k: v for k, v in raw.items() if k != "type"}
        }

    @property
    def is_active(self) -> bool:
        """流状态访问接口"""
        return self._active

    @property
    def list_events(self) -> list:
        """安全访问缓存副本"""
        return list(self._event_cache)

    @property
    def cache_size(self) -> int:
        """缓存数量查询"""
        return len(self._event_cache)

    @property
    def cached_events(self) -> tuple:
        """返回不可修改的缓存副本"""
        return tuple(self._event_cache)

    # ================= 扩展控制接口 =================
    def register_hook(self, callback: Callable):
        """注册钩子函数的参数验证"""
        if not callable(callback):
            raise TypeError("钩子必须为可调用对象")
        self._hooks.append(callback)

    def clear_cache(self):
        """清空事件缓存"""
        self._event_cache.clear()

    def pause_stream(self):
        """暂停事件流（线程安全）

        效果：
        - 立即停止后续事件产出
        - 保持当前状态直到resume被调用
        """
        self._active = False

    def resume_stream(self):
        """恢复事件流"""
        self._active = True

    async def _trigger_hooks(self):
        """触发已注册的钩子"""
        for hook in self._hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(self._event_cache)
            else:
                hook(self._event_cache)

    async def _wait_for_resume(self):
        pass


# ================= 获取方式 =================
def get_json_processor() -> JSONEventProcessor:
    """获取全局单例实例"""
    global _json_processor_instance
    if not _json_processor_instance:
        _json_processor_instance = JSONEventProcessor()
    return _json_processor_instance


# ================= 简化版API =================
async def load_events(path: str) -> AsyncGenerator[Dict[str, Any], None]:
    """简化的事件加载入口函数"""
    processor = get_json_processor()
    async for event in processor.stream_events(path):
        yield event


# class LoggerOperator:
#     """日志管理器"""
#
#     def __init__(self):
#         """日志文件根目录"""
#         self.root_directory = {  # 记录日志文件的根目录
#             "main": {  # 主要日志目录
#                 "path": "/saves/logs",  # 路径
#                 "absolute_path": False,  # 是否是绝对路径
#                 "currently_processed": name_file(mode="date") # 当前处理的文件
#             },
#             "temp": {  # 暂存日志的目录
#                 "path": "/temp/logs",
#                 "absolute_path": False,  # 是否是绝对路径
#             }
#         }
#
#         # 创建执行器
#         from EventMainActuator import Event, get_actuator
#         _actuator_instance = get_actuator()  # 确保实例的获取
#
#         from LoggerInstructionLibrary import register_commands
#         register_commands()  # 确保注册额外命令
#
#     # ================= 核心方法 =================
#
#     def verify_directory(self, level_name: str) -> bool:
#         """校验指定级别的目录结构"""
#         if level_name not in self.root_directory:
#             return False
#
#         config = self.root_directory[level_name]
#         return check_directory(
#             path=config["path"],
#             absolute_path=config["absolute_path"],
#             create_if_missing=True
#         )
#
#     def verify_all_directories(self) -> dict:
#         """校验所有目录结构"""
#         results = {}
#         for level_name in self.root_directory:
#             results[level_name] = self.verify_directory(level_name)
#         return results
#
#     def _handle_directory_check(self):
#         """执行目录检查的核心逻辑"""
#         check_results = self.verify_all_directories()
#
#         for level_name, success in check_results.items():
#             if not success:
#                 self._handle_directory_error(level_name)
#
#     def _handle_directory_error(self, level_name: str):
#         """处理目录校验失败的情况"""
#         print(f"Critical error: {level_name} directory validation failed")
#         # 这里可以添加更复杂的错误处理逻辑，比如：
#         # 1. 尝试重新创建目录
#         # 2. 切换到备用目录
#         # 3. 触发警报通知
#
#     # def found_file(self, path=""):
#     #     """
#     #     包装get_files函数
#     #
#     #     :param path: 默认指向 self.root_directory["main"]["path"]
#     #     :return: 返回的内容将会是生成器
#     #     """
#     #     if not path:
#     #         path = self.root_directory["main"]["path"]
#     #     return get_files(path)
#
#     async def main_loop(self):
#         """主事件处理器"""
#
#         # 一. 检查需要使用的日志文件夹的情况 并自动处理
#
#         # 1. 需要防止日志文件夹在程序执行过程中被删除或是路径不存在的问题
#         # 目录检查处理
#         self._handle_directory_check()
#
#         # pending_files = self.found_file()
#         # for item in pending_files:
#         #     pass
#
#
# # ================= 全局配置 =================
#
# _loggerOperator_instance = LoggerOperator()  # 先创建实例
#
#
# def get_actuator() -> LoggerOperator:
#     """获取单例实例的推荐方式"""
#     return _loggerOperator_instance