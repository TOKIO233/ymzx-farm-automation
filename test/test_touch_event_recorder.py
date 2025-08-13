#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TouchEventRecorder类单元测试
测试触摸事件记录器的依赖注入和ADB接口使用
"""

import unittest
from unittest.mock import Mock, patch, call
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from move_debugger import TouchEventRecorder, DeviceState, ADBExecutor


class TestTouchEventRecorder(unittest.TestCase):
    """TouchEventRecorder类单元测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建mock的DeviceState
        self.mock_device_state = Mock(spec=DeviceState)
        self.mock_device_state.is_valid = True
        self.mock_device_state.screen_width = 1080
        self.mock_device_state.screen_height = 1920
        self.mock_device_state.screen_orientation = 1  # 添加屏幕方向
        self.mock_device_state.touch_device = {
            'device': '/dev/input/event2',
            'max_x': 4095,
            'max_y': 4095
        }
        
        # 创建mock的ADBExecutor
        self.mock_adb_executor = Mock(spec=ADBExecutor)
        self.mock_adb_executor.tap_screen.return_value = True
        self.mock_adb_executor.swipe_screen.return_value = True
        
    def test_init_valid_dependencies(self):
        """测试有效依赖注入的初始化"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        self.assertEqual(recorder.device_state, self.mock_device_state)
        self.assertEqual(recorder.adb_executor, self.mock_adb_executor)
        self.assertFalse(recorder.recording)
        self.assertEqual(recorder.recorded_commands, [])
        self.assertEqual(recorder.output_file, "touch_commands.txt")
        self.assertEqual(recorder.working_touch_device, self.mock_device_state.touch_device)
        self.assertIsNone(recorder.process)
        
    def test_init_invalid_device_state(self):
        """测试无效DeviceState的初始化"""
        self.mock_device_state.is_valid = False
        
        with self.assertRaises(ValueError) as context:
            TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        self.assertIn("DeviceState必须已成功初始化", str(context.exception))
        
    def test_find_and_set_touch_device_success(self):
        """测试成功查找触摸设备"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        with patch('builtins.print') as mock_print:
            result = recorder.find_and_set_touch_device()
        
        self.assertEqual(result, '/dev/input/event2')
        self.assertEqual(recorder.working_touch_device, self.mock_device_state.touch_device)
        
        # 验证打印输出
        mock_print.assert_any_call("\n=== 查找触摸设备 ===")
        mock_print.assert_any_call("已设置工作触摸设备: /dev/input/event2")
        mock_print.assert_any_call("坐标范围 - X: 0-4095, Y: 0-4095")
        
    def test_find_and_set_touch_device_failure(self):
        """测试触摸设备查找失败"""
        self.mock_device_state.touch_device = None
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        with patch('builtins.print') as mock_print:
            result = recorder.find_and_set_touch_device()
        
        self.assertIsNone(result)
        mock_print.assert_any_call("❌ 设备状态中未找到可用的触摸设备")
        
    @patch('move_debugger.convert_touch_coordinates')
    @patch('move_debugger.datetime')
    def test_generate_touch_command_click(self, mock_datetime, mock_convert):
        """测试生成点击命令"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        # 设置mock返回值
        mock_convert.side_effect = [(540, 960), (542, 962)]  # 两次调用的返回值
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        
        touch_data = {
            'start_x': 2047, 'start_y': 2047,
            'end_x': 2049, 'end_y': 2049,
            'start_time': 1000.0, 'end_time': 1000.1
        }
        
        with patch('builtins.print') as mock_print:
            recorder.generate_touch_command(touch_data)
        
        # 验证命令生成
        self.assertEqual(len(recorder.recorded_commands), 1)
        command = recorder.recorded_commands[0]
        self.assertEqual(command['type'], '点击')
        self.assertEqual(command['command'], '540,960')
        self.assertEqual(command['start_pos'], (540, 960))
        self.assertEqual(command['end_pos'], (542, 962))
        self.assertEqual(command['distance'], ((542-540)**2 + (962-960)**2)**0.5)
        
        mock_print.assert_any_call("生成点击命令: 540,960")
        
    @patch('move_debugger.convert_touch_coordinates')
    @patch('move_debugger.datetime')
    def test_generate_touch_command_swipe(self, mock_datetime, mock_convert):
        """测试生成滑动命令"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        # 设置mock返回值 - 滑动距离大于20像素
        mock_convert.side_effect = [(100, 100), (200, 200)]
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        
        touch_data = {
            'start_x': 1000, 'start_y': 1000,
            'end_x': 2000, 'end_y': 2000,
            'start_time': 1000.0, 'end_time': 1000.5
        }
        
        with patch('builtins.print') as mock_print:
            recorder.generate_touch_command(touch_data)
        
        # 验证命令生成
        self.assertEqual(len(recorder.recorded_commands), 1)
        command = recorder.recorded_commands[0]
        self.assertEqual(command['type'], '滑动')
        self.assertEqual(command['command'], 'SWIPE:100,100,200,200,500')
        
        mock_print.assert_any_call("生成滑动命令: SWIPE:100,100,200,200,500")
        
    def test_generate_touch_command_missing_data(self):
        """测试缺少必需数据的命令生成"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        # 缺少end_y数据
        incomplete_touch_data = {
            'start_x': 100, 'start_y': 100,
            'end_x': 200,  # 缺少end_y
            'start_time': 1000.0, 'end_time': 1000.1
        }
        
        recorder.generate_touch_command(incomplete_touch_data)
        
        # 应该没有生成任何命令
        self.assertEqual(len(recorder.recorded_commands), 0)
        
    def test_generate_touch_command_no_screen_info(self):
        """测试屏幕信息缺失的命令生成"""
        self.mock_device_state.screen_width = None
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        touch_data = {
            'start_x': 100, 'start_y': 100,
            'end_x': 200, 'end_y': 200,
            'start_time': 1000.0, 'end_time': 1000.1
        }
        
        with patch('builtins.print') as mock_print:
            recorder.generate_touch_command(touch_data)
        
        # 应该没有生成任何命令
        self.assertEqual(len(recorder.recorded_commands), 0)
        mock_print.assert_any_call("❌ 无法获取屏幕或触摸设备信息，无法生成命令")
        
    @patch('builtins.input', side_effect=['y'])
    @patch('time.sleep')
    def test_test_generated_commands_click(self, mock_sleep, mock_input):
        """测试生成命令的执行 - 点击"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        # 添加一个点击命令
        recorder.recorded_commands.append({
            'type': '点击',
            'command': '540,960'
        })
        
        with patch('builtins.print') as mock_print:
            recorder.test_generated_commands()
        
        # 验证adb_executor被调用
        self.mock_adb_executor.tap_screen.assert_called_once_with(540, 960)
        mock_print.assert_any_call("[1/1] 执行: 540,960")
        mock_print.assert_any_call("命令测试完成")
        
    @patch('builtins.input', side_effect=['y'])
    @patch('time.sleep')
    def test_test_generated_commands_swipe(self, mock_sleep, mock_input):
        """测试生成命令的执行 - 滑动"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        # 添加一个滑动命令
        recorder.recorded_commands.append({
            'type': '滑动',
            'command': 'SWIPE:100,100,200,200,500'
        })
        
        with patch('builtins.print') as mock_print:
            recorder.test_generated_commands()
        
        # 验证adb_executor被调用
        self.mock_adb_executor.swipe_screen.assert_called_once_with(100, 100, 200, 200, 500)
        mock_print.assert_any_call("[1/1] 执行: SWIPE:100,100,200,200,500")
        
    @patch('builtins.input', side_effect=['n'])
    def test_test_generated_commands_cancelled(self, mock_input):
        """测试取消命令执行"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        recorder.recorded_commands.append({
            'type': '点击',
            'command': '540,960'
        })
        
        recorder.test_generated_commands()
        
        # 验证adb_executor没有被调用
        self.mock_adb_executor.tap_screen.assert_not_called()
        
    def test_test_generated_commands_empty(self):
        """测试空命令列表的执行"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        
        with patch('builtins.print') as mock_print:
            recorder.test_generated_commands()
        
        mock_print.assert_any_call("❌ 没有可测试的命令")
        
    @patch('builtins.input', side_effect=['y'])
    def test_test_generated_commands_execution_failure(self, mock_input):
        """测试命令执行失败"""
        recorder = TouchEventRecorder(self.mock_device_state, self.mock_adb_executor)
        self.mock_adb_executor.tap_screen.return_value = False  # 模拟执行失败
        
        recorder.recorded_commands.append({
            'type': '点击',
            'command': '540,960'
        })
        
        with patch('builtins.print') as mock_print:
            recorder.test_generated_commands()
        
        mock_print.assert_any_call("  ❌ 执行失败，测试中止")


if __name__ == '__main__':
    unittest.main()