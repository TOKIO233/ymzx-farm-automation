import time
import subprocess
import logging
import threading
import re
import json
from datetime import datetime

# 元梦之星农场自动化脚本 - PC端调试器
# 版本: v2.3
# 更新时间: 2025-08-06
# 更新内容: 最终修复了所有已知的语法和逻辑错误
# 负责人: AI Assistant (Augment Agent)

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('move_debugger.log'),
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

# 全局缓存，避免重复扫描
_cached_touch_device = None

def check_adb_connection():
    """检查ADB连接状态"""
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

def split_device_blocks(output):
    """
    将getevent -p -l的输出按设备分割成独立的块。
    
    参数:
    - output: getevent命令的完整输出字符串
    
    返回值:
    - List[str]: 每个元素是一个设备的完整信息块
    """
    # 用于存储所有设备信息块的列表
    blocks = []
    # 用于临时存储当前正在处理的设备信息块的行
    current_block = []
    
    # 按行分割输入的字符串并逐行处理
    for line in output.split('\n'):
        # 去除行首尾的空白字符
        line = line.strip()
        # 跳过空行
        if not line:
            continue
            
        # 检测新设备的开始标记
        # 'add device'开头且包含'/dev/input/event'的行表示一个新设备的开始
        if line.startswith('add device') and '/dev/input/event' in line:
            # 如果当前已经有收集的设备信息，则保存为一个完整的块
            if current_block:
                # 将当前块的所有行合并为一个字符串，并添加到blocks列表中
                blocks.append('\n'.join(current_block))
            # 开始新的设备块，将当前行作为新块的第一行
            current_block = [line]
        elif current_block:  # 如果当前行属于某个设备（即current_block不为空）
            # 将当前行添加到当前正在处理的设备块中
            current_block.append(line)
    
    # 处理最后一个设备块（循环结束后可能还有未保存的设备信息）
    if current_block:
        blocks.append('\n'.join(current_block))
    
    # 返回所有设备信息块的列表
    return blocks


def parse_device_block(device_block):
    """
    解析单个设备块，提取设备路径和坐标信息。
    
    参数:
    - device_block: 单个设备的信息块字符串
    
    返回值:
    - dict: {'device': str, 'max_x': int, 'max_y': int} 或 None
    """
    # 提取设备路径
    device_match = re.search(r'(/dev/input/event\d+)', device_block)
    if not device_match:
        return None
    
    device_path = device_match.group(1)
    
    # 提取X轴和Y轴最大值
    x_match = re.search(r'ABS_MT_POSITION_X.*?max\s+(\d+)', device_block)
    y_match = re.search(r'ABS_MT_POSITION_Y.*?max\s+(\d+)', device_block)
    
    if x_match and y_match:
        max_x = int(x_match.group(1))
        max_y = int(y_match.group(1))
        logger.debug(f"设备 {device_path}: 解析出触摸坐标范围 X=0-{max_x}, Y=0-{max_y}")
        return {
            'device': device_path,
            'max_x': max_x,
            'max_y': max_y
        }
    else:
        logger.debug(f"设备 {device_path}: 非触摸设备，跳过")
    
    return None

def find_touch_device(force_rescan=False):
    """
    查找可用的触摸设备并获取坐标范围。
    优化版本：使用基于设备块的解析方法，避免多层嵌套循环。

    参数:
    - force_rescan: 如果为True，则强制重新扫描设备，忽略缓存。

    返回值:
    - 成功: {'device': '/dev/input/eventX', 'max_x': int, 'max_y': int}
    - 失败: None
    """
    global _cached_touch_device
    if _cached_touch_device and not force_rescan:
        return _cached_touch_device

    logger.info("开始查找触摸设备 (使用优化的块解析方法)...")
    
    if not check_adb_connection():
        logger.error("ADB连接失败，无法查找触摸设备")
        return None
    
    try:
        command = "adb shell getevent -p -l"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            logger.error(f"执行 getevent -p -l 失败: {result.stderr}")
            return None
        
        # 使用新的优化解析方法
        device_blocks = split_device_blocks(result.stdout)
        logger.info(f"发现 {len(device_blocks)} 个输入设备")
        
        # 解析每个设备块查找触摸设备
        for device_block in device_blocks:
            device_info = parse_device_block(device_block)
            if device_info:  # 找到有效的触摸设备
                logger.info(f"找到符合条件的触摸设备: {device_info['device']}")
                logger.info(f"坐标范围 - X: 0-{device_info['max_x']}, Y: 0-{device_info['max_y']}")
                _cached_touch_device = device_info
                return _cached_touch_device

        logger.error("未找到任何具有ABS_MT_POSITION_X和ABS_MT_POSITION_Y的触摸设备")
        return None
        
    except subprocess.TimeoutExpired:
        logger.error("getevent命令执行超时")
        return None
    except Exception as e:
        logger.error(f"查找触摸设备时出错: {e}")
        return None

def execute_adb_command(command):
    """执行ADB命令并返回结果"""
    logger.info(f"执行ADB命令: {command}")
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"命令执行成功: {result.stdout.strip()}")
            return True, result.stdout.strip()
        else:
            logger.error(f"命令执行失败 (返回码: {result.returncode}): {result.stderr.strip()}")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时: {command}")
        return False, "命令超时"
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        return False, str(e)

def press_key_optimized(keycode, times, delay=KEY_INTERVAL):
    """优化的按键函数，专门使用longpress方法"""
    key_name = next((k for k, v in KEYMAP.items() if v == keycode), f"keycode_{keycode}")
    logger.info(f"开始执行按键操作: {key_name} (keycode: {keycode})")
    logger.info(f"参数: 次数={times}, 间隔={delay}秒 (使用longpress方法)")

    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行按键操作")
        return False

    success_count = 0
    for i in range(times):
        logger.info(f"第 {i+1}/{times} 次长按...")
        command = f"adb shell input keyevent --longpress {keycode}"
        success, output = execute_adb_command(command)

        if success:
            success_count += 1
            logger.info(f"第 {i+1} 次长按成功")
        else:
            logger.error(f"第 {i+1} 次长按失败: {output}")

        if i < times - 1:
            logger.info(f"等待 {delay} 秒...")
            time.sleep(delay)

    logger.info(f"按键操作完成: 成功 {success_count}/{times} 次")
    return success_count == times

def tap_screen(x, y):
    """模拟屏幕点击，带详细日志"""
    logger.info(f"开始执行屏幕点击: 坐标 ({x}, {y})")
    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行点击操作")
        return False
    command = f"adb shell input tap {x} {y}"
    success, output = execute_adb_command(command)
    if success:
        logger.info(f"屏幕点击成功: ({x}, {y})")
    else:
        logger.error(f"屏幕点击失败: {output}")
    return success

def swipe_screen(x1, y1, x2, y2, duration=500):
    """执行屏幕滑动操作"""
    logger.info(f"执行屏幕滑动: ({x1},{y1}) → ({x2},{y2}), 持续时间: {duration}ms")
    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行滑动操作")
        return False
    command = f"adb shell input swipe {x1} {y1} {x2} {y2} {duration}"
    success, output = execute_adb_command(command)
    if success:
        logger.info(f"屏幕滑动成功: ({x1},{y1}) → ({x2},{y2})")
    else:
        logger.error(f"屏幕滑动失败: {output}")
    return success

def get_screen_resolution(show_info=False):
    """获取屏幕分辨率，返回(width, height)"""
    logger.info("获取屏幕分辨率...")
    command = "adb shell wm size"
    success, output = execute_adb_command(command)
    if success:
        try:
            size_part = output.split(':')[-1].strip()
            width, height = map(int, size_part.split('x'))
            logger.info(f"屏幕分辨率: {width}x{height}")
            if show_info:
                print(f"屏幕尺寸: {output}")
                density_command = "adb shell wm density"
                density_success, density_output = execute_adb_command(density_command)
                if density_success:
                    print(f"屏幕密度: {density_output}")
                else:
                    print("❌ 无法获取屏幕密度")
            return width, height
        except Exception as e:
            logger.error(f"解析屏幕分辨率失败: {e}")
            if show_info:
                print("❌ 解析屏幕分辨率失败")
            return None, None
    else:
        logger.error("无法获取屏幕分辨率")
        if show_info:
            print("❌ 无法获取屏幕尺寸")
        return None, None

def get_screen_orientation():
    """
    获取屏幕方向 (更稳健的版本)
    返回值: 0:竖屏, 1:横屏, 2:反向竖屏, 3:反向横屏, 1:失败默认值
    """
    logger.info("获取屏幕方向...")
    try:
        command = "adb shell dumpsys window displays"
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.warning(f"无法获取'dumpsys window displays'信息: {result.stderr}")
            return 1
        output = result.stdout
        rotation_match = re.search(r'mDisplayRotation=ROTATION_(\d+)', output)
        if rotation_match:
            degrees = int(rotation_match.group(1))
            rotation = degrees // 90
        else:
            logger.warning("无法从dumpsys输出中解析屏幕方向，默认返回横屏")
            return 1
        orientation_names = {0: '竖屏', 1: '横屏', 2: '倒竖屏', 3: '倒横屏'}
        orientation_name = orientation_names.get(rotation, f'未知({rotation})')
        logger.info(f"检测到屏幕方向: {rotation} ({orientation_name})")
        return rotation
    except Exception as e:
        logger.error(f"获取屏幕方向时出错: {e}")
        return 1

def convert_touch_coordinates(raw_x, raw_y, max_x, max_y, screen_width, screen_height):
    """支持屏幕旋转的坐标转换函数"""
    x_norm = raw_x / max_x
    y_norm = raw_y / max_y
    orientation = get_screen_orientation()
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

def execute_unified_commands():
    """执行统一的移动、点击、滑动命令"""
    screen_width, screen_height = get_screen_resolution()
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
                    direction = cmd.upper()
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
        plan_str = " → ".join([action['display'] for action in action_plan])
        print(f"执行计划: {plan_str}")
        logger.info(f"开始执行统一命令序列: {command_input}")
        for i, action in enumerate(action_plan, 1):
            print(f"执行: {action['display']}", end=" ")
            success = False
            if action['type'] == 'move':
                success = press_key_optimized(*action['params'], delay=KEY_INTERVAL)
            elif action['type'] == 'tap':
                success = tap_screen(*action['params'])
            elif action['type'] == 'swipe':
                success = swipe_screen(*action['params'])
            if success:
                print("✓")
            else:
                print("❌ 失败")
                break
            if i < len(action_plan):
                time.sleep(action.get('delay_after', DEFAULT_INTERVAL))
        print("✓ 命令序列执行完成！\n")

class TouchEventRecorder:
    """触摸事件记录器类 - v2.3"""
    def __init__(self):
        self.recording = False
        self.recorded_commands = []
        self.output_file = "touch_commands.txt"
        self.working_touch_device = None
        self.process = None

    def start_recording_menu(self):
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
            if choice in menu: menu[choice]()
            else: print("❌ 无效选择，请重新输入")

    def find_and_set_touch_device(self):
        """查找并设置工作触摸设备"""
        print("\n=== 查找触摸设备 ===")
        touch_device_info = find_touch_device(force_rescan=True)
        if touch_device_info:
            self.working_touch_device = touch_device_info
            print(f"✅ 已设置工作触摸设备: {self.working_touch_device['device']}")
            print(f"📏 坐标范围 - X: 0-{self.working_touch_device['max_x']}, Y: 0-{self.working_touch_device['max_y']}")
            return self.working_touch_device['device']
        else:
            print("❌ 未找到可用的触摸设备")
            return None

    def start_touch_recording(self):
        """开始记录触摸事件"""
        print("\n=== 触摸事件记录 ===")
        if not self.working_touch_device:
            print("⚠️ 未找到工作触摸设备，正在查找...")
            if not self.find_and_set_touch_device():
                print("❌ 无法找到可用的触摸设备，请使用手动记录功能")
                return
        device_path = self.working_touch_device['device']
        print(f"使用已找到的触摸设备: {device_path}")
        print("请在手机屏幕上进行滑动或点击操作 (按 Ctrl+C 停止记录)")
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
                self.process.terminate()
                self.process = None

    def listen_touch_events(self, device_path):
        """监听触摸事件"""
        command = f"adb shell getevent {device_path}"
        self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        current_touch = {'is_touching': False}
        while self.recording:
            line = self.process.stdout.readline()
            if not line: break
            if line.strip():
                event_data = self.parse_event_line(line.strip())
                if event_data:
                    self.process_touch_event(event_data, current_touch)
        # Cleanup is handled in start_touch_recording's finally block

    def parse_event_line(self, line):
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

    def process_touch_event(self, event, current_touch):
        """处理单个触摸事件"""
        if event['type'] == 3:  # EV_ABS
            if event['code'] == 0x35:  # ABS_MT_POSITION_X
                if 'start_x' not in current_touch and current_touch['is_touching']:
                    current_touch['start_x'] = event['value']
                current_touch['end_x'] = event['value']
            elif event['code'] == 0x36:  # ABS_MT_POSITION_Y
                if 'start_y' not in current_touch and current_touch['is_touching']:
                    current_touch['start_y'] = event['value']
                current_touch['end_y'] = event['value']
        elif event['type'] == 1 and event['code'] == 0x14a:  # EV_KEY, BTN_TOUCH
            if event['value'] == 1:
                current_touch.update({'is_touching': True, 'start_time': time.time()})
                print("👆 检测到触摸开始")
            elif event['value'] == 0:
                current_touch['is_touching'] = False
                current_touch['end_time'] = time.time()
                print("👆 检测到触摸结束")
                self.generate_touch_command(current_touch)
                current_touch.clear()
                current_touch['is_touching'] = False

    def generate_touch_command(self, touch_data):
        """根据触摸数据生成命令"""
        required_keys = ['start_x', 'start_y', 'end_x', 'end_y', 'start_time', 'end_time']
        if not all(key in touch_data for key in required_keys): return
        
        screen_width, screen_height = get_screen_resolution()
        if not screen_width or not self.working_touch_device:
            print("❌ 无法获取屏幕或触摸设备信息，无法生成命令")
            return

        start_x, start_y = convert_touch_coordinates(touch_data['start_x'], touch_data['start_y'], self.working_touch_device['max_x'], self.working_touch_device['max_y'], screen_width, screen_height)
        end_x, end_y = convert_touch_coordinates(touch_data['end_x'], touch_data['end_y'], self.working_touch_device['max_x'], self.working_touch_device['max_y'], screen_width, screen_height)
        duration = int((touch_data['end_time'] - touch_data['start_time']) * 1000)
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

        if distance < 20:
            command = f"{start_x},{start_y}"
            command_type = "点击"
        else:
            command = f"SWIPE:{start_x},{start_y},{end_x},{end_y},{duration}"
            command_type = "滑动"
        print(f"✅ 生成{command_type}命令: {command}")
        self.recorded_commands.append({'type': command_type, 'command': command, 'start_pos': (start_x, start_y), 'end_pos': (end_x, end_y), 'duration': duration, 'distance': distance, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def manual_coordinate_recording(self):
        """手动记录坐标的备选方案"""
        print("\n=== 手动坐标记录 ===")
        while True:
            choice = input("选择操作: 1.点击 2.滑动 3.完成\n> ").strip()
            if choice == '1':
                try:
                    x, y = map(int, input("输入X,Y坐标 (e.g., 540,960): ").split(','))
                    self.recorded_commands.append({'type': '点击', 'command': f"{x},{y}", 'start_pos': (x, y), 'end_pos': (x, y), 'duration': 0, 'distance': 0, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    print(f"✓ 已记录点击: {x},{y}")
                except ValueError: print("❌ 格式错误")
            elif choice == '2':
                try:
                    x1, y1 = map(int, input("输入起始X,Y坐标: ").split(','))
                    x2, y2 = map(int, input("输入结束X,Y坐标: ").split(','))
                    duration = int(input("输入持续时间(ms): ") or "500")
                    command = f"SWIPE:{x1},{y1},{x2},{y2},{duration}"
                    self.recorded_commands.append({'type': '滑动', 'command': command, 'start_pos': (x1, y1), 'end_pos': (x2, y2), 'duration': duration, 'distance': 0, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    print(f"✓ 已记录滑动: {command}")
                except ValueError: print("❌ 格式错误")
            elif choice == '3': break
            else: print("❌ 无效选择")

    def show_raw_touch_events(self):
        """显示原始触摸事件代码 (调试用)"""
        print("\n=== 显示原始触摸事件代码 (调试用) ===")
        if not self.working_touch_device:
            if not self.find_and_set_touch_device(): return
        device_path = self.working_touch_device['device']
        screen_width, screen_height = get_screen_resolution()
        if not screen_width: return
        print("=" * 80)
        print(f"📱 监控设备: {device_path} | 传感器: {self.working_touch_device['max_x']}x{self.working_touch_device['max_y']} | 屏幕: {screen_width}x{screen_height}")
        print("=" * 80 + "\n⏹️  按 Ctrl+C 停止监听\n")
        try:
            command = f"adb shell getevent {device_path}"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
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
                            sx, sy = convert_touch_coordinates(current_x, current_y, self.working_touch_device['max_x'], self.working_touch_device['max_y'], screen_width, screen_height)
                            print(f"原始: ({current_x:5d}, {current_y:5d}) -> 屏幕: ({sx:4d}, {sy:4d})")
        except KeyboardInterrupt:
            print("\n✅ 监听完成")
        finally:
            if process: process.terminate()

    def show_recorded_commands(self):
        """显示已记录的命令"""
        if not self.recorded_commands:
            print("❌ 暂无记录的命令")
            return
        print(f"\n=== 已记录的命令 (共 {len(self.recorded_commands)} 条) ===")
        for i, record in enumerate(self.recorded_commands, 1):
            print(f"[{i}] {record['type']}: {record['command']}")

    def save_commands_to_file(self):
        """保存命令到文件"""
        if not self.recorded_commands:
            print("❌ 没有可保存的命令")
            return
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 触摸命令记录 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                commands_only = [record['command'] for record in self.recorded_commands]
                f.write(" ".join(commands_only) + "\n\n")
                for i, record in enumerate(self.recorded_commands, 1):
                    f.write(f"# [{i}] {record['type']}: {record['command']}\n")
            json_file = self.output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.recorded_commands, f, ensure_ascii=False, indent=2)
            print(f"✓ 命令已保存到: {self.output_file} 和 {json_file}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")

    def clear_records(self):
        """清空记录"""
        if not self.recorded_commands:
            print("❌ 没有可清空的记录")
            return
        if input(f"确定要清空 {len(self.recorded_commands)} 条记录吗？(y/n): ").lower() == 'y':
            self.recorded_commands.clear()
            print("✓ 记录已清空")

    def test_generated_commands(self):
        """测试生成的命令"""
        if not self.recorded_commands:
            print("❌ 没有可测试的命令")
            return
        if input(f"确定要测试 {len(self.recorded_commands)} 条命令吗？(y/n): ").lower() != 'y':
            return
        for i, record in enumerate(self.recorded_commands, 1):
            print(f"[{i}/{len(self.recorded_commands)}] 执行: {record['command']}")
            success = False
            if record['type'] == '点击':
                x, y = map(int, record['command'].split(','))
                success = tap_screen(x, y)
            else:
                params = record['command'][6:].split(',')
                x1, y1, x2, y2, duration = map(int, params)
                success = swipe_screen(x1, y1, x2, y2, duration)
            if not success:
                print("  ❌ 执行失败，测试中止")
                break
            if i < len(self.recorded_commands):
                time.sleep(DEFAULT_INTERVAL)
        print("✓ 命令测试完成")

if __name__ == "__main__":
    logger.info("=== ADB游戏自动化调试器启动 ===")
    print("正在检查ADB连接...")
    if not check_adb_connection():
        print("❌ ADB连接失败！请检查：")
        print("1. 手机是否已连接并开启USB调试")
        print("2. ADB是否已安装并添加到PATH")
        print("3. 是否已授权此电脑进行USB调试")
        input("按回车键退出...")
        exit(1)
    print("✓ ADB连接正常")

    print("\n正在获取设备屏幕信息...")
    screen_width, screen_height = get_screen_resolution()
    if screen_width and screen_height:
        print(f"✓ 屏幕分辨率: {screen_width}x{screen_height}")
    else:
        print("⚠️ 无法获取屏幕分辨率")
    
    orientation = get_screen_orientation()
    orientation_names = {0: '竖屏', 1: '横屏', 2: '倒竖屏', 3: '倒横屏'}
    orientation_name = orientation_names.get(orientation, f'未知({orientation})')
    print(f"✓ 屏幕方向: {orientation_name}")

    while True:
        print("\n" + "="*55 + "\n        ADB游戏自动化调试器 v2.3\n" + "="*55)
        print("1. 移动测试 (W/A/S/D)")
        print("2. 统一命令执行")
        print("3. 触摸参数记录器")
        print("4. 查看ADB连接状态")
        print("5. 查看屏幕信息")
        print("Q. 退出")
        choice = input("\n请选择操作: ").strip().upper()

        if choice == 'Q':
            logger.info("用户选择退出")
            break
        elif choice == '1':
            print("\n=== 移动测试 (Longpress方法) ===")
            key_choice = input("请输入要按的键 (W/A/S/D): ").strip().upper()
            if key_choice not in "WASD":
                print("❌ 无效的键位")
                continue
            try:
                press_count = int(input(f"按 '{key_choice}' 键多少次? "))
                delay = float(input(f"按键间隔时间(秒，默认{KEY_INTERVAL}): ") or str(KEY_INTERVAL))
                press_key_optimized(KEYMAP[key_choice], press_count, delay)
            except ValueError:
                print("❌ 请输入有效的数字")
        elif choice == '2':
            execute_unified_commands()
        elif choice == '3':
            touch_recorder = TouchEventRecorder()
            touch_recorder.start_recording_menu()
        elif choice == '4':
            print("\n=== ADB连接状态 ===")
            check_adb_connection()
        elif choice == '5':
            print("\n=== 屏幕信息 ===")
            get_screen_resolution(show_info=True)
            orientation = get_screen_orientation()
            orientation_name = orientation_names.get(orientation, f'未知({orientation})')
            print(f"屏幕方向: {orientation_name}")
        else:
            print("❌ 无效选择，请重新输入")