"""
EventActuator.py
一个可通过注册命令执行事件的核心执行器
"""
# import asyncio
from typing import AsyncGenerator, Any, Awaitable, Callable, Generator, Union, Dict, Tuple, Set

# ================= 核心类 =================
# 定义事件数据类，用于封装事件信息
class Event:
    """表示一个待执行的操作事件"""

    def __init__(self, event_type: str, data: Any):
        self.type = event_type  # 事件类型，对应注册的命令名
        self.data = data  # 事件携带的数据，传递给命令函数


class Actuator:  # 只负责执行，不关心事件来源
    """事件操作执行器（核心类）"""

    def __init__(self):
        """
        初始化执行器
        - commands: 存储已注册的命令（类型名 → 处理函数）
        - generator: 事件生成器，外部传入的事件源
        - running: 控制主循环的运行状态
        - end_msg: 决定结束时输出
        - _allowed_vars： 决定setting功能的无防呆白名单
        - _super_do_flag:
        """
        self.commands: dict[str, Callable[[Any], Awaitable[None]]] = {}  # 命令注册表（字典结构）  # 类型注解
        self.generator = None  # 事件生成器（需通过bind_generator设置）
        self.running = False  # 主循环运行标志 为False时候停止主循环
        self.end_msg = "0" # 结束提示信息 保证兼容性采用字符串 实际上应使用数值
        self._allowed_vars = {'end_msg', 'generator'}  # 初始白名单
        # self._super_do_flag = False  # 设定setting权限  # 冗余设计
        self._validators = {  # 初始化需要限制的值的类型的内容
            'end_msg': (str,),
            '_super_do_flag': (bool,),
            '_allowed_vars': (set,)
        }

    # ================= 核心方法 =================
    def register(self, name: str):
        """
        命令注册装饰器（重点理解）
        用法：@actuator.register("命令名")
              def 处理函数(event)
        功能：将函数注册到commands字典，使事件能触发对应函数
        """

        def decorator(func: Callable[[Any], Awaitable[None]]):
            self.commands[name] = func
            return func
        return decorator

    def bind_generator(self, gen: AsyncGenerator[Event, None]):
        """
        绑定事件生成器（生成器需异步生成Event对象）
        参数gen：一个异步生成器，通过async for循环产出事件
        例如：从文件、网络或用户输入获取事件
        """
        self.generator = gen

    def stop(self):
        """停止主循环"""
        self.running = False

    async def main_loop(self):
        """
        启动异步主循环（事件处理核心）
        流程：
        1. 检查是否已绑定生成器
        2. 循环获取生成器中的事件
        3. 查找并执行对应的命令处理函数
        4. 直到生成器结束或收到停止信号
        """
        if not self.generator:
            raise RuntimeError("[Error] Event generator must be bound first!")  # 必须先绑定事件生成器

        self.running = True
        try:
            # 异步迭代事件生成器
            async for event in self.generator:  # 完全解耦
                if not self.running:
                    break  # 收到停止信号

                # 查找对应的命令处理函数
                handler = self.commands.get(event.type)
                if handler:
                    try:
                        # 执行命令，并传入事件数据
                        await handler(event.data)
                    except Exception as e:
                        print(f"[Error] Error executing command {event.type}: {str(e)}")  # 事件执行错误处理
                else:
                    print(f"[Unknown] Unknown command type: {event.type}")  # 未知事件处理
        finally:
            self.running = False

    # ================= 额外方法 =================

    def get_commands_info(self,
                          include_help: bool = False,
                          return_type: str = 'set'
                          ) -> Union[
        Dict[str, Union[Set[str], Generator[str, None, None]]],  # include_help=False时的返回类型
        Dict[str, Union[Set[Tuple[str, str]], Generator[Tuple[str, str], None, None]]]  # include_help=True时的
    ]:
        """
        获取已注册命令的信息

        参数:
            include_help (bool): 是否包含帮助信息
            return_type (str): 返回类型，可选 'set' 或 'generator'

        返回:
            返回结构保持统一字典格式：
            - 当include_help=False时：{'commands': Set/Generator}
            - 当include_help=True时：{'commands': Set/Generator, 'help': Dict}
        """

        # 生成基础命令集合/生成器
        commands = self.commands.keys()

        # 处理基础命令结构
        if return_type == 'generator':
            base_commands = (cmd for cmd in commands)
        elif return_type == 'set':
            base_commands = set(commands)
        else:
            raise ValueError("return_type parameter must be 'set' or 'generator'")

        # 构建基础结果字典
        result = {'commands': base_commands}

        # 添加帮助信息
        if include_help:
            help_dict = {
                cmd: (func.__doc__ or "").strip()
                for cmd, func in self.commands.items()
            }
            result['help'] = help_dict

        return result

    def configure_allowed_vars(self, allowed_vars):
        """
        动态配置白名单（自动合并默认变量）
        :param allowed_vars: 要添加的白名单变量列表
        """
        if allowed_vars is not None:
            # 合并用户输入与默认白名单
            self._allowed_vars.update(allowed_vars)
        # 确保始终包含核心变量
        self._allowed_vars |= {'running', 'commands'}

    def setting(self, name, value, supper_do=False):
        """
        安全设置方法（核心逻辑）
        特殊操作：
        - name = "__allow__" 时添加白名单
        - name = "__disallow__" 时移除白名单
        """
        # 白名单管理操作
        if name == "__allow__":
            self._allowed_vars.add(value)
            return
        elif name == "__disallow__":
            if value in self._allowed_vars:
                self._allowed_vars.remove(value)
            return

        # 类型检查（如果定义了校验规则）
        if name in self._validators:
            if not isinstance(value, self._validators[name]):
                allowed_types = "|".join(t.__name__ for t in self._validators[name])
                raise TypeError(f"{name} must be of type {allowed_types}")

        setattr(self, name, value)

        # 常规变量设置校验
        if not supper_do and name not in self._allowed_vars:
            raise PermissionError(
                f"The variable {name} is not in the whitelist, the currently allowed variables:{self.white_list}"
            )
        setattr(self, name, value)

    def found(self, name):
        """安全查找方法（允许查找未初始化的白名单变量）"""
        if name in self._allowed_vars:
            return getattr(self, name, None)  # 返回 None 如果未初始化
        raise AttributeError(f"变量 {name} 既不在白名单也不存在")

    @property
    def white_list(self):
        """获取当前白名单（返回不可变副本）"""
        return frozenset(self._allowed_vars)

    def __str__(self):
        defined_vars = {k: v for k, v in vars(self).items() if k != '_allowed_vars'}
        return f"Actuator(white_list:{self.white_list}, variables_defined:{defined_vars})"

# ================= 全局配置 =================

_actuator_instance = Actuator()  # 先创建实例

def get_actuator() -> Actuator:
    """获取单例实例的推荐方式"""
    return _actuator_instance