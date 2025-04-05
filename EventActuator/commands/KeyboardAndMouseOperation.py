"""
KeyboardAndMouseOperation.py
键鼠操作的命令的注册
"""


# from typing import Callable, Awaitable, Any
import pyautogui

from EventActuator import get_actuator
_actuator_instance = get_actuator()


# ================= 创建命令 =================
def register_commands():
    """注册所有命令到全局执行器实例"""

    @_actuator_instance.register("click")
    async def handle_click(data: dict):
        # 添加坐标参数检查
        if "x" not in data or "y" not in data:
            raise ValueError("缺少坐标参数")
        pyautogui.click(data["x"], data["y"])
        print(f"在 ({data['x']}, {data['y']}) 执行点击")

    @_actuator_instance.register("input")
    async def handle_input(data: str):
        pyautogui.typewrite(data)
        print(f"输入文本: {data}")

    @_actuator_instance.register("mouse_move_abs")
    async def mouse_move_abs(data: dict):  # 移除 self 参数
        x, y = data["x"], data["y"]
        pyautogui.moveTo(x, y)
        print(f"移动到绝对坐标 ({x}, {y})")

    @_actuator_instance.register("mouse_move")
    async def _mouse_move(data):
        """
        鼠标移动命令处理函数
        参数data：需包含x和y坐标的字典，如{"x":100, "y":200}
        """
        x = data["x"]
        y = data["y"]
        pyautogui.moveTo(x, y)
        print(f"鼠标已移动到 ({x}, {y})")

    @_actuator_instance.register("mouse_click")
    async def _mouse_click(_):
        """执行鼠标点击（不需要参数）"""
        pyautogui.click()
        print("已执行鼠标点击")

    @_actuator_instance.register("keyboard_input")
    async def _keyboard_input(data):
        """键盘输入文本"""
        text = data["text"]
        pyautogui.typewrite(text)
        print(f"已输入文本：{text}")

    # 可继续添加更多命令...