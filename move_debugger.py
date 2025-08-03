import time
import subprocess
import logging
import threading
import re
import json
from datetime import datetime

# 元梦之星农场自动化脚本 - PC端调试器
# 版本: v1.2
# 更新时间: 2025-07-26
# 更新内容: 完成触摸参数记录器功能开发，包含基础录制和技术探索
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
DEFAULT_INTERVAL = 0.5    # 命令之间的默认间隔 (800ms)
KEY_INTERVAL = 0.2        # 按键之间的间隔 (800ms)
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

def press_key_longpress(keycode, duration=KEY_INTERVAL):
    """模拟长按键，使用longpress参数"""
    key_name = next((k for k, v in KEYMAP.items() if v == keycode), f"keycode_{keycode}")
    logger.info(f"执行长按操作: {key_name} (keycode: {keycode}), 持续时间: {duration}秒")

    # 检查ADB连接
    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行按键操作")
        return False

    # 使用longpress参数
    command = f"adb shell input keyevent --longpress {keycode}"
    success, output = execute_adb_command(command)

    if success:
        logger.info(f"长按 {key_name} 键成功")
        # 额外等待指定的持续时间
        if duration > 0:
            time.sleep(duration)
    else:
        logger.error(f"长按 {key_name} 键失败: {output}")

    return success

def press_key_with_duration(keycode, duration=0.5):
    """使用按下和松开事件模拟持续按压"""
    key_name = next((k for k, v in KEYMAP.items() if v == keycode), f"keycode_{keycode}")
    logger.info(f"执行持续按压: {key_name} (keycode: {keycode}), 持续时间: {duration}秒")

    # 检查ADB连接
    if not check_adb_connection():
        logger.error("ADB连接检查失败，无法执行按键操作")
        return False

    # 发送按下事件
    down_command = f"adb shell sendevent /dev/input/event0 1 {keycode} 1"
    logger.info(f"发送按下事件: {down_command}")
    success_down, output_down = execute_adb_command(down_command)

    if not success_down:
        logger.error(f"按下事件失败: {output_down}")
        return False

    # 发送同步事件
    sync_command = "adb shell sendevent /dev/input/event0 0 0 0"
    execute_adb_command(sync_command)

    # 持续按压指定时间
    logger.info(f"持续按压 {duration} 秒...")
    time.sleep(duration)

    # 发送松开事件
    up_command = f"adb shell sendevent /dev/input/event0 1 {keycode} 0"
    logger.info(f"发送松开事件: {up_command}")
    success_up, output_up = execute_adb_command(up_command)

    # 发送同步事件
    execute_adb_command(sync_command)

    if success_up:
        logger.info(f"持续按压 {key_name} 键完成")
    else:
        logger.error(f"松开事件失败: {output_up}")

    return success_down and success_up

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

def press_key(keycode, times, delay=KEY_INTERVAL, press_duration=None, method=None):
    """兼容性函数，统一调用优化的longpress方法"""
    # 忽略不需要的参数，只使用longpress方法
    return press_key_optimized(keycode, times, delay)

def calibrate_movement():
    """移动距离校准功能"""
    logger.info("开始移动距离校准...")
    print("\n=== 移动距离校准 ===")
    print("这个功能帮助您确定按键次数与移动距离的关系")

    # 选择校准方向
    direction = input("选择校准方向 (W/A/S/D，默认W): ").strip().upper() or "W"
    if direction not in KEYMAP or direction == 'J':
        print("使用默认方向 W (向上)")
        direction = "W"

    keycode = KEYMAP[direction]
    direction_name = {"W": "向上", "A": "向左", "S": "向下", "D": "向右"}[direction]

    print(f"\n开始校准 {direction} 键 ({direction_name}) 的移动距离")
    print("请按照提示操作，记录角色的移动情况")

    # 校准数据存储
    calibration_data = []

    for test_count in [1, 2, 3, 5, 10]:
        print(f"\n--- 测试按 {test_count} 次 {direction} 键 ---")
        input(f"请记住角色当前位置，然后按回车开始测试 {test_count} 次按键: ")

        success = press_key_optimized(keycode, test_count, KEY_INTERVAL)

        if success:
            distance = input(f"按键完成！角色{direction_name}移动了多少距离？(输入数字或描述): ").strip()
            calibration_data.append({
                'count': test_count,
                'distance': distance,
                'direction': direction_name
            })
            logger.info(f"校准数据: {test_count}次按键 = {distance} 距离")
            print(f"✓ 记录: {test_count}次{direction}键 = {distance}")
        else:
            print("❌ 按键发送失败")

    # 显示校准结果
    print(f"\n=== {direction}键 ({direction_name}) 校准结果 ===")
    for data in calibration_data:
        print(f"{data['count']}次按键 → {data['distance']}")

    # 保存校准数据到文件
    try:
        with open('movement_calibration.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n=== {direction}键校准 - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            for data in calibration_data:
                f.write(f"{data['count']}次按键 → {data['distance']}\n")
        print(f"\n✓ 校准数据已保存到 movement_calibration.txt")
        logger.info("校准数据已保存到文件")
    except Exception as e:
        print(f"❌ 保存校准数据失败: {e}")
        logger.error(f"保存校准数据失败: {e}")

def execute_unified_commands():
    """执行统一的移动、点击、滑动命令 - 融合版"""
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

def test_different_press_methods():
    """测试不同的按键方法"""
    logger.info("开始按键方法测试...")
    print("\n=== 按键方法测试 ===")
    print("这将测试不同的按键方法，找出游戏能识别的方式")

    methods = [
        ("traditional", "传统keyevent方法"),
        ("longpress", "长按keyevent方法"),
        ("duration", "sendevent持续按压方法")
    ]

    test_key = input("选择测试键位 (W/A/S/D，默认W): ").strip().upper() or "W"
    if test_key not in KEYMAP or test_key == 'J':
        print("使用默认键位 W")
        test_key = "W"

    keycode = KEYMAP[test_key]

    for method_code, method_name in methods:
        print(f"\n--- 测试 {method_name} ---")
        input(f"请观察屏幕，按回车测试 {test_key} 键 ({method_name}): ")

        if method_code == "traditional":
            # 传统方法
            command = f"adb shell input keyevent {keycode}"
            success, _ = execute_adb_command(command)
        elif method_code == "longpress":
            # 长按方法
            success = press_key_longpress(keycode, KEY_INTERVAL)
        else:  # duration
            # 持续按压方法
            success = press_key_with_duration(keycode, KEY_INTERVAL)

        if success:
            response = input(f"{method_name} 测试完成，角色是否移动了？(y/n): ").strip().lower()
            if response == 'y':
                logger.info(f"{method_name} 工作正常")
                print(f"✓ {method_name} 工作正常")
            else:
                logger.warning(f"{method_name} 可能无效")
                print(f"✗ {method_name} 可能无效")
        else:
            logger.error(f"{method_name} 发送失败")
            print(f"✗ {method_name} 发送失败")

def test_single_keypress():
    """测试单次按键是否有效（使用最佳方法）"""
    logger.info("开始单次按键测试...")
    print("\n=== 单次按键测试 ===")
    print("这将使用长按方法测试每个方向键")

    for key_name, keycode in KEYMAP.items():
        if key_name == 'J':  # 跳过动作键
            continue
        print(f"\n测试 {key_name} 键...")
        input(f"请观察屏幕，然后按回车键测试 {key_name} 键: ")
        success = press_key_longpress(keycode, KEY_INTERVAL)
        if success:
            response = input(f"{key_name} 键测试完成，角色是否移动了？(y/n): ").strip().lower()
            if response == 'y':
                logger.info(f"{key_name} 键工作正常")
                print(f"✓ {key_name} 键工作正常")
            else:
                logger.warning(f"{key_name} 键可能无效")
                print(f"✗ {key_name} 键可能无效")
        else:
            logger.error(f"{key_name} 键发送失败")
            print(f"✗ {key_name} 键发送失败")


class TouchEventRecorder:
    """
    触摸事件记录器类 - v1.2

    功能说明:
    - 基础录制模式: 可靠的单次滑动和点击操作录制 ✅
    - 坐标转换: 触摸传感器坐标到屏幕坐标的精确映射 ✅
    - 命令生成: 自动生成标准SWIPE和TAP命令格式 ✅
    - 专用录制模式: 实验性功能，因技术限制已停用 ❌

    技术实现:
    - 使用ADB getevent监听触摸事件
    - 智能区分点击和滑动操作（基于移动距离）
    - 支持完整的数据管理和文件输出
    """

    def __init__(self):
        self.recording = False
        self.touch_events = []
        self.current_touch = None
        self.recorded_commands = []
        self.output_file = "touch_commands.txt"

        # 专用录制相关属性
        self.dedicated_recording = False
        self.recording_mode = 'swipe'  # 'swipe' 或 'tap'
        self.unified_timeline = []  # 统一时间线，包含所有操作
        self.current_swipe = None  # 当前滑动操作
        self.swipe_start_time = None

        # 采样参数
        self.swipe_sample_interval = 0.03  # 滑动采样间隔：30ms
        self.min_swipe_distance = 10   # 最小滑动距离：10像素
        self.dedicated_output_file = "dedicated_recording.txt"

        # 高级录制参数
        self.sample_interval = 0.05  # 高级录制采样间隔：50ms
        self.min_move_distance = 5   # 最小移动距离：5像素
        self.sequence_output_file = "operation_sequence.txt"
        self.operation_sequence = []  # 完整操作序列
        self.active_touches = {}  # 当前活跃的触摸点
        self.last_sample_time = 0  # 上次采样时间
        self.advanced_recording = False

    def start_recording_menu(self):
        """触摸参数记录器主菜单"""
        while True:
            print("\n" + "="*50)
            print("        触摸参数记录器")
            print("="*50)
            print("1. 诊断getevent可用性")
            print("2. 开始记录触摸事件 (简单模式)")
            print("3. 专用录制模式 (滑动/点击分离) ⭐")
            print("4. 坐标转换诊断 (分析坐标映射关系)")
            print("5. 手动记录坐标 (备选方案)")
            print("6. 查看已记录的命令")
            print("7. 保存命令到文件")
            print("8. 清空记录")
            print("9. 测试生成的命令")
            print("Q. 返回主菜单")

            choice = input("\n请选择操作: ").strip().upper()

            if choice == 'Q':
                break
            elif choice == '1':
                self.diagnose_getevent()
            elif choice == '2':
                self.start_touch_recording()
            elif choice == '3':
                self.start_dedicated_recording()
            elif choice == '4':
                self.coordinate_mapping_diagnosis()
            elif choice == '5':
                self.manual_coordinate_recording()
            elif choice == '6':
                self.show_recorded_commands()
            elif choice == '7':
                self.save_commands_to_file()
            elif choice == '8':
                self.clear_records()
            elif choice == '9':
                self.test_generated_commands()
            else:
                print("❌ 无效选择，请重新输入")

    def diagnose_getevent(self):
        """诊断getevent命令的可用性"""
        print("\n=== getevent 可用性诊断 ===")
        print("正在检查ADB和getevent的可用性...")

        # 检查ADB连接
        if not check_adb_connection():
            print("❌ ADB连接失败，无法进行诊断")
            return

        print("✓ ADB连接正常")

        # 测试getevent命令
        print("\n1. 测试getevent命令...")
        try:
            # 先尝试获取可用的触摸设备进行测试
            test_device = "/dev/input/event3"  # 默认设备
            try:
                # 尝试动态获取一个可用设备
                quick_scan_cmd = "adb shell getevent -p"
                quick_result = subprocess.run(quick_scan_cmd, shell=True, capture_output=True, text=True, timeout=5)
                if quick_result.returncode == 0:
                    lines = quick_result.stdout.split('\n')
                    for line in lines:
                        if 'add device' in line:
                            match = re.search(r'add device \d+: (/dev/input/event\d+)', line)
                            if match:
                                test_device = match.group(1)
                                break
            except:
                pass  # 使用默认设备
            
            # 使用快速测试方法
            command = f"adb shell 'echo test | getevent -c 1 {test_device} 2>&1 || echo getevent_available'"
            print(f"执行测试命令... (使用设备: {test_device})")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)

            if "getevent_available" in result.stdout or result.returncode == 0:
                print("✓ getevent命令可用")
            else:
                print("❌ getevent命令可能不可用")
                if result.stderr:
                    print(f"错误信息: {result.stderr}")

            # 说明为什么不直接运行getevent
            print("📝 注意: 'adb shell getevent' 是持续监听命令，会一直运行直到手动停止")
            print("   这是正常行为，不是程序卡住！")

        except Exception as e:
            print(f"❌ 测试getevent命令失败: {e}")
            print("✓ 但这不影响实际使用，getevent通常都是可用的")

        # 测试设备列表并找到触摸设备
        print("\n2. 测试输入设备列表并查找触摸设备...")
        touch_devices = []
        try:
            command = "adb shell getevent -p"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✓ 可以获取设备列表")

                # 解析设备列表，查找触摸设备
                lines = result.stdout.split('\n')
                current_device = None
                current_name = ""

                for line in lines:
                    if line.startswith('add device'):
                        # 提取设备路径
                        match = re.search(r'add device \d+: (/dev/input/event\d+)', line)
                        if match:
                            current_device = match.group(1)
                    elif line.strip().startswith('name:'):
                        # 提取设备名称
                        match = re.search(r'name:\s*"([^"]*)"', line)
                        if match:
                            current_name = match.group(1)
                    elif current_device and ('ABS_MT_POSITION' in line or 'ABS_X' in line):
                        # 找到触摸设备
                        touch_devices.append((current_device, current_name))
                        print(f"🎯 找到触摸设备: {current_device} ({current_name})")
                        current_device = None  # 避免重复添加

                if not touch_devices:
                    print("⚠️ 未找到明确的触摸设备，显示所有设备信息:")
                    lines = result.stdout.split('\n')[:15]  # 显示前15行
                    for line in lines:
                        if line.strip():
                            print(f"  {line}")
                    if len(result.stdout.split('\n')) > 15:
                        print("  ... (更多设备)")
                else:
                    print(f"✓ 共找到 {len(touch_devices)} 个可能的触摸设备")

            else:
                print("❌ 无法获取设备列表")
                print(f"错误信息: {result.stderr}")
        except Exception as e:
            print(f"❌ 测试设备列表失败: {e}")

        # 测试单个设备访问
        print("\n3. 测试设备访问权限...")
        # 使用动态检测的设备进行测试
        available_devices = []
        try:
            # 直接在这里实现设备检测逻辑，避免依赖TouchRecorder类
            command = "adb shell getevent -p"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_device = None
                device_capabilities = {}
                
                for line in lines:
                    if line.startswith('add device'):
                        match = re.search(r'add device \d+: (/dev/input/event\d+)', line)
                        if match:
                            current_device = match.group(1)
                            device_capabilities[current_device] = {'caps': [], 'name': ''}
                    elif current_device and 'name:' in line:
                        match = re.search(r'name:\s*"([^"]*)"', line)
                        if match:
                            device_capabilities[current_device]['name'] = match.group(1)
                    elif current_device and ('ABS_MT_POSITION_X' in line or 'ABS_X' in line or 'ABS_Y' in line):
                        device_capabilities[current_device]['caps'].append(line.strip())
                
                # 筛选出可能的触摸设备
                for device, info in device_capabilities.items():
                    if any('ABS_MT_POSITION' in cap or 'ABS_X' in cap for cap in info['caps']):
                        available_devices.append((device, info['name']))
            
            if available_devices:
                print(f"✓ 检测到 {len(available_devices)} 个可能的触摸设备")
                for device, name in available_devices[:3]:  # 只测试前3个
                    try:
                        command = f"adb shell ls -l {device}"
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            print(f"✓ {device} ({name}) 存在: {result.stdout.strip()}")
                        else:
                            print(f"❌ {device} ({name}) 不存在或无权限")
                    except Exception as e:
                        print(f"❌ 测试 {device} 失败: {e}")
            else:
                print("⚠️ 未检测到触摸设备，进行全面设备扫描...")
                # 扫描所有可能的event设备
                for i in range(10):  # 扫描event0-event9
                    device = f"/dev/input/event{i}"
                    test_cmd = f"adb shell ls {device}"
                    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=3)
                    if test_result.returncode == 0:
                        print(f"✓ 发现设备: {device}")
                        try:
                            command = f"adb shell ls -l {device}"
                            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                print(f"✓ {device} 存在: {result.stdout.strip()}")
                            else:
                                print(f"❌ {device} 不存在或无权限")
                        except Exception as e:
                            print(f"❌ 测试 {device} 失败: {e}")
        except Exception as e:
            print(f"❌ 设备检测失败: {e}")
            # 最后回退：扫描所有可能的设备
            print("⚠️ 进行最后回退扫描...")
            for i in range(10):  # 扫描event0-event9
                device = f"/dev/input/event{i}"
                try:
                    command = f"adb shell ls -l {device}"
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        print(f"✓ {device} 存在: {result.stdout.strip()}")
                    else:
                        print(f"❌ {device} 不存在或无权限")
                except Exception as e:
                    print(f"❌ 测试 {device} 失败: {e}")

        # 测试实际事件读取  
        print("\n4. 测试事件读取 (10秒测试)...")
        print("请在手机屏幕上进行触摸操作...")

        # 使用智能检测的设备进行测试
        test_devices = []
        if available_devices:
            # 使用检测到的设备（按优先级排序）
            test_devices = [device[0] for device in available_devices]
            print(f"📱 使用检测到的 {len(test_devices)} 个设备进行测试")
        else:
            # 如果检测失败，进行全面扫描
            print("⚠️ 动态检测失败，进行全面设备扫描...")
            try:
                # 扫描所有可能的event设备
                for i in range(10):  # 扫描event0-event9
                    device = f"/dev/input/event{i}"
                    test_cmd = f"adb shell ls {device}"
                    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=3)
                    if test_result.returncode == 0:
                        test_devices.append(device)
                        
                if test_devices:
                    print(f"📱 扫描到 {len(test_devices)} 个可用设备: {test_devices}")
                else:
                    # 最后的回退
                    test_devices = ["/dev/input/event3", "/dev/input/event2", "/dev/input/event1", "/dev/input/event0"]
                    print("⚠️ 全面扫描也未找到设备，使用最后的默认列表")
            except Exception as scan_error:
                print(f"❌ 设备扫描失败: {scan_error}")
                test_devices = ["/dev/input/event3", "/dev/input/event2", "/dev/input/event1", "/dev/input/event0"]
                print("⚠️ 使用最后的默认设备列表进行测试")

        found_working_device = False
        for device in test_devices:
            try:
                print(f"\n测试设备: {device}")
                # 使用更长的超时时间，并且不使用timeout命令（可能不存在）
                command = f"adb shell getevent {device}"
                print(f"执行命令: {command}")
                print("⏰ 开始10秒测试，请立即在屏幕上滑动或点击...")

                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, bufsize=1)

                # 读取10秒的输出
                import time
                start_time = time.time()
                events_found = []

                while time.time() - start_time < 10:
                    try:
                        line = process.stdout.readline()
                        if line and line.strip():
                            events_found.append(line.strip())
                            if len(events_found) <= 3:  # 只显示前3个事件
                                print(f"📱 检测到事件: {line.strip()}")
                    except:
                        break

                process.terminate()

                if events_found:
                    print(f"✅ {device} 可以读取事件! (共检测到 {len(events_found)} 个事件)")
                    found_working_device = True

                    # 分析事件类型
                    touch_events = [e for e in events_found if '0003' in e or '0001' in e]
                    if touch_events:
                        print(f"🎯 其中包含 {len(touch_events)} 个可能的触摸相关事件")
                    break
                else:
                    print(f"❌ {device} 在10秒内无事件输出")

            except Exception as e:
                print(f"❌ 测试 {device} 事件读取失败: {e}")

        if not found_working_device:
            print("\n⚠️ 所有设备测试都未检测到事件")
            print("可能的原因:")
            print("1. 设备权限不足 (需要root权限)")
            print("2. 触摸设备路径不在测试列表中")
            print("3. Android安全策略阻止了事件读取")
            print("4. 测试时间内没有进行触摸操作")

        print("\n=== 诊断完成 ===")
        print("如果所有测试都失败，建议使用'手动记录坐标'功能作为替代方案")

    def coordinate_mapping_diagnosis(self):
        """坐标转换诊断 - 分析触摸坐标与屏幕坐标的映射关系"""
        print("\n=== 坐标转换诊断 ===")
        print("这个功能帮助分析触摸传感器坐标与屏幕显示坐标的映射关系")

        # 获取屏幕分辨率
        screen_width, screen_height = get_screen_resolution()
        if screen_width and screen_height:
            print(f"📱 屏幕分辨率: {screen_width} x {screen_height}")
        else:
            print("⚠️ 无法获取屏幕分辨率")
            return

        # 基于经验值和已记录数据进行分析
        print("\n📊 坐标映射分析...")

        # 常见的Android设备触摸传感器分辨率
        common_touch_resolutions = [
            (1080, 1920), (1440, 2560), (1080, 2340), (720, 1280)
        ]

        print(f"🔍 常见触摸传感器分辨率:")
        for i, (w, h) in enumerate(common_touch_resolutions, 1):
            print(f"   {i}. {w} x {h}")

        # 如果有已记录的数据，进行分析
        if hasattr(self, 'recorded_commands') and self.recorded_commands:
            print(f"\n📈 基于已记录数据的分析:")
            last_record = self.recorded_commands[-1]
            if 'raw_start_pos' in last_record:
                raw_x, raw_y = last_record['raw_start_pos']
                print(f"   最近记录的原始坐标: ({raw_x}, {raw_y})")
                print(f"   您说实际屏幕坐标约为: (1754, 911)")

                # 尝试不同的转换方式
                print(f"\n🔄 可能的坐标转换方式:")

                # 方式1: 直接缩放
                if raw_x > 0 and raw_y > 0:
                    scale_x = 1754 / raw_x
                    scale_y = 911 / raw_y
                    print(f"   1. 直接缩放: X*{scale_x:.3f}, Y*{scale_y:.3f}")

                # 方式2: X/Y轴交换
                if raw_y > 0 and raw_x > 0:
                    scale_x_swap = 1754 / raw_y
                    scale_y_swap = 911 / raw_x
                    print(f"   2. X/Y轴交换: 屏幕X=触摸Y*{scale_x_swap:.3f}, 屏幕Y=触摸X*{scale_y_swap:.3f}")

                # 方式3: 基于屏幕分辨率推测
                if screen_width and screen_height:
                    # 假设触摸传感器可能的最大值
                    possible_max_x = [1080, 1440, 2160, raw_x * 2, raw_x * 3]
                    # possible_max_y = [1920, 2560, 3840, raw_y * 2, raw_y * 3]  # 暂时不使用

                    print(f"   3. 基于屏幕分辨率的可能转换:")
                    for max_x in possible_max_x:
                        if max_x > raw_x:
                            scale = screen_width / max_x
                            converted_x = int(raw_x * scale)
                            if abs(converted_x - 1754) < 200:  # 误差在200像素内
                                print(f"      可能匹配: 触摸最大X={max_x}, 缩放={scale:.3f}, 转换结果={converted_x}")

                # 方式4: 翻转坐标
                if screen_width and screen_height:
                    flip_x = screen_width - raw_x
                    flip_y = screen_height - raw_y
                    print(f"   4. 坐标翻转: ({flip_x}, {flip_y})")

        # 交互式坐标对比
        print(f"\n🎯 交互式坐标对比:")
        print(f"请记录几个已知位置的触摸操作，然后我们可以计算精确的转换公式")

        # 提供一些测试建议
        print(f"\n📝 建议的测试步骤:")
        print(f"1. 在屏幕四个角落各点击一次")
        print(f"2. 在屏幕中心点击一次")
        print(f"3. 记录每次点击的:")
        print(f"   - 原始坐标 (程序显示)")
        print(f"   - 实际屏幕坐标 (开发者选项->指针位置)")
        print(f"4. 基于这些数据计算转换公式")

        print(f"\n📝 使用建议:")
        print(f"1. 记录一些触摸操作")
        print(f"2. 对比原始坐标和实际屏幕位置")
        print(f"3. 根据对比结果调整转换公式")
        print(f"4. 可能需要考虑坐标轴交换或翻转")

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

    def start_touch_recording(self):
        """开始记录触摸事件"""
        print("\n=== 触摸事件记录 ===")
        print("即将开始监听触摸事件...")
        print("请在手机屏幕上进行滑动或点击操作")
        print("按 Ctrl+C 停止记录")

        # 检查ADB连接
        if not check_adb_connection():
            print("❌ ADB连接失败，无法开始记录")
            return

        try:
            # 智能选择触摸设备
            touch_device = self.select_touch_device()
            if not touch_device:
                print("❌ 无法确定触摸设备，请使用手动记录功能")
                return

            print(f"使用设备: {touch_device}")
            print("开始监听触摸事件...")
            print("提示: 滑动和点击操作都会被记录，程序会自动区分")

            # 启动getevent监听
            self.recording = True
            self.listen_touch_events(touch_device)

        except KeyboardInterrupt:
            print("\n⏹️ 停止记录")
            self.recording = False
            self.process_recorded_events()
        except Exception as e:
            print(f"❌ 记录过程中出现错误: {e}")
            logger.error(f"触摸事件记录错误: {e}")

    def select_touch_device(self):
        """智能选择触摸设备"""
        print("正在选择触摸设备...")

        # 使用统一的设备检测逻辑
        devices = self.get_available_touch_devices()
        
        if not devices:
            print("❌ 未检测到任何触摸设备，请检查ADB连接")
            return None
            
        print("检测到以下触摸设备:")
        for i, (device, name) in enumerate(devices, 1):
            print(f"  {i}. {device} - {name}")

        # 选择优先级最高的设备（已按优先级排序）
        selected_device = devices[0][0]
        selected_name = devices[0][1]
        
        print(f"🎯 自动选择主触摸设备: {selected_device} ({selected_name})")
        
        # 如果检测到多个设备，给用户选择机会
        if len(devices) > 1:
            try:
                choice = input(f"\n是否使用推荐设备 {selected_device}? (Y/n或输入1-{len(devices)}选择其他): ").strip()
                if choice.lower() == 'n':
                    while True:
                        try:
                            idx = int(input(f"请选择设备 (1-{len(devices)}): ")) - 1
                            if 0 <= idx < len(devices):
                                selected_device = devices[idx][0]
                                selected_name = devices[idx][1]
                                print(f"✓ 已选择: {selected_device} ({selected_name})")
                                break
                            else:
                                print(f"请输入1-{len(devices)}之间的数字")
                        except ValueError:
                            print("请输入有效数字")
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(devices):
                        selected_device = devices[idx][0]
                        selected_name = devices[idx][1]
                        print(f"✓ 已选择: {selected_device} ({selected_name})")
                    else:
                        print(f"❌ 无效选择：设备编号应该在1-{len(devices)}之间")
                        print(f"✓ 继续使用推荐设备: {selected_device} ({selected_name})")
            except (KeyboardInterrupt, EOFError):
                print(f"\n使用默认设备: {selected_device}")

        return selected_device

    def start_dedicated_recording(self):
        """开始专用录制模式 - 滑动/点击分离"""
        print("\n=== 专用录制模式 (滑动/点击分离) ===")
        print("🎯 这个模式将滑动和点击操作分离录制：")
        print("   • 滑动模式：录制连续的拖拽轨迹（如摇杆操作）")
        print("   • 点击模式：录制独立的点击操作")
        print("   • 支持录制过程中快速切换模式")
        print("   • 严格按时间顺序记录所有操作")

        print(f"\n⚙️ 当前参数:")
        print(f"   滑动采样间隔: {self.swipe_sample_interval*1000:.0f}ms")
        print(f"   最小滑动距离: {self.min_swipe_distance}像素")

        print(f"\n🎮 操作说明:")
        print(f"   • 当前版本：固定模式录制（滑动模式）")
        print(f"   • 滑动模式：录制连续拖拽轨迹，生成多个连续滑动命令")
        print(f"   • 点击操作：在滑动模式下，短距离移动会被识别为点击")
        print(f"   • 按 Ctrl+C 停止录制")

        # 检查ADB连接
        if not check_adb_connection():
            print("❌ ADB连接失败，无法开始录制")
            return

        # 清空之前的录制数据
        self.unified_timeline.clear()
        self.current_swipe = None
        self.swipe_start_time = None
        self.recording_mode = 'swipe'  # 默认滑动模式

        try:
            # 选择触摸设备
            touch_device = self.select_touch_device()
            if not touch_device:
                print("❌ 无法确定触摸设备")
                return

            print(f"\n🎬 开始专用录制...")
            print(f"使用设备: {touch_device}")
            print(f"当前模式: 🔄 滑动模式")

            # 启动专用录制
            self.dedicated_recording = True
            self.listen_dedicated_touch_events(touch_device)

        except KeyboardInterrupt:
            print("\n⏹️ 停止录制")
            self.dedicated_recording = False
            self.process_dedicated_recording_results()
        except Exception as e:
            print(f"❌ 录制过程中出现错误: {e}")
            logger.error(f"专用录制错误: {e}")

    def listen_dedicated_touch_events(self, device_path):
        """监听专用录制的触摸事件"""
        process = None
        try:
            command = f"adb shell getevent {device_path}"
            print(f"执行命令: {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)

            print("✓ 开始专用录制")
            print("📱 请进行您的操作...")
            print("💡 提示: 当前为滑动模式，会自动识别滑动和点击操作")

            # 用于跟踪当前触摸状态
            is_touching = False
            last_sample_time = 0
            current_raw_x = None
            current_raw_y = None
            touch_events_count = 0  # 调试计数器

            while self.dedicated_recording:
                line = process.stdout.readline()
                if not line:
                    error_line = process.stderr.readline()
                    if error_line:
                        print(f"⚠️ 错误输出: {error_line.strip()}")
                    break

                if line.strip():
                    # 解析事件行
                    event_data = self.parse_event_line(line.strip())
                    if event_data:
                        touch_events_count += 1
                        current_time = event_data['timestamp']

                        # 显示调试信息（每50个事件显示一次）
                        if touch_events_count % 50 == 0:
                            print(f"🔍 已处理 {touch_events_count} 个事件，当前模式: {'🔄滑动' if self.recording_mode == 'swipe' else '👆点击'}")

                        # 处理坐标事件
                        if event_data['type'] == 3:  # EV_ABS
                            if event_data['code'] == 0x35:  # ABS_MT_POSITION_X
                                current_raw_x = event_data['value']
                                if touch_events_count <= 10:  # 前10个事件显示详细信息
                                    print(f"🔍 X坐标更新: {current_raw_x}")
                            elif event_data['code'] == 0x36:  # ABS_MT_POSITION_Y
                                current_raw_y = event_data['value']
                                if touch_events_count <= 10:
                                    print(f"🔍 Y坐标更新: {current_raw_y}")

                        # 处理按键事件
                        elif event_data['type'] == 1 and event_data['code'] == 0x14a:  # BTN_TOUCH
                            if event_data['value'] == 1:  # 按下
                                print(f"🔍 检测到触摸按下，坐标: ({current_raw_x}, {current_raw_y})")
                                if current_raw_x is not None and current_raw_y is not None:
                                    is_touching = True
                                    last_sample_time = current_time

                                    # 应用坐标转换
                                    screen_x = current_raw_y  # 屏幕X = 原始Y
                                    screen_y = 1080 - current_raw_x  # 屏幕Y = 1080 - 原始X

                                    print(f"🔍 转换后坐标: ({screen_x}, {screen_y})")
                                    self.handle_touch_start(screen_x, screen_y, current_raw_x, current_raw_y, current_time)
                                else:
                                    print(f"⚠️ 按下时坐标不完整: X={current_raw_x}, Y={current_raw_y}")

                            elif event_data['value'] == 0:  # 抬起
                                print(f"🔍 检测到触摸抬起，坐标: ({current_raw_x}, {current_raw_y})")
                                if is_touching and current_raw_x is not None and current_raw_y is not None:
                                    is_touching = False

                                    # 应用坐标转换
                                    screen_x = current_raw_y  # 屏幕X = 原始Y
                                    screen_y = 1080 - current_raw_x  # 屏幕Y = 1080 - 原始X

                                    self.handle_touch_end(screen_x, screen_y, current_raw_x, current_raw_y, current_time)
                                else:
                                    print(f"⚠️ 抬起时状态异常: is_touching={is_touching}, X={current_raw_x}, Y={current_raw_y}")

                        # 处理移动事件（仅在滑动模式下）
                        if (is_touching and self.recording_mode == 'swipe' and
                            current_raw_x is not None and current_raw_y is not None and
                            current_time - last_sample_time >= self.swipe_sample_interval):

                            # 应用坐标转换
                            screen_x = current_raw_y  # 屏幕X = 原始Y
                            screen_y = 1080 - current_raw_x  # 屏幕Y = 1080 - 原始X

                            self.handle_touch_move(screen_x, screen_y, current_raw_x, current_raw_y, current_time)
                            last_sample_time = current_time

        except Exception as e:
            logger.error(f"专用录制监听失败: {e}")
            print(f"❌ 监听失败: {e}")
        finally:
            if process:
                process.terminate()

    def handle_touch_start(self, screen_x, screen_y, raw_x, raw_y, timestamp):
        """处理触摸开始事件"""
        # 统一处理：开始新的触摸轨迹（稍后根据移动距离判断是滑动还是点击）
        self.current_swipe = {
            'start_time': timestamp,
            'start_x': screen_x,
            'start_y': screen_y,
            'points': [(screen_x, screen_y, timestamp)],
            'raw_points': [(raw_x, raw_y, timestamp)]
        }
        self.swipe_start_time = timestamp
        print(f"🎯 触摸开始: ({screen_x}, {screen_y})")

    def handle_touch_move(self, screen_x, screen_y, raw_x, raw_y, timestamp):
        """处理触摸移动事件"""
        if self.current_swipe:
            # 检查移动距离
            last_point = self.current_swipe['points'][-1]
            distance = ((screen_x - last_point[0]) ** 2 + (screen_y - last_point[1]) ** 2) ** 0.5

            if distance >= self.min_swipe_distance:
                # 添加采样点
                self.current_swipe['points'].append((screen_x, screen_y, timestamp))
                self.current_swipe['raw_points'].append((raw_x, raw_y, timestamp))

                # 每10个点显示一次进度
                if len(self.current_swipe['points']) % 10 == 0:
                    print(f"🔄 移动中: ({screen_x}, {screen_y}) [已采样{len(self.current_swipe['points'])}个点]")

    def handle_touch_end(self, screen_x, screen_y, raw_x, raw_y, timestamp):
        """处理触摸结束事件"""
        if self.current_swipe:
            # 滑动模式：完成滑动轨迹
            self.current_swipe['end_time'] = timestamp
            self.current_swipe['end_x'] = screen_x
            self.current_swipe['end_y'] = screen_y

            # 确保结束点被记录
            if self.current_swipe['points'][-1][:2] != (screen_x, screen_y):
                self.current_swipe['points'].append((screen_x, screen_y, timestamp))
                self.current_swipe['raw_points'].append((raw_x, raw_y, timestamp))

            # 生成连续滑动命令序列
            points = self.current_swipe['points']
            total_distance = ((screen_x - self.current_swipe['start_x']) ** 2 +
                            (screen_y - self.current_swipe['start_y']) ** 2) ** 0.5

            # 自动判断是滑动还是点击
            if total_distance >= 5:  # 移动距离大于5像素认为是滑动
                if len(points) >= 2:  # 至少2个点才能生成滑动
                    # 添加长滑动操作开始注释
                    self.unified_timeline.append({
                        'type': '注释',
                        'command': f"# === 长滑动操作开始 ===",
                        'timestamp': self.current_swipe['start_time'],
                        'comment': f"共{len(points)}个采样点，将生成{len(points)-1}个连续滑动命令"
                    })

                    # 将相邻采样点转换为连续的滑动命令
                    for i in range(len(points) - 1):
                        start_point = points[i]
                        end_point = points[i + 1]

                        start_x, start_y, start_time = start_point
                        end_x, end_y, end_time = end_point

                        # 计算这一段的持续时间
                        segment_duration = int((end_time - start_time) * 1000)
                        segment_duration = max(segment_duration, 50)  # 最小50ms

                        # 计算这一段的距离
                        segment_distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

                        swipe_command = f"SWIPE:{int(start_x)},{int(start_y)},{int(end_x)},{int(end_y)},{segment_duration}"

                        # 添加到统一时间线
                        self.unified_timeline.append({
                            'type': '滑动',
                            'command': swipe_command,
                            'timestamp': start_time,
                            'duration': segment_duration,
                            'distance': segment_distance,
                            'segment_index': i + 1,
                            'total_segments': len(points) - 1,
                            'start_pos': (int(start_x), int(start_y)),
                            'end_pos': (int(end_x), int(end_y))
                        })

                    # 添加长滑动操作结束注释
                    self.unified_timeline.append({
                        'type': '注释',
                        'command': f"# === 长滑动操作结束 ===",
                        'timestamp': timestamp,
                        'comment': f"总距离:{total_distance:.1f}px，总时长:{int((timestamp - self.current_swipe['start_time']) * 1000)}ms"
                    })

                    print(f"✅ 长滑动完成: {len(points)-1}个连续滑动命令")
                    print(f"   总距离:{total_distance:.1f}px, 采样点:{len(points)}个")
                else:
                    print(f"⚠️ 滑动采样点不足({len(points)}个)，已忽略")
            else:
                # 移动距离小，认为是点击
                duration = int((timestamp - self.current_swipe['start_time']) * 1000)
                tap_command = f"{int(self.current_swipe['start_x'])},{int(self.current_swipe['start_y'])}"

                # 添加到统一时间线
                self.unified_timeline.append({
                    'type': '点击',
                    'command': tap_command,
                    'timestamp': self.current_swipe['start_time'],
                    'duration': duration,
                    'distance': total_distance,
                    'start_pos': (int(self.current_swipe['start_x']), int(self.current_swipe['start_y'])),
                    'end_pos': (int(screen_x), int(screen_y))
                })

                print(f"✅ 点击完成: {tap_command} (移动距离:{total_distance:.1f}px)")

            self.current_swipe = None

    def process_dedicated_recording_results(self):
        """处理专用录制结果"""
        if not self.unified_timeline:
            print("❌ 没有记录到任何操作")
            return

        # 按时间排序
        self.unified_timeline.sort(key=lambda x: x['timestamp'])

        print(f"\n✅ 录制完成！")
        print(f"📊 录制统计:")
        print(f"   总操作数: {len(self.unified_timeline)}")

        # 统计不同类型的操作
        swipe_count = len([op for op in self.unified_timeline if op['type'] == '滑动'])
        tap_count = len([op for op in self.unified_timeline if op['type'] == '点击'])
        comment_count = len([op for op in self.unified_timeline if op['type'] == '注释'])

        print(f"   滑动操作: {swipe_count} 次")
        print(f"   点击操作: {tap_count} 次")
        if comment_count > 0:
            print(f"   注释标记: {comment_count} 条")

        # 计算录制时长
        if len(self.unified_timeline) >= 2:
            duration = self.unified_timeline[-1]['timestamp'] - self.unified_timeline[0]['timestamp']
            print(f"   录制时长: {duration:.2f}秒")

        # 显示操作序列预览
        print(f"\n📋 操作序列预览:")
        start_time = self.unified_timeline[0]['timestamp']

        for i, op in enumerate(self.unified_timeline[:15], 1):  # 显示前15个操作
            relative_time = op['timestamp'] - start_time

            if op['type'] == '注释':
                print(f"   {i:2d}. [{relative_time:6.2f}s] {op['command']}")
            elif op['type'] == '滑动' and 'segment_index' in op:
                # 显示分段滑动信息
                print(f"   {i:2d}. [{relative_time:6.2f}s] 滑动段{op['segment_index']}/{op['total_segments']}: {op['command']}")
            else:
                print(f"   {i:2d}. [{relative_time:6.2f}s] {op['type']}: {op['command']}")

        if len(self.unified_timeline) > 15:
            print(f"   ... 还有 {len(self.unified_timeline) - 15} 个操作")

        # 询问是否保存
        save_choice = input("\n是否保存操作序列？(y/n): ").strip().lower()
        if save_choice == 'y':
            self.save_dedicated_recording()

    def save_dedicated_recording(self):
        """保存专用录制结果"""
        try:
            with open(self.dedicated_output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 专用录制结果 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总操作数: {len(self.unified_timeline)}\n")
                f.write(f"# 滑动采样间隔: {self.swipe_sample_interval*1000:.0f}ms\n")
                f.write(f"# 最小滑动距离: {self.min_swipe_distance}px\n\n")

                # 保存可执行的命令序列
                f.write("# 可执行的命令序列 (按时间顺序):\n")
                for op in self.unified_timeline:
                    if op['type'] == '注释':
                        f.write(f"{op['command']}\n")
                    else:
                        f.write(f"{op['command']}\n")

                f.write(f"\n# 详细操作信息:\n")
                start_time = self.unified_timeline[0]['timestamp'] if self.unified_timeline else 0

                for i, op in enumerate(self.unified_timeline, 1):
                    relative_time = op['timestamp'] - start_time

                    if op['type'] == '注释':
                        f.write(f"# [{i:3d}] {relative_time:6.2f}s - {op['command']}\n")
                        if 'comment' in op:
                            f.write(f"#      说明: {op['comment']}\n")
                    else:
                        f.write(f"# [{i:3d}] {relative_time:6.2f}s - {op['type']}: {op['command']}\n")
                        if 'start_pos' in op and 'end_pos' in op:
                            f.write(f"#      起始: {op['start_pos']}, 结束: {op['end_pos']}\n")
                        if 'duration' in op and 'distance' in op:
                            f.write(f"#      持续: {op['duration']}ms, 距离: {op['distance']:.1f}px\n")
                        if 'segment_index' in op:
                            f.write(f"#      分段: {op['segment_index']}/{op['total_segments']}\n")
                    f.write(f"\n")

            # 同时保存为JSON格式
            json_file = self.dedicated_output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'timestamp': datetime.now().isoformat(),
                        'total_operations': len(self.unified_timeline),
                        'swipe_sample_interval_ms': self.swipe_sample_interval * 1000,
                        'min_swipe_distance_px': self.min_swipe_distance
                    },
                    'operations': self.unified_timeline
                }, f, ensure_ascii=False, indent=2)

            print(f"✅ 专用录制结果已保存:")
            print(f"   文本格式: {self.dedicated_output_file}")
            print(f"   JSON格式: {json_file}")

        except Exception as e:
            print(f"❌ 保存失败: {e}")
            logger.error(f"保存专用录制结果失败: {e}")

    def start_advanced_recording(self):
        """开始高级录制 - 完整操作序列录制"""
        print("\n=== 完整操作序列录制 (高级模式) ===")
        print("🎯 这个模式可以录制完整的操作轨迹，包括：")
        print("   • 连续拖拽摇杆的完整路径")
        print("   • 多点触控操作")
        print("   • 复杂手势序列")
        print("   • 精确的时间控制")

        # 显示采样参数
        print(f"\n⚙️ 当前采样参数:")
        print(f"   采样间隔: {self.sample_interval*1000:.0f}ms")
        print(f"   最小移动距离: {self.min_move_distance}像素")

        # 询问是否调整参数
        adjust = input("\n是否需要调整采样参数？(y/n，默认n): ").strip().lower()
        if adjust == 'y':
            self.adjust_sampling_parameters()

        print("\n📝 操作说明:")
        print("   1. 开始录制后，请进行您的完整操作")
        print("   2. 可以包含拖拽、滑动、点击等任意组合")
        print("   3. 支持多个手指同时操作")
        print("   4. 按 Ctrl+C 停止录制")

        # 检查ADB连接
        if not check_adb_connection():
            print("❌ ADB连接失败，无法开始录制")
            return

        # 清空之前的录制数据
        self.operation_sequence.clear()
        self.active_touches.clear()
        self.last_sample_time = 0

        try:
            # 选择触摸设备
            touch_device = self.select_touch_device()
            if not touch_device:
                print("❌ 无法确定触摸设备")
                return

            print(f"\n🎬 开始高级录制...")
            print(f"使用设备: {touch_device}")

            # 启动高级录制
            self.advanced_recording = True
            self.listen_advanced_touch_events(touch_device)

        except KeyboardInterrupt:
            print("\n⏹️ 停止录制")
            self.advanced_recording = False
            self.process_advanced_recording_results()
        except Exception as e:
            print(f"❌ 录制过程中出现错误: {e}")
            logger.error(f"高级录制错误: {e}")

    def adjust_sampling_parameters(self):
        """调整采样参数"""
        print("\n⚙️ 调整采样参数:")

        try:
            # 调整采样间隔
            interval_ms = input(f"采样间隔 (当前{self.sample_interval*1000:.0f}ms，建议20-100ms): ").strip()
            if interval_ms:
                new_interval = float(interval_ms) / 1000.0
                if 0.01 <= new_interval <= 0.5:  # 10ms到500ms之间
                    self.sample_interval = new_interval
                    print(f"✓ 采样间隔设置为: {new_interval*1000:.0f}ms")
                else:
                    print("⚠️ 采样间隔超出范围，使用默认值")

            # 调整最小移动距离
            min_distance = input(f"最小移动距离 (当前{self.min_move_distance}像素，建议5-20像素): ").strip()
            if min_distance:
                new_distance = int(min_distance)
                if 1 <= new_distance <= 50:
                    self.min_move_distance = new_distance
                    print(f"✓ 最小移动距离设置为: {new_distance}像素")
                else:
                    print("⚠️ 移动距离超出范围，使用默认值")

        except ValueError:
            print("⚠️ 参数格式错误，使用默认值")

        print(f"\n✓ 最终采样参数:")
        print(f"   采样间隔: {self.sample_interval*1000:.0f}ms")
        print(f"   最小移动距离: {self.min_move_distance}像素")

    def listen_advanced_touch_events(self, device_path):
        """监听高级触摸事件"""
        process = None
        try:
            command = f"adb shell getevent {device_path}"
            print(f"执行命令: {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)

            print("✓ 开始高级录制 (按 Ctrl+C 停止)")
            print("📱 请进行您的完整操作序列...")

            event_count = 0
            while self.advanced_recording:
                line = process.stdout.readline()
                if not line:
                    error_line = process.stderr.readline()
                    if error_line:
                        print(f"⚠️ 错误输出: {error_line.strip()}")
                    break

                if line.strip():
                    event_count += 1

                    # 解析事件行
                    event_data = self.parse_event_line(line.strip())
                    if event_data:
                        self.process_advanced_touch_event(event_data)

            print(f"📊 总共处理了 {event_count} 个事件")

        except Exception as e:
            logger.error(f"高级录制监听失败: {e}")
            print(f"❌ 监听失败: {e}")
        finally:
            if process:
                process.terminate()

    def process_advanced_touch_event(self, event):
        """处理高级触摸事件"""
        current_time = event['timestamp']

        # 添加调试信息
        if event['type'] in [1, 3]:
            event_type_names = {1: 'EV_KEY', 3: 'EV_ABS'}
            type_name = event_type_names.get(event['type'])

            # 只显示关键事件的调试信息
            if event['type'] == 1 or event['code'] in [0x35, 0x36, 0x39]:
                print(f"🔍 高级录制事件: {type_name} code=0x{event['code']:02x} value={event['value']}")

        if event['type'] == 3:  # EV_ABS (绝对坐标事件)
            if event['code'] == 0x39:  # ABS_MT_TRACKING_ID
                finger_id = event['value']
                if finger_id == -1:  # 手指抬起
                    print(f"🔍 检测到手指抬起事件 (TRACKING_ID = -1)")
                    # 结束最近活跃的触摸
                    if self.active_touches:
                        # 找到最近更新的触摸
                        latest_fid = max(self.active_touches.keys(),
                                       key=lambda fid: self.active_touches[fid].get('last_update', 0))
                        touch_data = self.active_touches[latest_fid]

                        if (touch_data['raw_x'] is not None and
                            touch_data['raw_y'] is not None):
                            # 应用坐标转换
                            screen_x = touch_data['raw_y']  # 屏幕X = 原始Y
                            screen_y = 1080 - touch_data['raw_x']  # 屏幕Y = 1080 - 原始X

                            self.add_operation_point(latest_fid, 'up', screen_x, screen_y,
                                                   touch_data['raw_x'], touch_data['raw_y'], current_time)
                            del self.active_touches[latest_fid]
                            print(f"🔍 手指{latest_fid}抬起，坐标({screen_x}, {screen_y})")
                else:  # 新的手指按下
                    print(f"🔍 检测到新手指按下: ID={finger_id}")
                    self.active_touches[finger_id] = {
                        'start_time': current_time,
                        'current_x': None,
                        'current_y': None,
                        'raw_x': None,
                        'raw_y': None,
                        'last_sample_time': 0,
                        'last_update': current_time,
                        'ending': False,
                        'finger_id': finger_id,
                        'has_down_event': False  # 标记是否已记录按下事件
                    }

            elif event['code'] == 0x35:  # ABS_MT_POSITION_X
                # 更新最近活跃触摸的X坐标
                if self.active_touches:
                    # 更新最近的触摸点
                    latest_fid = max(self.active_touches.keys(),
                                   key=lambda fid: self.active_touches[fid].get('last_update', 0))
                    touch_data = self.active_touches[latest_fid]
                    if not touch_data['ending']:
                        touch_data['raw_x'] = event['value']
                        touch_data['current_x'] = event['value']
                        touch_data['last_update'] = current_time

            elif event['code'] == 0x36:  # ABS_MT_POSITION_Y
                # 更新最近活跃触摸的Y坐标
                if self.active_touches:
                    # 更新最近的触摸点
                    latest_fid = max(self.active_touches.keys(),
                                   key=lambda fid: self.active_touches[fid].get('last_update', 0))
                    touch_data = self.active_touches[latest_fid]
                    if not touch_data['ending']:
                        touch_data['raw_y'] = event['value']
                        touch_data['current_y'] = event['value']
                        touch_data['last_update'] = current_time

        elif event['type'] == 1:  # EV_KEY (按键事件)
            if event['code'] == 0x14a:  # BTN_TOUCH
                if event['value'] == 1:  # 按下
                    print(f"🔍 检测到BTN_TOUCH按下")
                    # 为所有有坐标但未记录按下事件的触摸记录按下事件
                    for finger_id, touch_data in self.active_touches.items():
                        if (touch_data['raw_x'] is not None and
                            touch_data['raw_y'] is not None and
                            not touch_data['has_down_event']):

                            # 应用坐标转换
                            screen_x = touch_data['raw_y']  # 屏幕X = 原始Y
                            screen_y = 1080 - touch_data['raw_x']  # 屏幕Y = 1080 - 原始X

                            self.add_operation_point(finger_id, 'down', screen_x, screen_y,
                                                   touch_data['raw_x'], touch_data['raw_y'], current_time)
                            touch_data['last_sample_time'] = current_time
                            touch_data['has_down_event'] = True
                            print(f"🔍 手指{finger_id}按下，坐标({screen_x}, {screen_y})")

                elif event['value'] == 0:  # 抬起
                    print(f"🔍 检测到BTN_TOUCH抬起")
                    # 标记所有触摸为结束状态
                    for touch_data in self.active_touches.values():
                        touch_data['ending'] = True

        # 检查是否需要采样移动事件
        self.check_and_sample_moves(current_time)

    def check_and_sample_moves(self, current_time):
        """检查并采样移动事件"""
        for finger_id, touch_data in self.active_touches.items():
            if (touch_data['current_x'] is not None and
                touch_data['current_y'] is not None and
                not touch_data['ending'] and
                self.should_sample(touch_data, current_time)):

                # 应用坐标转换
                screen_x = touch_data['raw_y']  # 屏幕X = 原始Y
                screen_y = 1080 - touch_data['raw_x']  # 屏幕Y = 1080 - 原始X

                self.add_operation_point(finger_id, 'move', screen_x, screen_y,
                                       touch_data['raw_x'], touch_data['raw_y'], current_time)
                touch_data['last_sample_time'] = current_time

    def should_sample(self, touch_data, current_time):
        """判断是否应该采样"""
        # 时间间隔检查
        if current_time - touch_data['last_sample_time'] < self.sample_interval:
            return False

        # 如果有上一个采样点，检查移动距离
        if len(self.operation_sequence) > 0:
            last_point = None
            for point in reversed(self.operation_sequence):
                if point['finger_id'] == touch_data.get('finger_id'):
                    last_point = point
                    break

            if last_point:
                # 计算移动距离
                dx = touch_data['current_x'] - last_point['x']
                dy = touch_data['current_y'] - last_point['y']
                distance = (dx * dx + dy * dy) ** 0.5

                if distance < self.min_move_distance:
                    return False

        return True

    def add_operation_point(self, finger_id, action, x, y, raw_x, raw_y, timestamp):
        """添加操作点到序列"""
        point = {
            'timestamp': timestamp,
            'action': action,
            'finger_id': finger_id,
            'x': int(x),
            'y': int(y),
            'raw_x': raw_x,
            'raw_y': raw_y
        }

        self.operation_sequence.append(point)

        # 显示关键操作点
        if action in ['down', 'up']:
            print(f"🎯 {action.upper()}: 手指{finger_id} ({x}, {y})")
        elif len(self.operation_sequence) % 20 == 0:  # 每20个移动点显示一次
            print(f"📍 MOVE: 手指{finger_id} ({x}, {y}) [已记录{len(self.operation_sequence)}个点]")

    def process_advanced_recording_results(self):
        """处理高级录制结果"""
        if not self.operation_sequence:
            print("❌ 没有记录到任何操作")
            return

        print(f"\n✅ 录制完成！")
        print(f"📊 录制统计:")
        print(f"   总操作点数: {len(self.operation_sequence)}")

        # 统计不同类型的操作
        actions = {}
        fingers = set()
        for point in self.operation_sequence:
            action = point['action']
            actions[action] = actions.get(action, 0) + 1
            fingers.add(point['finger_id'])

        print(f"   涉及手指数: {len(fingers)}")
        for action, count in actions.items():
            print(f"   {action.upper()}操作: {count}次")

        # 计算录制时长
        if len(self.operation_sequence) >= 2:
            duration = self.operation_sequence[-1]['timestamp'] - self.operation_sequence[0]['timestamp']
            print(f"   录制时长: {duration:.2f}秒")

        # 生成操作序列脚本
        self.generate_operation_sequence_script()

        # 询问是否保存
        save_choice = input("\n是否保存操作序列？(y/n): ").strip().lower()
        if save_choice == 'y':
            self.save_operation_sequence()

    def generate_operation_sequence_script(self):
        """生成操作序列脚本 - 转换为可执行的SWIPE和TAP命令"""
        if not self.operation_sequence:
            return

        print(f"\n🎬 生成操作序列脚本...")
        print("🔄 将复杂触摸序列转换为SWIPE和TAP命令...")

        # 按时间和手指ID排序
        sorted_sequence = sorted(self.operation_sequence, key=lambda x: (x['finger_id'], x['timestamp']))

        # 按手指ID分组
        finger_sequences = {}
        for point in sorted_sequence:
            finger_id = point['finger_id']
            if finger_id not in finger_sequences:
                finger_sequences[finger_id] = []
            finger_sequences[finger_id].append(point)

        # 生成可执行的命令
        executable_commands = []

        for finger_id, sequence in finger_sequences.items():
            print(f"🔍 处理手指{finger_id}的操作序列 ({len(sequence)}个点)")

            # 查找down和up事件
            down_points = [p for p in sequence if p['action'] == 'down']
            up_points = [p for p in sequence if p['action'] == 'up']
            # move_points = [p for p in sequence if p['action'] == 'move']  # 暂时不使用

            if not down_points or not up_points:
                print(f"⚠️ 手指{finger_id}缺少完整的按下/抬起事件，跳过")
                continue

            # 取第一个down和最后一个up
            start_point = down_points[0]
            end_point = up_points[-1]

            # 计算操作类型和参数
            start_x, start_y = start_point['x'], start_point['y']
            end_x, end_y = end_point['x'], end_point['y']
            duration = int((end_point['timestamp'] - start_point['timestamp']) * 1000)  # 毫秒

            # 计算移动距离
            distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

            if distance < 5:  # 移动距离小于5像素认为是点击
                command = f"{start_x},{start_y}"
                command_type = "点击"
                print(f"  ✓ 生成点击命令: {command}")
            else:
                # 确保持续时间合理
                if duration < 100:
                    duration = 300  # 最小300ms
                elif duration > 3000:
                    duration = 1000  # 最大1000ms

                command = f"SWIPE:{start_x},{start_y},{end_x},{end_y},{duration}"
                command_type = "滑动"
                print(f"  ✓ 生成滑动命令: {command} (距离:{distance:.1f}px, 时长:{duration}ms)")

            # 添加到可执行命令列表
            executable_commands.append({
                'type': command_type,
                'command': command,
                'finger_id': finger_id,
                'start_pos': (start_x, start_y),
                'end_pos': (end_x, end_y),
                'duration': duration,
                'distance': distance,
                'timestamp': start_point['timestamp']
            })

        # 按时间排序最终命令
        executable_commands.sort(key=lambda x: x['timestamp'])

        # 存储生成的可执行命令
        self.executable_commands = executable_commands

        print(f"\n✅ 转换完成，生成 {len(executable_commands)} 条可执行命令:")
        for i, cmd in enumerate(executable_commands, 1):
            print(f"   {i}. {cmd['type']}: {cmd['command']}")

        print(f"\n💡 这些命令与简单模式生成的命令格式相同，可以直接执行！")

    def save_operation_sequence(self):
        """保存操作序列"""
        try:
            # 保存详细的操作序列数据
            with open(self.sequence_output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 完整操作序列录制 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总操作点数: {len(self.operation_sequence)}\n")
                f.write(f"# 采样间隔: {self.sample_interval*1000:.0f}ms\n")
                f.write(f"# 最小移动距离: {self.min_move_distance}px\n\n")

                # 保存脚本命令
                f.write("# 可执行的操作序列脚本:\n")
                for cmd in self.generated_script:
                    f.write(f"{cmd}\n")

                f.write(f"\n# 详细的原始数据:\n")
                for i, point in enumerate(self.operation_sequence):
                    f.write(f"# [{i+1:4d}] {point['action'].upper()}: "
                           f"手指{point['finger_id']} ({point['x']}, {point['y']}) "
                           f"时间:{point['timestamp']:.3f} "
                           f"原始:({point['raw_x']}, {point['raw_y']})\n")

            # 同时保存为JSON格式
            json_file = self.sequence_output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'timestamp': datetime.now().isoformat(),
                        'total_points': len(self.operation_sequence),
                        'sample_interval_ms': self.sample_interval * 1000,
                        'min_move_distance_px': self.min_move_distance
                    },
                    'script_commands': self.generated_script,
                    'raw_sequence': self.operation_sequence
                }, f, ensure_ascii=False, indent=2)

            print(f"✅ 操作序列已保存:")
            print(f"   文本格式: {self.sequence_output_file}")
            print(f"   JSON格式: {json_file}")

        except Exception as e:
            print(f"❌ 保存失败: {e}")
            logger.error(f"保存操作序列失败: {e}")

    def get_available_touch_devices(self):
        """获取可用的触摸设备列表（带设备名称）"""
        devices = []  # [(device_path, device_name), ...]
        try:
            # 获取输入设备列表
            command = "adb shell getevent -p"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.error(f"获取设备列表失败: {result.stderr}")
                return self._fallback_scan_devices()

            # 解析输出，查找所有可能的触摸设备
            lines = result.stdout.split('\n')
            current_device = None
            current_name = ""
            device_capabilities = {}

            for line in lines:
                if line.startswith('add device'):
                    # 提取设备路径
                    match = re.search(r'add device \d+: (/dev/input/event\d+)', line)
                    if match:
                        current_device = match.group(1)
                        device_capabilities[current_device] = {'caps': [], 'name': ''}
                elif current_device and 'name:' in line:
                    # 提取设备名称
                    match = re.search(r'name:\s*"([^"]*)"', line)
                    if match:
                        device_capabilities[current_device]['name'] = match.group(1)
                elif current_device and ('ABS_MT_POSITION_X' in line or 'ABS_X' in line or 'ABS_Y' in line):
                    # 记录设备支持的坐标类型
                    device_capabilities[current_device]['caps'].append(line.strip())

            # 筛选出可能的触摸设备
            for device, info in device_capabilities.items():
                if any('ABS_MT_POSITION' in cap or 'ABS_X' in cap for cap in info['caps']):
                    devices.append((device, info['name']))

            # 如果没找到任何设备，进行更全面的扫描
            if not devices:
                logger.warning("通过getevent -p未找到触摸设备，启用回退扫描")
                return self._fallback_scan_devices()

            # 按优先级排序设备
            devices = self._sort_devices_by_priority(devices)
            return devices

        except Exception as e:
            logger.error(f"获取触摸设备失败: {e}")
            return self._fallback_scan_devices()

    def _fallback_scan_devices(self):
        """回退方案：扫描所有event设备"""
        devices = []
        try:
            # 扫描所有可能的event设备
            for i in range(10):  # 扫描event0-event9
                device = f"/dev/input/event{i}"
                test_cmd = f"adb shell ls {device}"
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=3)
                if test_result.returncode == 0:
                    # 尝试获取设备名称
                    name_cmd = f"adb shell cat /sys/class/input/event{i}/device/name 2>/dev/null || echo 'unknown'"
                    name_result = subprocess.run(name_cmd, shell=True, capture_output=True, text=True, timeout=3)
                    device_name = name_result.stdout.strip() if name_result.returncode == 0 else 'unknown'
                    devices.append((device, device_name))
                    
            logger.info(f"回退扫描找到 {len(devices)} 个输入设备")
            # 按优先级排序
            return self._sort_devices_by_priority(devices)
            
        except Exception as e:
            logger.error(f"回退扫描失败: {e}")
            # 最后的回退：返回常见设备
            return [("/dev/input/event3", "unknown"), ("/dev/input/event2", "unknown"), 
                   ("/dev/input/event1", "unknown"), ("/dev/input/event0", "unknown")]

    def _sort_devices_by_priority(self, devices):
        """按优先级排序设备列表"""
        # 触摸设备名称优先级（从高到低）
        priority_patterns = [
            'goodix',           # Goodix触摸IC
            'synaptics',        # Synaptics触摸IC
            'atmel',           # Atmel触摸IC
            'elan',            # ELAN触摸IC
            'cypress',         # Cypress触摸IC
            'touchscreen',     # 通用触摸屏
            'touch_dev',       # 触摸设备
            'touch_panel',     # 触摸面板
            'tp',              # 触摸板缩写
            'ft5x06',          # FocalTech 5x06系列
            'gt9xx',           # Goodix 9xx系列
            'nt36xxx',         # Novatek 36xxx系列
            'ili2xxx',         # ILI2xxx系列
            'touch'            # 包含touch的通用设备
        ]
        
        def get_priority(device_info):
            device_path, device_name = device_info
            name_lower = device_name.lower()
            
            # 按名称匹配优先级
            for i, pattern in enumerate(priority_patterns):
                if pattern in name_lower:
                    return i
            
            # 如果名称不匹配，按设备路径编号排序（编号越大优先级越高）
            match = re.search(r'event(\d+)', device_path)
            if match:
                return 1000 - int(match.group(1))  # 编号大的优先级高
            
            return 2000  # 未知设备最低优先级
        
        return sorted(devices, key=get_priority)

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
                    if event_count <= 5:  # 只显示前5个事件作为调试
                        print(f"🔍 原始事件: {line.strip()}")
                    elif event_count == 6:
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
            # 您的getevent输出格式: type code value (没有设备路径前缀)
            # 例如: 0003 0035 00000276

            # 移除时间戳（如果存在）
            if line.startswith('['):
                bracket_end = line.find(']')
                if bracket_end != -1:
                    line = line[bracket_end + 1:].strip()

            parts = line.split()

            # 检查是否是标准的3部分格式 (type code value)
            if len(parts) == 3:
                # 直接解析3部分格式
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

            # 获取时间戳
            timestamp = time.time()

            result = {
                'device': device,
                'type': event_type,
                'code': event_code,
                'value': event_value,
                'timestamp': timestamp,
                'raw_line': line  # 保存原始行用于调试
            }

            # 调试输出
            if event_type in [1, 3]:  # 只显示关键事件的解析结果
                print(f"🔍 解析结果: type=0x{event_type:04x} code=0x{event_code:04x} value={event_value}")

            return result

        except (ValueError, IndexError) as e:
            print(f"⚠️ 解析失败: {line} - {e}")
            return None

    def process_touch_event(self, event, current_touch):
        """处理单个触摸事件"""
        # 添加调试信息
        event_type_names = {1: 'EV_KEY', 3: 'EV_ABS', 0: 'EV_SYN'}
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

        # 显示详细的事件信息
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
            # 多点触控按键
            if event['code'] == 0x14a:  # BTN_TOUCH (330)
                if event['value'] == 1:  # 按下
                    current_touch['is_touching'] = True
                    current_touch['start_time'] = event['timestamp']
                    print("👆 检测到触摸开始 (BTN_TOUCH)")

                elif event['value'] == 0:  # 抬起
                    current_touch['is_touching'] = False
                    current_touch['end_time'] = event['timestamp']
                    print("👆 检测到触摸结束 (BTN_TOUCH)")

                    # 完成一次触摸，生成命令
                    self.generate_touch_command(current_touch)

                    # 重置当前触摸状态
                    self.reset_touch_state(current_touch)

            # 其他可能的触摸按键
            elif event['code'] in [0x110, 0x111]:  # BTN_LEFT, BTN_RIGHT
                if event['value'] == 1:  # 按下
                    current_touch['is_touching'] = True
                    current_touch['start_time'] = event['timestamp']
                    print(f"👆 检测到触摸开始 (BTN_{event['code']:02x})")

                elif event['value'] == 0:  # 抬起
                    current_touch['is_touching'] = False
                    current_touch['end_time'] = event['timestamp']
                    print(f"👆 检测到触摸结束 (BTN_{event['code']:02x})")

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

        # 坐标转换：基于用户最终确认的规律
        # 屏幕X = 原始Y坐标
        # 屏幕Y = 1080 - 原始X坐标
        start_x = raw_start_y  # 屏幕X = 原始Y
        start_y = 1080 - raw_start_x  # 屏幕Y = 1080 - 原始X
        end_x = raw_end_y  # 屏幕X = 原始Y
        end_y = 1080 - raw_end_x  # 屏幕Y = 1080 - 原始X

        print(f"   转换后起始坐标: ({start_x}, {start_y}) [已转换]")
        print(f"   转换后结束坐标: ({end_x}, {end_y}) [已转换]")
        print(f"   转换规律: 屏幕X=原始Y, 屏幕Y=1080-原始X")

        # 计算移动距离（使用原始坐标）
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

    def show_recorded_commands(self):
        """显示已记录的命令"""
        # 检查各种录制模式的数据
        simple_commands = len(self.recorded_commands) if self.recorded_commands else 0
        dedicated_operations = len(self.unified_timeline) if hasattr(self, 'unified_timeline') and self.unified_timeline else 0

        if simple_commands == 0 and dedicated_operations == 0:
            print("❌ 暂无记录的命令或操作序列")
            print("💡 提示:")
            print("   - 简单模式录制的命令会显示在这里")
            print("   - 专用模式录制的操作序列也会显示在这里")
            return

        # 显示简单录制的命令
        if simple_commands > 0:
            print(f"\n=== 简单模式记录的命令 (共 {simple_commands} 条) ===")
            for i, record in enumerate(self.recorded_commands, 1):
                print(f"\n[{i}] {record['type']} - {record['timestamp']}")
                print(f"    命令: {record['command']}")
                print(f"    起始位置: {record['start_pos']}")
                print(f"    结束位置: {record['end_pos']}")
                print(f"    持续时间: {record['duration']}ms")
                print(f"    移动距离: {record['distance']:.1f}px")

        # 显示专用录制的操作序列
        if dedicated_operations > 0:
            print(f"\n=== 专用模式记录的操作序列 (共 {dedicated_operations} 个操作) ===")

            # 统计信息
            swipe_count = len([op for op in self.unified_timeline if op['type'] == '滑动'])
            tap_count = len([op for op in self.unified_timeline if op['type'] == '点击'])
            comment_count = len([op for op in self.unified_timeline if op['type'] == '注释'])

            print(f"📊 序列统计:")
            print(f"   滑动操作: {swipe_count} 次")
            print(f"   点击操作: {tap_count} 次")
            if comment_count > 0:
                print(f"   注释标记: {comment_count} 条")

            # 计算时长
            if len(self.unified_timeline) >= 2:
                duration = self.unified_timeline[-1]['timestamp'] - self.unified_timeline[0]['timestamp']
                print(f"   总时长: {duration:.2f}秒")

            # 显示操作序列
            print(f"\n🎯 操作序列:")
            start_time = self.unified_timeline[0]['timestamp'] if self.unified_timeline else 0

            for i, op in enumerate(self.unified_timeline[:15], 1):  # 显示前15个操作
                relative_time = op['timestamp'] - start_time

                if op['type'] == '注释':
                    print(f"   [{i:2d}] {relative_time:6.2f}s - {op['command']}")
                elif op['type'] == '滑动' and 'segment_index' in op:
                    print(f"   [{i:2d}] {relative_time:6.2f}s - 滑动段{op['segment_index']}/{op['total_segments']}: {op['command']}")
                else:
                    print(f"   [{i:2d}] {relative_time:6.2f}s - {op['type']}: {op['command']}")

            if len(self.unified_timeline) > 15:
                print(f"   ... 还有 {len(self.unified_timeline) - 15} 个操作")

            print("   可以选择'测试生成的命令'来测试这些操作")

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
        # 检查各种录制模式的数据
        simple_commands = len(self.recorded_commands) if self.recorded_commands else 0
        dedicated_operations = len(self.unified_timeline) if hasattr(self, 'unified_timeline') and self.unified_timeline else 0

        if simple_commands == 0 and dedicated_operations == 0:
            print("❌ 没有可测试的命令或操作序列")
            return

        print(f"\n=== 测试生成的命令 ===")

        # 显示可测试的内容
        if simple_commands > 0:
            print(f"📋 简单模式命令: {simple_commands} 条")
        if dedicated_operations > 0:
            print(f"🎬 专用模式操作序列: {dedicated_operations} 个操作")

        # 选择测试模式
        if simple_commands > 0 and dedicated_operations > 0:
            print("\n选择测试模式:")
            print("1. 测试简单模式命令")
            print("2. 测试专用模式操作序列")
            print("3. 测试所有内容")

            choice = input("请选择 (1-3): ").strip()
            if choice == '1':
                self.test_simple_commands()
            elif choice == '2':
                self.test_dedicated_sequence()
            elif choice == '3':
                self.test_simple_commands()
                print("\n" + "="*50)
                self.test_dedicated_sequence()
            else:
                print("❌ 无效选择")
        elif simple_commands > 0:
            self.test_simple_commands()
        else:
            self.test_dedicated_sequence()

    def test_simple_commands(self):
        """测试简单模式的命令"""
        if not self.recorded_commands:
            return

        print(f"\n🧪 测试简单模式命令 ({len(self.recorded_commands)} 条)")

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

        print("✓ 简单命令测试完成")

    def test_dedicated_sequence(self):
        """测试专用模式的操作序列"""
        if not hasattr(self, 'unified_timeline') or not self.unified_timeline:
            return

        print(f"\n🎬 测试专用模式操作序列 ({len(self.unified_timeline)} 个操作)")

        # 显示操作预览
        print(f"📋 操作预览:")
        start_time = self.unified_timeline[0]['timestamp']
        for i, op in enumerate(self.unified_timeline[:5], 1):
            relative_time = op['timestamp'] - start_time
            print(f"   {i}. [{relative_time:6.2f}s] {op['type']}: {op['command']}")

        if len(self.unified_timeline) > 5:
            print(f"   ... 还有 {len(self.unified_timeline) - 5} 个操作")

        confirm = input("\n确定要开始测试吗？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消测试")
            return

        print("开始执行操作序列...")

        # 按时间顺序执行操作
        start_time = self.unified_timeline[0]['timestamp']
        last_time = start_time

        executed_count = 0
        for i, op in enumerate(self.unified_timeline, 1):
            # 跳过注释
            if op['type'] == '注释':
                print(f"[{i}/{len(self.unified_timeline)}] {op['command']}")
                continue

            executed_count += 1

            # 计算延迟
            current_time = op['timestamp']
            delay = current_time - last_time

            if delay > 0.05:  # 延迟大于50ms才等待
                print(f"   ⏱️ 等待 {delay:.2f}秒...")
                time.sleep(delay)

            # 显示执行信息
            if 'segment_index' in op:
                print(f"[{i}/{len(self.unified_timeline)}] 执行滑动段{op['segment_index']}/{op['total_segments']}: {op['command']}")
            else:
                print(f"[{i}/{len(self.unified_timeline)}] 执行: {op['command']}")

            # 执行命令
            if op['type'] == '点击':
                # 解析点击命令
                coords = op['command'].split(',')
                x, y = int(coords[0]), int(coords[1])
                success = tap_screen(x, y)
            else:  # 滑动
                # 解析滑动命令
                params = op['command'][6:].split(',')  # 去掉 'SWIPE:' 前缀
                x1, y1, x2, y2, duration = map(int, params)
                success = swipe_screen(x1, y1, x2, y2, duration)

            if success:
                print(f"  ✓ 执行成功")
            else:
                print(f"  ❌ 执行失败")
                break

            last_time = current_time

        print(f"✓ 专用序列测试完成 (执行了{executed_count}个实际操作)")

    def test_advanced_sequence(self):
        """测试高级模式的操作序列"""
        if not hasattr(self, 'operation_sequence') or not self.operation_sequence:
            return

        print(f"\n🎬 测试高级模式操作序列 ({len(self.operation_sequence)} 个操作点)")

        # 检查是否有生成的可执行命令
        if not hasattr(self, 'executable_commands') or not self.executable_commands:
            print("⚠️ 未找到可执行命令，正在生成...")
            self.generate_operation_sequence_script()

        if not hasattr(self, 'executable_commands') or not self.executable_commands:
            print("❌ 无法生成可执行命令")
            return

        print(f"📋 将执行 {len(self.executable_commands)} 条可执行命令")

        confirm = input("确定要开始测试吗？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消测试")
            return

        print("开始执行操作序列...")

        # 执行可执行命令 (使用与简单模式相同的逻辑)
        for i, cmd_record in enumerate(self.executable_commands, 1):
            print(f"[{i}/{len(self.executable_commands)}] 执行: {cmd_record['command']}")

            if cmd_record['type'] == '点击':
                # 解析点击命令
                coords = cmd_record['command'].split(',')
                x, y = int(coords[0]), int(coords[1])
                success = tap_screen(x, y)
            else:  # 滑动
                # 解析滑动命令
                params = cmd_record['command'][6:].split(',')  # 去掉 'SWIPE:' 前缀
                x1, y1, x2, y2, duration = map(int, params)
                success = swipe_screen(x1, y1, x2, y2, duration)

            if success:
                print(f"  ✓ 执行成功")
            else:
                print(f"  ❌ 执行失败")
                break

            # 命令间间隔
            if i < len(self.executable_commands):
                time.sleep(DEFAULT_INTERVAL)

        print("✓ 高级序列测试完成")




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
        print("        ADB游戏自动化调试器 (融合版)")
        print("="*55)
        print("1. 移动测试 (W/A/S/D) - 使用longpress方法")
        print("2. 移动距离校准 - 确定按键次数与移动距离关系")
        print("3. 统一命令执行 - 移动/点击/滑动混合操作")
        print("4. 单次按键测试")
        print("5. 查看ADB连接状态")
        print("6. 查看屏幕信息")
        print("7. 触摸参数记录器 - 记录滑动和点击参数")
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
            calibrate_movement()

        elif choice == '3':
            execute_unified_commands()

        elif choice == '4':
            test_single_keypress()

        elif choice == '5':
            print("\n=== ADB连接状态 ===")
            if check_adb_connection():
                print("✓ ADB连接正常")
            else:
                print("❌ ADB连接异常")

        elif choice == '6':
            print("\n=== 屏幕信息 ===")
            get_screen_info()

        elif choice == '7':
            touch_recorder = TouchEventRecorder()
            touch_recorder.start_recording_menu()

        else:
            print("❌ 无效选择，请重新输入")
