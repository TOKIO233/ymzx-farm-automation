import time
import subprocess
import logging
import threading
import re
import json
from datetime import datetime

# 元梦之星农场自动化脚本 - PC端调试器
# 版本: v2.0
# 更新时间: 2025-08-03
# 更新内容: 重构功能结构，优化触摸设备检测，简化操作流程
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

    # 检查ADB连接
    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行按键操作")
        return False

    success_count = 0
    for i in range(times):
        logger.info(f"第 {i+1}/{times} 次长按...")

        # 使用longpress方法
        command = f"adb shell input keyevent --longpress {keycode}"
        success, output = execute_adb_command(command)

        if success:
            success_count += 1
            logger.info(f"第 {i+1} 次长按成功")
        else:
            logger.error(f"第 {i+1} 次长按失败: {output}")

        # 按键间延迟
        if i < times - 1:  # 最后一次不需要延迟
            logger.info(f"等待 {delay} 秒...")
            time.sleep(delay)

    logger.info(f"按键操作完成: 成功 {success_count}/{times} 次")
    return success_count == times

def tap_screen(x, y):
    """模拟屏幕点击，带详细日志"""
    logger.info(f"开始执行屏幕点击: 坐标 ({x}, {y})")

    # 检查ADB连接
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

    # 检查ADB连接
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

def get_screen_info():
    """获取屏幕信息，用于调试"""
    logger.info("获取屏幕信息...")
    command = "adb shell wm size"
    success, output = execute_adb_command(command)
    if success:
        logger.info(f"屏幕尺寸: {output}")
        print(f"屏幕尺寸: {output}")
    else:
        logger.error("无法获取屏幕尺寸")
        print("❌ 无法获取屏幕尺寸")

    command = "adb shell wm density"
    success, output = execute_adb_command(command)
    if success:
        logger.info(f"屏幕密度: {output}")
        print(f"屏幕密度: {output}")
    else:
        logger.error("无法获取屏幕密度")
        print("❌ 无法获取屏幕密度")

def get_screen_resolution():
    """获取屏幕分辨率，返回(width, height)"""
    logger.info("获取屏幕分辨率...")
    command = "adb shell wm size"
    success, output = execute_adb_command(command)
    if success:
        try:
            # 输出格式通常是: Physical size: 1080x2340
            size_part = output.split(':')[-1].strip()
            width, height = map(int, size_part.split('x'))
            logger.info(f"屏幕分辨率: {width}x{height}")
            return width, height
        except Exception as e:
            logger.error(f"解析屏幕分辨率失败: {e}")
            return None, None
    else:
        logger.error("无法获取屏幕分辨率")
        return None, None

def execute_unified_commands():
    """执行统一的移动、点击、滑动命令"""
    # 获取屏幕分辨率用于滑动操作
    screen_width, screen_height = get_screen_resolution()
    if screen_width and screen_height:
        print(f"检测到屏幕分辨率: {screen_width}x{screen_height}")
    else:
        print("⚠️ 无法获取屏幕分辨率，滑动功能可能受影响")

    while True:
        print("\n=== 统一命令执行 ===")
        print("支持的命令格式:")
        print("  移动: W3 A2 S1 D4 (方向键+次数)")
        print("  点击: 540,960 (x,y坐标)")
        print("  滑动: SWIPE:800,500,800,300,500 (起点x,y,终点x,y,持续时间ms)")
        print("  间隔: 500ms 1000ms 2000ms (步骤间等待时间)")
        print("  混合: W3 500ms 540,960 A2 1000ms SWIPE:800,500,800,300,500")
        print("输入 'q' 返回主菜单")

        command_input = input("\n请输入命令序列: ").strip()
        if command_input.lower() == 'q':
            break

        if not command_input:
            print("❌ 输入为空，请重新输入")
            continue

        # 解析命令序列
        commands = command_input.split()
        action_plan = []

        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue

            # 检查是否是间隔时间参数 (以ms结尾)
            if cmd.lower().endswith('ms'):
                try:
                    delay_value = int(cmd[:-2])  # 去掉'ms'后缀
                    if delay_value < 0:
                        print(f"❌ 间隔时间不能为负数: {cmd}")
                        continue

                    # 将间隔时间应用到前一个命令
                    if action_plan:
                        action_plan[-1]['delay_after'] = delay_value / 1000.0  # 转换为秒
                        logger.info(f"为前一个命令设置间隔时间: {delay_value}ms")
                    else:
                        print(f"⚠️ 忽略开头的间隔时间参数: {cmd}")
                    continue
                except ValueError:
                    print(f"❌ 间隔时间格式错误: {cmd}")
                    continue

            # 检查是否是滑动命令
            elif cmd.upper().startswith('SWIPE:'):
                swipe_params = cmd[6:]  # 去掉 'SWIPE:' 前缀
                try:
                    params = swipe_params.split(',')
                    if len(params) != 5:
                        print(f"❌ 滑动命令格式错误: {cmd} (需要5个参数)")
                        continue

                    x1, y1, x2, y2, duration = map(int, params)
                    action_plan.append({
                        'type': 'swipe',
                        'params': (x1, y1, x2, y2, duration),
                        'display': f"滑动({x1},{y1})→({x2},{y2}),{duration}ms",
                        'delay_after': DEFAULT_INTERVAL  # 默认间隔
                    })
                except ValueError:
                    print(f"❌ 滑动命令参数错误: {cmd}")
                    continue

            # 检查是否是点击命令 (包含逗号)
            elif ',' in cmd:
                try:
                    coords = cmd.split(',')
                    if len(coords) != 2:
                        print(f"❌ 点击命令格式错误: {cmd}")
                        continue

                    x, y = int(coords[0]), int(coords[1])
                    if x < 0 or y < 0:
                        print(f"❌ 坐标不能为负数: {cmd}")
                        continue

                    action_plan.append({
                        'type': 'tap',
                        'params': (x, y),
                        'display': f"点击({x},{y})",
                        'delay_after': DEFAULT_INTERVAL  # 默认间隔
                    })
                except ValueError:
                    print(f"❌ 点击命令坐标错误: {cmd}")
                    continue

            # 检查是否是移动命令
            else:
                cmd_upper = cmd.upper()
                if len(cmd_upper) < 2:
                    print(f"❌ 无效命令格式: {cmd}")
                    continue

                direction = cmd_upper[0]
                try:
                    count = int(cmd_upper[1:])
                except ValueError:
                    print(f"❌ 移动命令数字错误: {cmd}")
                    continue

                if direction not in KEYMAP:
                    print(f"❌ 无效方向: {direction}")
                    continue

                if count <= 0:
                    print(f"❌ 次数必须大于0: {count}")
                    continue

                action_plan.append({
                    'type': 'move',
                    'params': (KEYMAP[direction], count),
                    'display': f"移动{direction}×{count}",
                    'delay_after': DEFAULT_INTERVAL  # 默认间隔
                })

        if not action_plan:
            print("❌ 没有有效的命令，请重新输入")
            continue

        # 显示执行计划
        plan_str = " → ".join([action['display'] for action in action_plan])
        print(f"执行计划: {plan_str}")

        logger.info(f"开始执行统一命令序列: {command_input}")

        # 执行命令序列
        for i, action in enumerate(action_plan, 1):
            print(f"执行: {action['display']}", end=" ")

            if action['type'] == 'move':
                keycode, count = action['params']
                success = press_key_optimized(keycode, count, KEY_INTERVAL)
            elif action['type'] == 'tap':
                x, y = action['params']
                success = tap_screen(x, y)
            elif action['type'] == 'swipe':
                x1, y1, x2, y2, duration = action['params']
                success = swipe_screen(x1, y1, x2, y2, duration)
            else:
                success = False

            if success:
                print("✓")
            else:
                print("❌ 失败")
                break

            # 步骤间等待 (除了最后一步)
            if i < len(action_plan):
                delay_time = action.get('delay_after', DEFAULT_INTERVAL)
                if delay_time != DEFAULT_INTERVAL:  # 如果不是默认值，记录到日志
                    logger.info(f"使用自定义间隔时间: {delay_time * 1000:.0f}ms")
                time.sleep(delay_time)

        print("✓ 命令序列执行完成！\n")


class TouchEventRecorder:
    """
    触摸事件记录器类 - v2.0
    
    功能说明:
    - 自动查找触摸设备：智能检测并测试触摸设备直到找到正确的
    - 基础录制模式: 可靠的滑动和点击操作录制
    - 坐标转换: 触摸传感器坐标到屏幕坐标的精确映射
    - 命令生成: 自动生成标准SWIPE和TAP命令格式
    """

    def __init__(self):
        self.recording = False
        self.touch_events = []
        self.current_touch = None
        self.recorded_commands = []
        self.output_file = "touch_commands.txt"
        self.working_touch_device = None  # 找到的工作触摸设备

    def start_recording_menu(self):
        """触摸参数记录器主菜单"""
        while True:
            print("\n" + "="*50)
            print("        触摸参数记录器")
            print("="*50)
            print("1. 查找触摸设备")
            print("2. 显示原始触摸事件代码 (调试用)")
            print("3. 开始记录触摸事件")
            print("4. 手动记录坐标 (备选方案)")
            print("5. 查看已记录的命令")
            print("6. 保存命令到文件")
            print("7. 清空记录")
            print("8. 测试生成的命令")
            print("Q. 返回主菜单")

            choice = input("\n请选择操作: ").strip().upper()

            if choice == 'Q':
                break
            elif choice == '1':
                self.find_touch_device()
            elif choice == '2':
                self.show_raw_touch_events()
            elif choice == '3':
                self.start_touch_recording()
            elif choice == '4':
                self.manual_coordinate_recording()
            elif choice == '5':
                self.show_recorded_commands()
            elif choice == '6':
                self.save_commands_to_file()
            elif choice == '7':
                self.clear_records()
            elif choice == '8':
                self.test_generated_commands()
            else:
                print("❌ 无效选择，请重新输入")

    def find_touch_device(self):
        """查找可用的触摸设备"""
        print("\n=== 查找触摸设备 ===")
        print("正在查找可用的触摸设备...")

        # 检查ADB连接
        if not check_adb_connection():
            print("❌ ADB连接失败，无法查找设备")
            return None

        print("✓ ADB连接正常")

        # 直接扫描所有event设备
        print("\n1. 扫描输入设备...")
        available_devices = []
        
        try:
            # 扫描所有可能的event设备
            for i in range(15):  # 扫描event0-event14
                device = f"/dev/input/event{i}"
                test_cmd = f"adb shell ls {device}"
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=3)
                if test_result.returncode == 0:
                    # 尝试获取设备名称
                    name_cmd = f"adb shell cat /sys/class/input/event{i}/device/name 2>/dev/null || echo 'unknown'"
                    name_result = subprocess.run(name_cmd, shell=True, capture_output=True, text=True, timeout=3)
                    device_name = name_result.stdout.strip() if name_result.returncode == 0 else 'unknown'
                    available_devices.append((device, device_name))
                    
            if not available_devices:
                print("❌ 未发现任何输入设备")
                return None
                
            print(f"✓ 发现 {len(available_devices)} 个输入设备")
            
        except Exception as e:
            print(f"❌ 设备扫描失败: {e}")
            return None

        # 显示设备列表
        print("\n2. 设备列表:")
        for i, (device, name) in enumerate(available_devices, 1):
            print(f"   {i}. {device} - {name}")

        # 逐个测试设备
        print("\n3. 测试设备 (按优先级)...")
        tested_devices = []
        
        for device, name in available_devices:
            print(f"\n测试设备: {device} ({name})")
            print("请在手机屏幕上进行触摸操作...")
            
            try:
                # 测试5秒
                command = f"adb shell getevent {device}"
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, bufsize=1)

                start_time = time.time()
                events_found = []
                touch_events = []

                while time.time() - start_time < 5:
                    try:
                        line = process.stdout.readline()
                        if line and line.strip():
                            events_found.append(line.strip())
                            # 检查是否是触摸相关事件
                            if '0003' in line or '0001' in line:
                                touch_events.append(line.strip())
                            if len(events_found) <= 3:  # 只显示前3个事件
                                print(f"📱 检测到事件: {line.strip()}")
                    except:
                        break

                process.terminate()

                if touch_events:
                    print(f"✅ {device} ({name}) 可以读取触摸事件! (共检测到 {len(touch_events)} 个触摸事件)")
                    self.working_touch_device = device
                    print(f"🎯 找到工作触摸设备: {device} ({name})")
                    return device
                else:
                    print(f"❌ {device} ({name}) 未检测到触摸事件")
                    tested_devices.append((device, name, False))

            except Exception as e:
                print(f"❌ 测试 {device} 失败: {e}")
                tested_devices.append((device, name, False))

        print("\n⚠️ 所有设备测试都未检测到触摸事件")
        print("可能的原因:")
        print("1. 设备权限不足 (需要root权限)")
        print("2. 测试时间内没有进行触摸操作")
        print("3. Android安全策略阻止了事件读取")
        print("建议使用'手动记录坐标'功能作为替代方案")
        return None

    def start_touch_recording(self):
        """开始记录触摸事件"""
        print("\n=== 触摸事件记录 ===")
        
        # 检查是否已找到工作设备
        if not self.working_touch_device:
            print("⚠️ 未找到工作触摸设备，正在查找...")
            device = self.find_touch_device()
            if not device:
                print("❌ 无法找到可用的触摸设备，请使用手动记录功能")
                return
        else:
            device = self.working_touch_device
            print(f"使用已找到的触摸设备: {device}")

        # 获取屏幕分辨率用于坐标转换
        screen_width, screen_height = get_screen_resolution()
        if screen_width and screen_height:
            print(f"✓ 屏幕分辨率: {screen_width}x{screen_height}")
            print(f"✓ 坐标转换规则: 屏幕X=原始Y, 屏幕Y={screen_height}-原始X")
        else:
            print("⚠️ 无法获取屏幕分辨率，将使用默认转换")

        print("即将开始监听触摸事件...")
        print("请在手机屏幕上进行滑动或点击操作")
        print("按 Ctrl+C 停止记录")

        try:
            print(f"开始监听触摸事件...")
            print("提示: 滑动和点击操作都会被记录，程序会自动区分")

            # 启动getevent监听
            self.recording = True
            self.listen_touch_events(device)

        except KeyboardInterrupt:
            print("\n⏹️ 停止记录")
            self.recording = False
            self.process_recorded_events()
        except Exception as e:
            print(f"❌ 记录过程中出现错误: {e}")
            logger.error(f"触摸事件记录错误: {e}")

    def listen_touch_events(self, device_path):
        """监听触摸事件"""
        process = None
        try:
            command = f"adb shell getevent {device_path}"
            print(f"执行命令: {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)

            current_touch = {
                'start_time': None,
                'end_time': None,
                'start_x': None,
                'start_y': None,
                'end_x': None,
                'end_y': None,
                'is_touching': False
            }

            print("✓ 开始监听触摸事件 (按 Ctrl+C 停止)")
            print("📱 请在手机屏幕上进行触摸操作...")

            event_count = 0
            while self.recording:
                line = process.stdout.readline()
                if not line:
                    # 检查是否有错误输出
                    error_line = process.stderr.readline()
                    if error_line:
                        print(f"⚠️ 错误输出: {error_line.strip()}")
                    break

                # 显示原始事件数据（调试用）
                if line.strip():
                    event_count += 1
                    # 显示更多原始事件用于调试
                    if event_count <= 20:  # 显示前20个事件作为调试
                        print(f"🔍 原始事件: {line.strip()}")
                    elif event_count == 21:
                        print("🔍 (后续事件将在后台处理...)")

                    # 解析事件行
                    event_data = self.parse_event_line(line.strip())
                    if event_data:
                        self.process_touch_event(event_data, current_touch)

            print(f"📊 总共处理了 {event_count} 个事件")

        except Exception as e:
            logger.error(f"监听触摸事件失败: {e}")
            print(f"❌ 监听失败: {e}")
        finally:
            if process:
                process.terminate()

    def parse_event_line(self, line):
        """解析getevent输出行"""
        try:
            # 移除时间戳（如果存在）
            if line.startswith('['):
                bracket_end = line.find(']')
                if bracket_end != -1:
                    line = line[bracket_end + 1:].strip()

            parts = line.split()

            # 检查是否是标准的3部分格式 (type code value)
            if len(parts) == 3:
                event_type = int(parts[0], 16)
                event_code = int(parts[1], 16)
                event_value = int(parts[2], 16)
                device = "unknown"
            elif len(parts) >= 4:
                # 带设备路径的格式: /dev/input/eventX: type code value
                device = parts[0].rstrip(':')
                event_type = int(parts[1], 16)
                event_code = int(parts[2], 16)
                event_value = int(parts[3], 16)
            else:
                return None

            timestamp = time.time()

            return {
                'device': device,
                'type': event_type,
                'code': event_code,
                'value': event_value,
                'timestamp': timestamp,
                'raw_line': line
            }

        except (ValueError, IndexError) as e:
            print(f"⚠️ 解析失败: {line} - {e}")
            return None

    def process_touch_event(self, event, current_touch):
        """处理单个触摸事件"""
        # 显示原始触摸事件代码（调试用）
        if event['type'] in [1, 3]:  # 只显示关键事件
            event_type_names = {1: 'EV_KEY', 3: 'EV_ABS'}
            type_name = event_type_names.get(event['type'], f'TYPE_{event["type"]}')
            
            # 详细的事件代码解释
            abs_codes = {
                0x00: 'ABS_X', 0x01: 'ABS_Y',
                0x35: 'ABS_MT_POSITION_X', 0x36: 'ABS_MT_POSITION_Y',
                0x39: 'ABS_MT_TRACKING_ID', 0x3a: 'ABS_MT_PRESSURE'
            }
            key_codes = {
                0x14a: 'BTN_TOUCH', 0x110: 'BTN_LEFT', 0x111: 'BTN_RIGHT'
            }
            
            if event['type'] == 3:  # EV_ABS
                code_name = abs_codes.get(event['code'], f'ABS_0x{event["code"]:02x}')
                print(f"🔍 {type_name}: {code_name} = {event['value']} (原始值)")
            elif event['type'] == 1:  # EV_KEY
                code_name = key_codes.get(event['code'], f'KEY_0x{event["code"]:02x}')
                print(f"🔍 {type_name}: {code_name} = {event['value']}")
        # EV_ABS = 3, EV_KEY = 1
        if event['type'] == 3:  # EV_ABS (绝对坐标事件)
            # 多点触控坐标
            if event['code'] == 0x35:  # ABS_MT_POSITION_X (53)
                if current_touch['start_x'] is None and current_touch['is_touching']:
                    current_touch['start_x'] = event['value']
                    print(f"📍 记录起始X坐标: {event['value']} (原始触摸传感器值)")
                current_touch['end_x'] = event['value']

            elif event['code'] == 0x36:  # ABS_MT_POSITION_Y (54)
                if current_touch['start_y'] is None and current_touch['is_touching']:
                    current_touch['start_y'] = event['value']
                    print(f"📍 记录起始Y坐标: {event['value']} (原始触摸传感器值)")
                current_touch['end_y'] = event['value']

            # 单点触控坐标
            elif event['code'] == 0x00:  # ABS_X (0)
                if current_touch['start_x'] is None and current_touch['is_touching']:
                    current_touch['start_x'] = event['value']
                    print(f"📍 记录起始X坐标(单点): {event['value']} (原始触摸传感器值)")
                current_touch['end_x'] = event['value']

            elif event['code'] == 0x01:  # ABS_Y (1)
                if current_touch['start_y'] is None and current_touch['is_touching']:
                    current_touch['start_y'] = event['value']
                    print(f"📍 记录起始Y坐标(单点): {event['value']} (原始触摸传感器值)")
                current_touch['end_y'] = event['value']

        elif event['type'] == 1:  # EV_KEY (按键事件)
            # 触摸按键
            if event['code'] in [0x14a, 0x110, 0x111]:  # BTN_TOUCH, BTN_LEFT, BTN_RIGHT
                if event['value'] == 1:  # 按下
                    current_touch['is_touching'] = True
                    current_touch['start_time'] = event['timestamp']
                    print("👆 检测到触摸开始")

                elif event['value'] == 0:  # 抬起
                    current_touch['is_touching'] = False
                    current_touch['end_time'] = event['timestamp']
                    print("👆 检测到触摸结束")

                    # 完成一次触摸，生成命令
                    self.generate_touch_command(current_touch)
                    # 重置当前触摸状态
                    self.reset_touch_state(current_touch)

    def reset_touch_state(self, current_touch):
        """重置触摸状态"""
        current_touch.update({
            'start_time': None,
            'end_time': None,
            'start_x': None,
            'start_y': None,
            'end_x': None,
            'end_y': None,
            'is_touching': False
        })

    def generate_touch_command(self, touch_data):
        """根据触摸数据生成命令"""
        if not all([touch_data['start_x'], touch_data['start_y'],
                   touch_data['end_x'], touch_data['end_y'],
                   touch_data['start_time'], touch_data['end_time']]):
            return

        # 原始触摸传感器坐标
        raw_start_x = touch_data['start_x']
        raw_start_y = touch_data['start_y']
        raw_end_x = touch_data['end_x']
        raw_end_y = touch_data['end_y']
        duration = int((touch_data['end_time'] - touch_data['start_time']) * 1000)  # 转换为毫秒

        print(f"\n📊 坐标分析:")
        print(f"   原始起始坐标: ({raw_start_x}, {raw_start_y})")
        print(f"   原始结束坐标: ({raw_end_x}, {raw_end_y})")

        # 坐标转换：动态获取屏幕分辨率进行转换
        screen_width, screen_height = get_screen_resolution()
        if not screen_width or not screen_height:
            print("⚠️ 无法获取屏幕分辨率，使用默认转换规律")
            screen_width, screen_height = 1080, 1920  # 默认值
        
        # 坐标转换：屏幕X = 原始Y坐标，屏幕Y = 屏幕高度 - 原始X坐标
        start_x = raw_start_y
        start_y = screen_height - raw_start_x
        end_x = raw_end_y
        end_y = screen_height - raw_end_x

        print(f"   转换后起始坐标: ({start_x}, {start_y}) [已转换]")
        print(f"   转换后结束坐标: ({end_x}, {end_y}) [已转换]")
        print(f"   转换规律: 屏幕X=原始Y, 屏幕Y={screen_height}-原始X")

        # 计算移动距离（使用转换后坐标）
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

        # 判断是点击还是滑动
        if distance < 5:  # 移动距离小于5像素认为是点击
            command = f"{start_x},{start_y}"
            command_type = "点击"
            print(f"✅ 生成点击命令: {command} (已转换为屏幕坐标)")
        else:
            command = f"SWIPE:{start_x},{start_y},{end_x},{end_y},{duration}"
            command_type = "滑动"
            print(f"✅ 生成滑动命令: {command} (已转换为屏幕坐标)")

        # 保存命令记录（包含原始坐标信息）
        record = {
            'type': command_type,
            'command': command,
            'start_pos': (start_x, start_y),
            'end_pos': (end_x, end_y),
            'raw_start_pos': (raw_start_x, raw_start_y),  # 保存原始坐标
            'raw_end_pos': (raw_end_x, raw_end_y),
            'duration': duration,
            'distance': distance,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.recorded_commands.append(record)
        logger.info(f"记录{command_type}命令: {command} (原始坐标: {raw_start_x},{raw_start_y} -> {raw_end_x},{raw_end_y})")

    def process_recorded_events(self):
        """处理记录完成后的事件"""
        if not self.recorded_commands:
            print("❌ 没有记录到任何触摸事件")
            return

        print(f"\n✓ 记录完成！共记录 {len(self.recorded_commands)} 个触摸操作")
        self.show_recorded_commands()

    def manual_coordinate_recording(self):
        """手动记录坐标的备选方案"""
        print("\n=== 手动坐标记录 ===")
        print("这是一个备选方案，当getevent不可用时使用")
        print("您需要手动输入触摸操作的坐标信息")

        while True:
            print("\n选择操作类型:")
            print("1. 记录点击操作")
            print("2. 记录滑动操作")
            print("3. 完成记录")

            choice = input("请选择 (1-3): ").strip()

            if choice == '3':
                break
            elif choice == '1':
                self.manual_record_tap()
            elif choice == '2':
                self.manual_record_swipe()
            else:
                print("❌ 无效选择")

    def manual_record_tap(self):
        """手动记录点击操作"""
        try:
            print("\n--- 记录点击操作 ---")
            x = int(input("请输入点击的X坐标: "))
            y = int(input("请输入点击的Y坐标: "))

            command = f"{x},{y}"
            record = {
                'type': '点击',
                'command': command,
                'start_pos': (x, y),
                'end_pos': (x, y),
                'duration': 0,
                'distance': 0,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            self.recorded_commands.append(record)
            print(f"✓ 已记录点击命令: {command}")

        except ValueError:
            print("❌ 请输入有效的数字坐标")

    def manual_record_swipe(self):
        """手动记录滑动操作"""
        try:
            print("\n--- 记录滑动操作 ---")
            x1 = int(input("请输入起始X坐标: "))
            y1 = int(input("请输入起始Y坐标: "))
            x2 = int(input("请输入结束X坐标: "))
            y2 = int(input("请输入结束Y坐标: "))
            duration = int(input("请输入滑动持续时间(毫秒，建议300-1000): ") or "500")

            command = f"SWIPE:{x1},{y1},{x2},{y2},{duration}"
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

            record = {
                'type': '滑动',
                'command': command,
                'start_pos': (x1, y1),
                'end_pos': (x2, y2),
                'duration': duration,
                'distance': distance,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            self.recorded_commands.append(record)
            print(f"✓ 已记录滑动命令: {command}")

        except ValueError:
            print("❌ 请输入有效的数字")

    def show_raw_touch_events(self):
        """显示原始触摸事件代码 (调试用)"""
        print("\n=== 显示原始触摸事件代码 (调试用) ===")
        
        # 检查是否已找到工作设备
        if not self.working_touch_device:
            print("⚠️ 未找到工作触摸设备，正在查找...")
            device = self.find_touch_device()
            if not device:
                print("❌ 无法找到可用的触摸设备")
                return
        else:
            device = self.working_touch_device
            print(f"使用已找到的触摸设备: {device}")

        print("即将显示原始触摸事件代码...")
        print("请在手机屏幕上进行触摸操作")
        print("按 Ctrl+C 停止显示")
        print("\n事件代码说明:")
        print("  EV_ABS (0003): 绝对坐标事件")
        print("    ABS_MT_POSITION_X (0035): 多点触控X坐标")
        print("    ABS_MT_POSITION_Y (0036): 多点触控Y坐标")
        print("    ABS_X (0000): 单点触控X坐标")
        print("    ABS_Y (0001): 单点触控Y坐标")
        print("  EV_KEY (0001): 按键事件")
        print("    BTN_TOUCH (014a): 触摸按键")
        print("  数值说明: 按下=1, 抬起=0, 坐标=实际像素值")

        try:
            command = f"adb shell getevent {device}"
            print(f"\n执行命令: {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)

            print("✓ 开始显示原始触摸事件代码...")
            print("🔍 原始事件格式: 设备路径: 事件类型 事件代码 事件值")
            print("-" * 60)

            event_count = 0
            while True:
                line = process.stdout.readline()
                if not line:
                    error_line = process.stderr.readline()
                    if error_line:
                        print(f"⚠️ 错误: {error_line.strip()}")
                    break

                if line.strip():
                    event_count += 1
                    raw_line = line.strip()
                    
                    # 解析并显示事件详情
                    event_data = self.parse_event_line(raw_line)
                    if event_data:
                        # 显示原始行
                        print(f"🔍 原始: {raw_line}")
                        
                        # 显示解析结果
                        event_type = event_data['type']
                        event_code = event_data['code']
                        event_value = event_data['value']
                        
                        # 事件类型解释
                        type_names = {
                            0: 'EV_SYN', 1: 'EV_KEY', 2: 'EV_REL', 3: 'EV_ABS',
                            4: 'EV_MSC', 5: 'EV_SW'
                        }
                        type_name = type_names.get(event_type, f'TYPE_{event_type:04x}')
                        
                        # 事件代码解释
                        if event_type == 3:  # EV_ABS
                            abs_codes = {
                                0x00: 'ABS_X', 0x01: 'ABS_Y',
                                0x35: 'ABS_MT_POSITION_X', 0x36: 'ABS_MT_POSITION_Y',
                                0x39: 'ABS_MT_TRACKING_ID', 0x3a: 'ABS_MT_PRESSURE'
                            }
                            code_name = abs_codes.get(event_code, f'ABS_0x{event_code:02x}')
                        elif event_type == 1:  # EV_KEY
                            key_codes = {
                                0x14a: 'BTN_TOUCH', 0x110: 'BTN_LEFT', 0x111: 'BTN_RIGHT'
                            }
                            code_name = key_codes.get(event_code, f'KEY_0x{event_code:02x}')
                        else:
                            code_name = f'CODE_0x{event_code:02x}'
                        
                        print(f"📱 解析: {type_name}: {code_name} = {event_value}")
                        
                        # 特殊值解释
                        if event_type == 1 and event_code == 0x14a:  # BTN_TOUCH
                            action = "按下" if event_value == 1 else "抬起" if event_value == 0 else f"值{event_value}"
                            print(f"   👆 触摸动作: {action}")
                        elif event_type == 3 and event_code in [0x00, 0x35]:  # X坐标
                            print(f"   📍 X坐标: {event_value} (原始触摸传感器值)")
                        elif event_type == 3 and event_code in [0x01, 0x36]:  # Y坐标
                            print(f"   📍 Y坐标: {event_value} (原始触摸传感器值)")
                            
                        print("-" * 40)

        except KeyboardInterrupt:
            print(f"\n⏹️ 停止显示 (共显示了 {event_count} 个事件)")
        except Exception as e:
            print(f"❌ 显示原始事件失败: {e}")
        finally:
            if 'process' in locals():
                process.terminate()

    def show_recorded_commands(self):
        """显示已记录的命令"""
        if not self.recorded_commands:
            print("❌ 暂无记录的命令")
            return

        print(f"\n=== 已记录的命令 (共 {len(self.recorded_commands)} 条) ===")
        for i, record in enumerate(self.recorded_commands, 1):
            print(f"\n[{i}] {record['type']} - {record['timestamp']}")
            print(f"    命令: {record['command']}")
            print(f"    起始位置: {record['start_pos']}")
            print(f"    结束位置: {record['end_pos']}")
            print(f"    持续时间: {record['duration']}ms")
            print(f"    移动距离: {record['distance']:.1f}px")

    def save_commands_to_file(self):
        """保存命令到文件"""
        if not self.recorded_commands:
            print("❌ 没有可保存的命令")
            return

        try:
            # 保存为文本格式
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 触摸命令记录 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 共记录 {len(self.recorded_commands)} 个触摸操作\n\n")

                # 只保存命令，用于直接使用
                f.write("# 可直接复制使用的命令序列:\n")
                commands_only = [record['command'] for record in self.recorded_commands]
                f.write(" ".join(commands_only) + "\n\n")

                # 详细信息
                f.write("# 详细记录信息:\n")
                for i, record in enumerate(self.recorded_commands, 1):
                    f.write(f"# [{i}] {record['type']} - {record['timestamp']}\n")
                    f.write(f"# 起始: {record['start_pos']}, 结束: {record['end_pos']}\n")
                    f.write(f"# 持续: {record['duration']}ms, 距离: {record['distance']:.1f}px\n")
                    f.write(f"{record['command']}\n\n")

            # 同时保存为JSON格式，便于程序读取
            json_file = self.output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.recorded_commands, f, ensure_ascii=False, indent=2)

            print(f"✓ 命令已保存到文件:")
            print(f"  文本格式: {self.output_file}")
            print(f"  JSON格式: {json_file}")

        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            logger.error(f"保存触摸命令失败: {e}")

    def clear_records(self):
        """清空记录"""
        if not self.recorded_commands:
            print("❌ 没有可清空的记录")
            return

        confirm = input(f"确定要清空 {len(self.recorded_commands)} 条记录吗？(y/n): ").strip().lower()
        if confirm == 'y':
            self.recorded_commands.clear()
            print("✓ 记录已清空")
        else:
            print("❌ 取消清空操作")

    def test_generated_commands(self):
        """测试生成的命令"""
        if not self.recorded_commands:
            print("❌ 没有可测试的命令")
            return

        print(f"\n🧪 测试已记录的命令 ({len(self.recorded_commands)} 条)")

        confirm = input("确定要开始测试吗？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消测试")
            return

        print("开始执行命令...")

        for i, record in enumerate(self.recorded_commands, 1):
            print(f"[{i}/{len(self.recorded_commands)}] 执行: {record['command']}")

            if record['type'] == '点击':
                # 解析点击命令
                coords = record['command'].split(',')
                x, y = int(coords[0]), int(coords[1])
                success = tap_screen(x, y)
            else:  # 滑动
                # 解析滑动命令
                params = record['command'][6:].split(',')  # 去掉 'SWIPE:' 前缀
                x1, y1, x2, y2, duration = map(int, params)
                success = swipe_screen(x1, y1, x2, y2, duration)

            if success:
                print(f"  ✓ 执行成功")
            else:
                print(f"  ❌ 执行失败")
                break

            # 命令间间隔
            if i < len(self.recorded_commands):
                time.sleep(DEFAULT_INTERVAL)

        print("✓ 命令测试完成")


if __name__ == "__main__":
    logger.info("=== ADB游戏自动化调试器启动 ===")

    # 启动时检查ADB连接
    print("正在检查ADB连接...")
    if not check_adb_connection():
        print("❌ ADB连接失败！请检查：")
        print("1. 手机是否已连接并开启USB调试")
        print("2. ADB是否已安装并添加到PATH")
        print("3. 是否已授权此电脑进行USB调试")
        input("按回车键退出...")
        exit(1)

    print("✓ ADB连接正常")

    # 获取屏幕信息
    print("\n正在获取设备屏幕信息...")
    screen_width, screen_height = get_screen_resolution()
    if screen_width and screen_height:
        print(f"✓ 屏幕分辨率: {screen_width}x{screen_height}")
    else:
        print("⚠️ 无法获取屏幕分辨率")
    get_screen_info()

    while True:
        print("\n" + "="*55)
        print("        ADB游戏自动化调试器 v2.0")
        print("="*55)
        print("1. 移动测试 (W/A/S/D) - 使用longpress方法")
        print("2. 统一命令执行 - 移动/点击/滑动混合操作")
        print("3. 触摸参数记录器 - 记录滑动和点击参数")
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

            if key_choice not in KEYMAP or key_choice == 'J':
                print("❌ 无效的键位，请输入 W、A、S 或 D")
                continue

            try:
                press_count = int(input(f"按 '{key_choice}' 键多少次? "))
                if press_count <= 0:
                    print("❌ 次数必须大于0")
                    continue

                delay = float(input(f"按键间隔时间(秒，默认{KEY_INTERVAL}): ") or str(KEY_INTERVAL))
                if delay < 0:
                    print("❌ 延迟时间不能为负数")
                    continue

                direction_names = {"W": "向上", "A": "向左", "S": "向下", "D": "向右"}
                print(f"\n即将执行: {key_choice}键 ({direction_names[key_choice]}) × {press_count}次，间隔{delay}秒")
                input("请观察屏幕，然后按回车开始...")

                success = press_key_optimized(KEYMAP[key_choice], press_count, delay)
                if success:
                    print("✓ 按键命令发送完成")
                else:
                    print("❌ 按键命令发送失败")

            except ValueError:
                print("❌ 请输入有效的数字")

        elif choice == '2':
            execute_unified_commands()

        elif choice == '3':
            touch_recorder = TouchEventRecorder()
            touch_recorder.start_recording_menu()

        elif choice == '4':
            print("\n=== ADB连接状态 ===")
            if check_adb_connection():
                print("✓ ADB连接正常")
            else:
                print("❌ ADB连接异常")

        elif choice == '5':
            print("\n=== 屏幕信息 ===")
            get_screen_info()

        else:
            print("❌ 无效选择，请重新输入")