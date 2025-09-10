from __future__ import annotations

import time
import subprocess
import logging
import re

from datetime import datetime
from typing import Any, TypedDict, Union

# 元梦之星农场自动化脚本 - PC端调试器
# 版本: v2.4.1 (触摸事件修复版)
# 更新时间: 2025-08-12
# 更新内容: 修复process_touch_event函数的竞态条件问题，确保点击/滑动正确识别
# 负责人: Claude Code Assistant

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('move_debugger.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 配置参数 ====================
# 时间间隔参数 (单位: 秒) - 与auto_game.sh保持一致
DEFAULT_INTERVAL = 0.5    # 命令之间的默认间隔 (500ms)
KEY_INTERVAL = 0.2        # 按键之间的间隔 (200ms)
SEQ_INTERVAL = 2.0        # 命令序列之间的间隔 (2000ms)

# ADB Keycode Mappings for WASD and a common "action" key (e.g., J for Enter/OK)
# 这些是标准的Android keycode值 - 与auto_game.sh保持一致
KEYCODE_W = "51"  # W键 - 向上移动
KEYCODE_A = "29"  # A键 - 向左移动
KEYCODE_S = "47"  # S键 - 向下移动
KEYCODE_D = "32"  # D键 - 向右移动
KEYCODE_ACTION = "38"  # J键 - 通常用于确认/动作

# 键位映射字典，方便查找
KEYMAP = {
    "W": KEYCODE_W,
    "A": KEYCODE_A,
    "S": KEYCODE_S,
    "D": KEYCODE_D,
    "J": KEYCODE_ACTION
}


# ==================== 核心类定义 ====================

class DeviceState:
    """
    设备状态管理类 - 实现"一次初始化，全程信任"的核心原则
    负责在程序启动时一次性获取并存储所有设备信息
    """
    
    def __init__(self) -> None:
        """初始化设备状态对象"""
        self.is_valid: bool = False           # 设备状态是否有效
        self.device_info: str | None = None         # 设备基本信息
        self.screen_width: int | None = None        # 屏幕宽度
        self.screen_height: int | None = None       # 屏幕高度
        self.screen_orientation: int | None = None  # 屏幕方向
        self.touch_device: dict[str, Union[int, str]] | None = None        # 触摸设备信息
        # touch_device格式: {'device': '/dev/input/eventX', 'max_x': 4095, 'max_y': 4095}
    
    def initialize_all(self) -> bool:
        """
        一次性初始化所有设备信息
        
        返回值:
        - bool: 初始化是否成功
        """
        logger.info("开始初始化设备状态...")
        try:
            # 第一步：检查ADB连接
            if not self._check_adb_connection():
                logger.error("ADB连接检查失败")
                return False
                
            # 第二步：获取屏幕分辨率和方向
            screen_info = self._get_screen_resolution()
            if not screen_info:
                logger.error("屏幕信息获取失败") 
                return False
            self.screen_width, self.screen_height = screen_info
            
            # 获取屏幕方向
            self.screen_orientation = self._get_screen_orientation()
            
            # 第三步：查找触摸设备
            self.touch_device = self._find_touch_device()
            if not self.touch_device:
                logger.error("触摸设备查找失败")
                return False
            
            # 所有步骤成功完成
            self.is_valid = True
            logger.info("设备状态初始化成功")
            logger.info(f"屏幕: {self.screen_width}x{self.screen_height}")
            if isinstance(self.touch_device, dict):
                device_path = self.touch_device.get('device')
                if isinstance(device_path, str):
                    logger.info(f"触摸设备: {device_path}")
            return True
            
        except Exception as e:
            logger.error(f"设备初始化失败: {e}")
            self.is_valid = False
            return False
    
    def _check_adb_connection(self) -> bool:
        """检查ADB连接状态（私有方法）"""
        logger.info("检查ADB连接状态...")
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
            output = result.stdout.strip()
            logger.info(f"ADB devices输出: {output}")

            lines = output.split('\n')
            if len(lines) < 2:
                logger.error("没有检测到连接的设备")
                return False

            devices = [line for line in lines[1:] if line.strip() and 'device' in line]
            if not devices:
                logger.error("没有检测到在线的设备")
                return False

            logger.info(f"检测到 {len(devices)} 个设备: {devices}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("ADB命令超时")
            return False
        except FileNotFoundError:
            logger.error("找不到ADB命令，请确保ADB已安装并添加到PATH")
            return False
        except Exception as e:
            logger.error(f"检查ADB连接时出错: {e}")
            return False
    
    def _get_screen_resolution(self) -> tuple[int, int] | None:
        """获取屏幕分辨率（私有方法）"""
        logger.info("获取屏幕分辨率...")
        try:
            result = subprocess.run(
                ["adb", "shell", "wm", "size"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                logger.info(f"屏幕尺寸输出: {output}")
                
                # 解析输出，格式通常为 "Physical size: 1080x2340"
                size_part = output.split(':')[-1].strip()
                parts = size_part.split('x')
                if len(parts) != 2:
                    logger.error(f"无法解析屏幕分辨率: {output}")
                    return None
                width, height = map(int, parts)
                logger.info(f"屏幕分辨率: {width}x{height}")
                return width, height
            else:
                logger.error(f"获取屏幕分辨率失败: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("获取屏幕分辨率超时")
            return None
        except Exception as e:
            logger.error(f"获取屏幕分辨率时出错: {e}")
            return None
    
    def _get_screen_orientation(self) -> int:
        """获取屏幕方向（私有方法）"""
        logger.info("获取屏幕方向...")
        try:
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "window", "displays"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                logger.warning(f"无法获取屏幕方向信息: {result.stderr}")
                return 1  # 默认横屏
                
            output = result.stdout
            rotation_match = re.search(r'mDisplayRotation=ROTATION_(\d+)', output)
            if rotation_match:
                degrees = int(rotation_match.group(1))
                rotation = degrees // 90
                logger.info(f"检测到屏幕方向: {rotation}")
                return rotation
            else:
                logger.warning("无法解析屏幕方向，默认返回横屏")
                return 1
                
        except Exception as e:
            logger.warning(f"获取屏幕方向时出错: {e}")
            return 1  # 默认横屏
    
    def _find_touch_device(self) -> dict[str, Union[int, str]] | None:
        """查找触摸设备（私有方法）"""
        logger.info("开始查找触摸设备...")
        
        try:
            result = subprocess.run(
                ["adb", "shell", "getevent", "-p", "-l"], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            if result.returncode != 0:
                logger.error(f"执行 getevent -p -l 失败: {result.stderr}")
                return None
            
            # 使用现有的设备块解析方法
            device_blocks = self._split_device_blocks(result.stdout)
            logger.info(f"发现 {len(device_blocks)} 个输入设备")
            
            # 解析每个设备块查找触摸设备
            for device_block in device_blocks:
                device_info = self._parse_device_block(device_block)
                if device_info:  # 找到有效的触摸设备
                    logger.info(f"找到符合条件的触摸设备: {device_info['device']}")
                    logger.info(f"坐标范围 - X: 0-{device_info['max_x']}, Y: 0-{device_info['max_y']}")
                    return device_info

            logger.error("未找到任何具有ABS_MT_POSITION_X和ABS_MT_POSITION_Y的触摸设备")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("getevent命令执行超时")
            return None
        except Exception as e:
            logger.error(f"查找触摸设备时出错: {e}")
            return None
    
    def _split_device_blocks(self, output: str) -> list[str]:
        """将getevent -p -l的输出按设备分割成独立的块"""
        blocks = []
        current_block = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('add device') and '/dev/input/event' in line:
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
            elif current_block:
                current_block.append(line)
        
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _parse_device_block(self, device_block: str) -> dict[str, Union[int, str]] | None:
        """解析单个设备块，提取设备路径和坐标信息"""
        device_match = re.search(r'(/dev/input/event\d+)', device_block)
        if not device_match:
            return None
        
        device_path = device_match.group(1)
        
        x_match = re.search(r'ABS_MT_POSITION_X.*?max\s+(\d+)', device_block)
        y_match = re.search(r'ABS_MT_POSITION_Y.*?max\s+(\d+)', device_block)
        
        if x_match and y_match:
            max_x = int(x_match.group(1))
            max_y = int(y_match.group(1))
            return {
                'device': device_path,
                'max_x': max_x,
                'max_y': max_y
            }
        
        return None

class ADBExecutor:
    """
    ADB命令执行类 - 统一处理所有ADB相关操作
    依赖DeviceState，不再进行重复的连接检查
    """
    
    def __init__(self, device_state: DeviceState) -> None:
        """初始化ADB执行器"""
        self.device_state = device_state
        if not device_state.is_valid:
            raise ValueError("DeviceState必须已成功初始化")
    
    def _run_adb_command(self, shell_command: str, timeout: int = 5) -> bool:
        """
        执行ADB shell命令（私有方法）
        
        参数:
        - shell_command: shell命令（不包含'adb shell'前缀）
        - timeout: 超时时间（秒）
        
        返回值:
        - bool: 命令是否执行成功
        """
        try:
            command = f"adb shell {shell_command}"
            logger.debug(f"执行ADB命令: {command}")
            
            result = subprocess.run(
                command.split(), 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.debug(f"命令执行成功: {shell_command}")
                return True
            else:
                logger.error(f"命令执行失败 (返回码: {result.returncode}): {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {shell_command}")
            return False
        except Exception as e:
            logger.error(f"执行命令时出错: {e}")
            return False
    
    def press_key(self, keycode: str, count: int, delay: float = KEY_INTERVAL) -> bool:
        """
        执行按键操作（使用longpress方法）
        
        参数:
        - keycode: 按键代码
        - count: 按键次数
        - delay: 按键间隔（秒）
        
        返回值:
        - bool: 是否全部按键成功
        """
        key_name = next((k for k, v in KEYMAP.items() if v == keycode), f"keycode_{keycode}")
        logger.info(f"执行按键操作: {key_name} (keycode: {keycode}), 次数={count}")
        
        success_count = 0
        for i in range(count):
            logger.debug(f"第 {i+1}/{count} 次长按...")
            if self._run_adb_command(f"input keyevent --longpress {keycode}"):
                success_count += 1
                logger.debug(f"第 {i+1} 次长按成功")
            else:
                logger.error(f"第 {i+1} 次长按失败")
            
            if i < count - 1:
                time.sleep(delay)
        
        logger.info(f"按键操作完成: 成功 {success_count}/{count} 次")
        return success_count == count
    
    def tap_screen(self, x: int, y: int) -> bool:
        """
        执行屏幕点击
        
        参数:
        - x: X坐标
        - y: Y坐标
        
        返回值:
        - bool: 点击是否成功
        """
        logger.info(f"执行屏幕点击: 坐标 ({x}, {y})")
        success = self._run_adb_command(f"input tap {x} {y}")
        if success:
            logger.info(f"屏幕点击成功: ({x}, {y})")
        else:
            logger.error(f"屏幕点击失败: ({x}, {y})")
        return success
    
    def swipe_screen(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> bool:
        """
        执行屏幕滑动
        
        参数:
        - x1, y1: 起始坐标
        - x2, y2: 结束坐标
        - duration: 滑动持续时间（毫秒）
        
        返回值:
        - bool: 滑动是否成功
        """
        logger.info(f"执行屏幕滑动: ({x1},{y1}) → ({x2},{y2}), 持续时间: {duration}ms")
        success = self._run_adb_command(f"input swipe {x1} {y1} {x2} {y2} {duration}")
        if success:
            logger.info(f"屏幕滑动成功: ({x1},{y1}) → ({x2},{y2})")
        else:
            logger.error(f"屏幕滑动失败: ({x1},{y1}) → ({x2},{y2})")
        return success

# ==================== 工具函数 ====================

def convert_touch_coordinates(raw_x: int, raw_y: int, max_x: int, max_y: int, screen_width: int, screen_height: int, orientation: int = 1) -> tuple[int, int]:
    """支持屏幕旋转的坐标转换函数"""
    x_norm = raw_x / max_x
    y_norm = raw_y / max_y
    if orientation == 0:
        screen_x = int(x_norm * screen_width)
        screen_y = int(y_norm * screen_height)
    elif orientation == 1:
        screen_x = int(y_norm * screen_height)
        screen_y = int((1 - x_norm) * screen_width)
    elif orientation == 2:
        screen_x = int((1 - x_norm) * screen_width)
        screen_y = int((1 - y_norm) * screen_height)
    elif orientation == 3:
        screen_x = int((1 - y_norm) * screen_height)
        screen_y = int(x_norm * screen_width)
    else:
        screen_x = int(x_norm * screen_width)
        screen_y = int(y_norm * screen_height)
    logger.debug(f"坐标转换: 原始({raw_x},{raw_y}) -> 屏幕({screen_x},{screen_y}) [方向:{orientation}]")
    return screen_x, screen_y


# ==================== 系统初始化与组件工厂 ====================

class SystemComponents:
    """
    系统组件容器类 - 实现依赖注入模式的组件管理
    遵循SOLID原则中的依赖倒置和单一职责原则
    """
    
    def __init__(self) -> None:
        """初始化组件容器"""
        self.device_state: DeviceState | None = None
        self.adb_executor: ADBExecutor | None = None
        self.touch_recorder: TouchEventRecorder | None = None
        self.is_initialized: bool = False
    
    def initialize_system(self) -> bool:
        """
        统一初始化系统所有组件
        
        实现KISS原则 - 提供一个简单的初始化入口
        实现SOLID原则 - 各组件职责分离，统一管理依赖关系
        
        返回值:
        - bool: 系统是否初始化成功
        """
        logger.info("开始初始化系统组件...")
        
        try:
            # 第一步：初始化设备状态
            logger.info("步骤1/3: 初始化设备状态...")
            self.device_state = DeviceState()
            if not self.device_state.initialize_all():
                logger.error("设备状态初始化失败")
                return False
            logger.info("设备状态初始化成功")
            
            # 第二步：创建ADB执行器
            logger.info("步骤2/3: 创建ADB执行器...")
            self.adb_executor = ADBExecutor(self.device_state)
            logger.info("ADB执行器创建成功")
            
            # 第三步：创建触摸事件记录器
            logger.info("步骤3/3: 创建触摸事件记录器...")
            self.touch_recorder = TouchEventRecorder(self.device_state, self.adb_executor)
            logger.info("触摸事件记录器创建成功")
            
            self.is_initialized = True
            logger.info("系统组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            self.is_initialized = False
            return False
    
    def get_device_state(self) -> DeviceState:
        """获取设备状态实例"""
        if not self.is_initialized or self.device_state is None:
            raise RuntimeError("系统未初始化，请先调用initialize_system()")
        return self.device_state
    
    def get_adb_executor(self) -> ADBExecutor:
        """获取ADB执行器实例"""
        if not self.is_initialized or self.adb_executor is None:
            raise RuntimeError("系统未初始化，请先调用initialize_system()")
        return self.adb_executor
    
    def get_touch_recorder(self) -> TouchEventRecorder:
        """获取触摸事件记录器实例"""
        if not self.is_initialized or self.touch_recorder is None:
            raise RuntimeError("系统未初始化，请先调用initialize_system()")
        return self.touch_recorder


class TouchEventRecorder:
    """触摸事件记录器类 - v2.3"""
    def __init__(self, device_state: DeviceState, adb_executor: ADBExecutor):
        """
        初始化触摸事件记录器
        
        参数:
        - device_state: DeviceState实例，提供设备信息
        - adb_executor: ADBExecutor实例，提供ADB命令执行能力
        """
        # 验证依赖有效性
        if not device_state.is_valid:
            raise ValueError("DeviceState必须已成功初始化")
        
        self.device_state: DeviceState = device_state
        self.adb_executor: ADBExecutor = adb_executor
        self.recording: bool = False
        self.recorded_commands: list[RecordedCommand] = []
        self.output_file: str = "touch_commands.txt"
        # 从device_state获取触摸设备信息
        self.working_touch_device: dict[str, Union[int, str]] | None = device_state.touch_device
        self.process: subprocess.Popen[str] | None = None
        # 添加时间跟踪属性，用于计算命令间隔
        self.previous_command_time: float | None = None

    def start_recording_menu(self) -> None:
        """触摸参数记录器主菜单"""
        while True:
            print("\n" + "="*60 + "\n              触摸参数记录器\n" + "="*60)
            print("1. 查找并设置触摸设备")
            print("2. 显示原始触摸事件 (调试用)")
            print("3. 开始记录触摸事件")
            print("4. 手动记录坐标 (备选方案)")
            print("5. 查看已记录的命令")
            print("6. 保存命令到文件")
            print("7. 清空记录")
            print("8. 测试生成的命令")
            print("Q. 返回主菜单")
            choice = input("\n请选择操作: ").strip().upper()
            menu = {'1': self.find_and_set_touch_device, '2': self.show_raw_touch_events, '3': self.start_touch_recording,
                    '4': self.manual_coordinate_recording, '5': self.show_recorded_commands, '6': self.save_commands_to_file,
                    '7': self.clear_records, '8': self.test_generated_commands}
            if choice == 'Q': break
            if choice in menu: 
                _ = menu[choice]()
            else: print("❌ 无效选择，请重新输入")

    def find_and_set_touch_device(self) -> str | None:
        """查找并设置工作触摸设备"""
        print("\n=== 查找触摸设备 ===")
        # 现在从注入的device_state获取触摸设备信息
        if self.device_state.touch_device:
            self.working_touch_device = self.device_state.touch_device
            device_path = self.working_touch_device['device']
            if isinstance(device_path, str):
                print(f"已设置工作触摸设备: {device_path}")
                print(f"坐标范围 - X: 0-{self.working_touch_device['max_x']}, Y: 0-{self.working_touch_device['max_y']}")
                return device_path
            else:
                print("❌ 设备路径类型错误")
                return None
        else:
            print("❌ 设备状态中未找到可用的触摸设备")
            return None

    def start_touch_recording(self) -> None:
        """开始记录触摸事件"""
        print("\n=== 触摸事件记录 ===")
        if not self.working_touch_device:
            print("⚠️ 未找到工作触摸设备，正在查找...")
            if not self.find_and_set_touch_device():
                print("❌ 无法找到可用的触摸设备，请使用手动记录功能")
                return
        device_path_val = self.working_touch_device.get('device') if isinstance(self.working_touch_device, dict) else None
        if not isinstance(device_path_val, str):
            print("❌ 触摸设备路径无效")
            return
        device_path = device_path_val
        print(f"使用已找到的触摸设备: {device_path}")
        print("请在手机屏幕上进行滑动或点击操作 (按 Ctrl+C 停止记录)")
        
        # 重置时间跟踪，开始新的记录会话
        self.previous_command_time = None
        print("⏰ 时间跟踪已重置，开始记录...")
        
        try:
            self.recording = True
            self.listen_touch_events(device_path)
        except KeyboardInterrupt:
            print("\n⏹️ 停止记录")
        except Exception as e:
            print(f"❌ 记录过程中出现错误: {e}")
        finally:
            self.recording = False
            if self.process:
                try:
                    self.process.terminate()
                except Exception:
                    pass
                self.process = None

    def listen_touch_events(self, device_path: str):
        """监听触摸事件"""
        # 使用注入的adb_executor执行getevent命令
        command = f"getevent {device_path}"
        self.process = subprocess.Popen(
            ["adb", "shell", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        if self.process.stdout is None:
            print("❌ 无法读取触摸事件流")
            return
        current_touch: dict[str, Any] = {'is_touching': False}
        while self.recording:
            line = self.process.stdout.readline()
            if not line: break
            if line.strip():
                event_data = self.parse_event_line(line.strip())
                if event_data:
                    self.process_touch_event(event_data, current_touch)
        # Cleanup is handled in start_touch_recording's finally block

    def parse_event_line(self, line: str) -> dict[str, int] | None:
        """解析getevent输出行"""
        try:
            if line.startswith('['):
                line = line[line.find(']') + 1:].strip()
            parts = line.split()
            if len(parts) >= 3:
                return {'type': int(parts[-3], 16), 'code': int(parts[-2], 16), 'value': int(parts[-1], 16)}
        except (ValueError, IndexError):
            return None
        return None

    def process_touch_event(self, event: dict[str, int], current_touch: dict[str, Any]) -> None:
        """处理单个触摸事件 - 修复版v2.4.1"""
        if event['type'] == 3:  # EV_ABS
            if event['code'] == 0x35:  # ABS_MT_POSITION_X
                # 修复竞态条件：无论is_touching状态如何，都记录第一个坐标为起始坐标
                if 'start_x' not in current_touch:
                    current_touch['start_x'] = event['value']
                    # 如果还没记录开始时间，现在记录（处理事件顺序问题）
                    if 'start_time' not in current_touch:
                        current_touch['start_time'] = time.time()
                        current_touch['is_touching'] = True
                        print("👆 检测到触摸开始 (坐标优先)")
                current_touch['end_x'] = event['value']
            elif event['code'] == 0x36:  # ABS_MT_POSITION_Y
                # 修复竞态条件：无论is_touching状态如何，都记录第一个坐标为起始坐标
                if 'start_y' not in current_touch:
                    current_touch['start_y'] = event['value']
                    # 如果还没记录开始时间，现在记录（处理事件顺序问题）
                    if 'start_time' not in current_touch:
                        current_touch['start_time'] = time.time()
                        current_touch['is_touching'] = True
                        print("👆 检测到触摸开始 (坐标优先)")
                current_touch['end_y'] = event['value']
        elif event['type'] == 1 and event['code'] == 0x14a:  # EV_KEY, BTN_TOUCH
            if event['value'] == 1:
                # BTN_TOUCH按下事件：如果坐标事件还没触发，设置基础状态
                if 'start_time' not in current_touch:
                    current_touch.update({'is_touching': True, 'start_time': time.time()})
                    print("👆 检测到触摸开始 (按钮优先)")
                else:
                    # 坐标事件已经处理过了，只更新状态
                    current_touch['is_touching'] = True
            elif event['value'] == 0:
                current_touch['is_touching'] = False
                current_touch['end_time'] = time.time()
                print("👆 检测到触摸结束")
                self.generate_touch_command(current_touch)
                current_touch.clear()
                current_touch['is_touching'] = False

    def generate_touch_command(self, touch_data: dict[str, Any]) -> None:
        """根据触摸数据生成命令"""
        required_keys = ['start_x', 'start_y', 'end_x', 'end_y', 'start_time', 'end_time']
        if not all(key in touch_data for key in required_keys): return
        
        # 从注入的device_state获取屏幕信息
        screen_width = self.device_state.screen_width
        screen_height = self.device_state.screen_height
        orientation = self.device_state.screen_orientation if isinstance(self.device_state.screen_orientation, int) else 1
        if screen_width is None or screen_height is None or not isinstance(self.working_touch_device, dict):
            print("❌ 无法获取屏幕或触摸设备信息，无法生成命令")
            return
        max_x_val = self.working_touch_device.get('max_x')
        max_y_val = self.working_touch_device.get('max_y')
        if not isinstance(max_x_val, int) or not isinstance(max_y_val, int):
            print("❌ 触摸设备坐标范围无效")
            return

        start_x, start_y = convert_touch_coordinates(
            int(touch_data['start_x']), int(touch_data['start_y']),
            int(max_x_val), int(max_y_val),
            int(screen_width), int(screen_height), int(orientation)
        )
        end_x, end_y = convert_touch_coordinates(
            int(touch_data['end_x']), int(touch_data['end_y']),
            int(max_x_val), int(max_y_val),
            int(screen_width), int(screen_height), int(orientation)
        )
        duration = int((touch_data['end_time'] - touch_data['start_time']) * 1000)
        distance = int(((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5)

        # 计算与前一个命令的时间间隔
        current_time = touch_data['end_time']
        interval_before = None
        if self.previous_command_time is not None:
            interval_before = int((current_time - self.previous_command_time) * 1000)  # 转换为毫秒
        self.previous_command_time = current_time

        if distance < 20:
            command = f"{start_x},{start_y}"
            command_type = "点击"
        else:
            command = f"SWIPE:{start_x},{start_y},{end_x},{end_y},{duration}"
            command_type = "滑动"
        print(f"生成{command_type}命令: {command}")
        
        # 记录命令时包含时间间隔信息
        command_record: RecordedCommand = {
            'type': command_type, 
            'command': command, 
            'start_pos': (start_x, start_y), 
            'end_pos': (end_x, end_y), 
            'duration': duration, 
            'distance': distance, 
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'interval_before': interval_before  # 添加间隔时间字段
        }
        self.recorded_commands.append(command_record)

    def manual_coordinate_recording(self) -> None:
        """手动记录坐标的备选方案"""
        print("\n=== 手动坐标记录 ===")
        while True:
            choice = input("选择操作: 1.点击 2.滑动 3.完成\n> ").strip()
            if choice == '1':
                try:
                    x, y = map(int, input("输入X,Y坐标 (e.g., 540,960): ").split(','))
                    self.recorded_commands.append({'type': '点击', 'command': f"{x},{y}", 'start_pos': (x, y), 'end_pos': (x, y), 'duration': 0, 'distance': 0, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    print(f"已记录点击: {x},{y}")
                except ValueError: print("❌ 格式错误")
            elif choice == '2':
                try:
                    x1, y1 = map(int, input("输入起始X,Y坐标: ").split(','))
                    x2, y2 = map(int, input("输入结束X,Y坐标: ").split(','))
                    duration = int(input("输入持续时间(ms): ") or "500")
                    command = f"SWIPE:{x1},{y1},{x2},{y2},{duration}"
                    self.recorded_commands.append({'type': '滑动', 'command': command, 'start_pos': (x1, y1), 'end_pos': (x2, y2), 'duration': duration, 'distance': 0, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    print(f"已记录滑动: {command}")
                except ValueError: print("❌ 格式错误")
            elif choice == '3': break
            else: print("❌ 无效选择")

    def show_raw_touch_events(self) -> None:
        """显示原始触摸事件代码 (调试用)"""
        print("\n=== 显示原始触摸事件代码 (调试用) ===")
        if not self.working_touch_device:
            if not self.find_and_set_touch_device(): return
        device_path_val = self.working_touch_device.get('device') if isinstance(self.working_touch_device, dict) else None
        if not isinstance(device_path_val, str):
            print("❌ 触摸设备路径无效")
            return
        device_path = device_path_val
        # 从注入的device_state获取屏幕信息
        screen_width = self.device_state.screen_width
        screen_height = self.device_state.screen_height
        if screen_width is None or screen_height is None:
            return
        print("=" * 80)
        if self.working_touch_device:
            print(f"📱 监控设备: {device_path} | 传感器: {self.working_touch_device['max_x']}x{self.working_touch_device['max_y']} | 屏幕: {screen_width}x{screen_height}")
        else:
            print(f"📱 监控设备: {device_path} | 屏幕: {screen_width}x{screen_height}")
        print("=" * 80 + "\n⏹️  按 Ctrl+C 停止监听\n")
        try:
            command = f"adb shell getevent {device_path}"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            if process.stdout is None:
                print("❌ 无法读取事件输出")
                return
            current_x, current_y = 0, 0
            while True:
                line = process.stdout.readline()
                if not line: break
                if line.strip():
                    event = self.parse_event_line(line.strip())
                    if event:
                        if event['type'] == 3 and event['code'] == 0x35: current_x = event['value']
                        elif event['type'] == 3 and event['code'] == 0x36: current_y = event['value']
                        elif event['type'] == 0 and event['code'] == 0 and current_x > 0:
                            wd = self.working_touch_device if isinstance(self.working_touch_device, dict) else None
                            if not wd:
                                break
                            max_x = wd.get('max_x'); max_y = wd.get('max_y')
                            if not isinstance(max_x, int) or not isinstance(max_y, int):
                                break
                            orient = self.device_state.screen_orientation if isinstance(self.device_state.screen_orientation, int) else 1
                            sx, sy = convert_touch_coordinates(
                                int(current_x), int(current_y),
                                int(max_x), int(max_y),
                                int(screen_width), int(screen_height),
                                int(orient)
                            )
                            print(f"原始: ({current_x:5d}, {current_y:5d}) -> 屏幕: ({sx:4d}, {sy:4d})")
        except KeyboardInterrupt:
            print("监听完成")
        finally:
            if self.process is not None:
                try:
                    self.process.terminate()
                    self.process = None
                except Exception:
                    pass

    def show_recorded_commands(self) -> None:
        """显示已记录的命令"""
        if not self.recorded_commands:
            print("❌ 暂无记录的命令")
            return
        print(f"\n=== 已记录的命令 (共 {len(self.recorded_commands)} 条) ===")
        for i, record in enumerate(self.recorded_commands, 1):
            print(f"[{i}] {record.get('type', '未知')}: {record.get('command', '未知命令')}")

    def save_commands_to_file(self) -> None:
        """保存命令到文件"""
        if not self.recorded_commands:
            print("❌ 没有可保存的命令")
            return
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 触摸命令记录 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # 构建包含间隔时间的命令序列
                command_sequence: list[str] = []
                for i, record in enumerate(self.recorded_commands):
                    # 如果不是第一个命令且有间隔时间，插入间隔
                    interval_before = record.get('interval_before')
                    if i > 0 and interval_before is not None and isinstance(interval_before, (int, float)):
                        # 设置合理的间隔范围，避免异常长间隔
                        interval = int(interval_before)
                        if interval > 10000:  # 超过10秒的间隔认为是异常，使用默认间隔
                            interval = int(DEFAULT_INTERVAL * 1000)
                        command_sequence.append(f"{interval}ms")
                    
                    command = record.get('command')
                    if isinstance(command, str):
                        command_sequence.append(command)
                
                f.write(" ".join(command_sequence) + "\n\n")
                
                # 写入详细注释
                for i, record in enumerate(self.recorded_commands, 1):
                    interval_info = ""
                    if 'interval_before' in record and record['interval_before'] is not None:
                        interval_info = f" (间隔:{record['interval_before']}ms)"
                    f.write(f"# [{i}] {record.get('type', '未知')}: {record.get('command', '未知命令')}{interval_info}\n")
                    
            print(f"命令已保存到: {self.output_file}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")

    def clear_records(self) -> None:
        """清空记录"""
        if not self.recorded_commands:
            print("❌ 没有可清空的记录")
            return
        if input(f"确定要清空 {len(self.recorded_commands)} 条记录吗？(y/n): ").lower() == 'y':
            self.recorded_commands.clear()
            print("记录已清空")

    def test_generated_commands(self) -> None:
        """测试生成的命令"""
        if not self.recorded_commands:
            print("❌ 没有可测试的命令")
            return
        if input(f"确定要测试 {len(self.recorded_commands)} 条命令吗？(y/n): ").lower() != 'y':
            return
            
        print("开始执行命令序列...")
        for i, record in enumerate(self.recorded_commands, 1):
            # 如果不是第一个命令，先等待间隔时间
            if i > 1:  # 第一个命令前不需要等待
                prev_record = self.recorded_commands[i-2]  # 获取前一个命令记录
                
                # 使用实际记录的间隔时间
                if 'interval_before' in record and record['interval_before'] is not None:
                    interval_before = record['interval_before']
                    if isinstance(interval_before, (int, float)):
                        interval_sec = interval_before / 1000.0  # 转换为秒
                    else:
                        interval_sec = DEFAULT_INTERVAL
                    # 设置合理的间隔范围
                    if interval_sec > 10:  # 超过10秒使用默认间隔
                        interval_sec = DEFAULT_INTERVAL
                        print(f"  ⚠️ 间隔时间过长({record['interval_before']}ms)，使用默认间隔")
                    elif interval_sec < 0.1:  # 小于100ms使用最小间隔
                        interval_sec = 0.1
                        print(f"  ⚠️ 间隔时间过短({record['interval_before']}ms)，使用100ms")
                    
                    print(f"  ⏳ 等待间隔: {int(interval_sec * 1000)}ms")
                    time.sleep(interval_sec)
                else:
                    # 对于手动记录的命令或没有间隔信息的命令，使用默认间隔
                    print(f"  ⏳ 使用默认间隔: {int(DEFAULT_INTERVAL * 1000)}ms")
                    time.sleep(DEFAULT_INTERVAL)
            
            command_str = record.get('command', '')
            print(f"[{i}/{len(self.recorded_commands)}] 执行: {command_str}")
            success = False
            if record.get('type') == '点击' and isinstance(command_str, str):
                x, y = map(int, command_str.split(','))
                success = self.adb_executor.tap_screen(x, y)
            elif isinstance(command_str, str) and command_str.startswith('滑动'):
                params = command_str[6:].split(',')
                x1, y1, x2, y2, duration = map(int, params)
                success = self.adb_executor.swipe_screen(x1, y1, x2, y2, duration)
            
            if not success:
                print("  ❌ 执行失败，测试中止")
                break
                
        print("命令测试完成")

class ActionPlanItem(TypedDict, total=False):
    type: str
    params: tuple[int, ...]
    display: str
    delay_after: float

class RecordedCommand(TypedDict, total=False):
    type: str
    command: str
    interval_before: float | None
    timestamp: str
    start_pos: tuple[int, int]
    end_pos: tuple[int, int]
    duration: int
    distance: int

def execute_unified_commands_with_components(adb_executor: ADBExecutor) -> None:
    """使用组件化架构的统一命令执行功能"""
    device_state = adb_executor.device_state
    screen_width = device_state.screen_width
    screen_height = device_state.screen_height
    
    if screen_width and screen_height:
        print(f"检测到屏幕分辨率: {screen_width}x{screen_height}")
    else:
        print("⚠️ 无法获取屏幕分辨率，滑动功能可能受影响")
        
    while True:
        print("\n=== 统一命令执行 ===")
        print("  移动: W3 A2 S1 D4 | 点击: 540,960 | 滑动: SWIPE:800,500,800,300,500")
        print("  间隔: 500ms | 混合: W3 500ms 540,960 | 输入 'q' 返回")
        command_input = input("\n请输入命令序列: ").strip()
        if command_input.lower() == 'q':
            break
        if not command_input:
            print("❌ 输入为空，请重新输入")
            continue
            
        commands = command_input.split()
        action_plan = []
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd: continue
            if cmd.lower().endswith('ms'):
                try:
                    delay_value = int(cmd[:-2])
                    if action_plan:
                        action_plan[-1]['delay_after'] = delay_value / 1000.0
                    else:
                        print(f"⚠️ 忽略开头的间隔时间参数: {cmd}")
                except ValueError:
                    print(f"❌ 间隔时间格式错误: {cmd}")
            elif cmd.upper().startswith('SWIPE:'):
                try:
                    params = cmd[6:].split(',')
                    x1, y1, x2, y2, duration = map(int, params)
                    action_plan.append({'type': 'swipe', 'params': (x1, y1, x2, y2, duration), 'display': f"滑动({x1},{y1})→({x2},{y2})", 'delay_after': DEFAULT_INTERVAL})
                except (ValueError, IndexError):
                    print(f"❌ 滑动命令参数错误: {cmd}")
            elif ',' in cmd:
                try:
                    x, y = map(int, cmd.split(','))
                    action_plan.append({'type': 'tap', 'params': (x, y), 'display': f"点击({x},{y})", 'delay_after': DEFAULT_INTERVAL})
                except (ValueError, IndexError):
                    print(f"❌ 点击命令坐标错误: {cmd}")
            else:
                try:
                    direction = cmd[0].upper()
                    count = int(cmd[1:])
                    if direction not in KEYMAP or count <= 0:
                        print(f"❌ 无效移动命令: {cmd}")
                        continue
                    action_plan.append({'type': 'move', 'params': (KEYMAP[direction], count), 'display': f"移动{direction}×{count}", 'delay_after': DEFAULT_INTERVAL})
                except (ValueError, IndexError):
                    print(f"❌ 移动命令格式错误: {cmd}")
                    
        if not action_plan:
            print("❌ 没有有效的命令，请重新输入")
            continue
            
        plan_str = " → ".join([str(action.get('display', '')) for action in action_plan])
        print(f"执行计划: {plan_str}")
        logger.info(f"开始执行统一命令序列: {command_input}")
        
        for i, action in enumerate(action_plan, 1):
            print(f"执行: {action.get('display','')}", end=" ")
            success = False
            if action['type'] == 'move':
                success = adb_executor.press_key(*action['params'], delay=KEY_INTERVAL)
            elif action['type'] == 'tap':
                success = adb_executor.tap_screen(*action['params'])
            elif action['type'] == 'swipe':
                success = adb_executor.swipe_screen(*action['params'])
            if success:
                print("[成功]")
            else:
                print("❌ 失败")
                break
            if i < len(action_plan):
                time.sleep(float(action.get('delay_after', DEFAULT_INTERVAL)))
        print("命令序列执行完成！\n")


if __name__ == "__main__":
    logger.info("=== ADB游戏自动化调试器启动 v2.4 (OOP架构) ===")
    print("初始化系统组件...")
    
    # 使用新的组件系统初始化
    system = SystemComponents()
    if not system.initialize_system():
        print("❌ 系统初始化失败！请检查：")
        print("1. 手机是否已连接并开启USB调试")
        print("2. ADB是否已安装并添加到PATH")
        print("3. 是否已授权此电脑进行USB调试")
        input("按回车键退出...")
        exit(1)
    
    print("系统初始化成功")
    device_state = system.get_device_state()
    adb_executor = system.get_adb_executor()
    touch_recorder = system.get_touch_recorder()
    
    # 显示设备信息
    print("屏幕分辨率:", f"{device_state.screen_width}x{device_state.screen_height}")
    orientation_names = {0: '竖屏', 1: '横屏', 2: '倒竖屏', 3: '倒横屏'}
    orientation_key = device_state.screen_orientation if isinstance(device_state.screen_orientation, int) else -1
    orientation_name = orientation_names.get(orientation_key, f'未知({orientation_key})')
    print("屏幕方向:", orientation_name)

    while True:
        print("\n" + "="*55 + "\n        ADB游戏自动化调试器 v2.4\n" + "="*55)
        print("1. 移动测试 (W/A/S/D)")
        print("2. 统一命令执行")
        print("3. 触摸参数记录器")
        print("4. 查看设备状态")
        print("Q. 退出")
        choice = input("\n请选择操作: ").strip().upper()

        if choice == 'Q':
            logger.info("用户选择退出")
            break
        elif choice == '1':
            print("\n=== 移动测试 (ADBExecutor) ===")
            key_choice = input("请输入要按的键 (W/A/S/D): ").strip().upper()
            if key_choice not in "WASD":
                print("❌ 无效的键位")
                continue
            try:
                press_count = int(input(f"按 '{key_choice}' 键多少次? "))
                delay = float(input(f"按键间隔时间(秒，默认{KEY_INTERVAL}): ") or str(KEY_INTERVAL))
                success = adb_executor.press_key(KEYMAP[key_choice], press_count, delay)
                if success:
                    print("移动测试完成")
                else:
                    print("❌ 移动测试失败")
            except ValueError:
                print("❌ 请输入有效的数字")
        elif choice == '2':
            execute_unified_commands_with_components(adb_executor)
        elif choice == '3':
            touch_recorder.start_recording_menu()
        elif choice == '4':
            print("\n=== 设备状态信息 ===")
            print(f"屏幕分辨率: {device_state.screen_width}x{device_state.screen_height}")
            orientation_key = device_state.screen_orientation if device_state.screen_orientation is not None else -1
            print(f"屏幕方向: {orientation_names.get(orientation_key, '未知')}")
            if isinstance(device_state.touch_device, dict) and isinstance(device_state.touch_device.get('device'), str):
                print(f"触摸设备: {device_state.touch_device['device']}")
                print(f"触摸坐标范围: X(0-{device_state.touch_device.get('max_x')}), Y(0-{device_state.touch_device.get('max_y')})")
            else:
                print("触摸设备: 未找到")
        else:
            print("❌ 无效选择，请重新输入")