"""
ADBExecutor类单元测试
测试ADB命令执行的核心功能，包括按键、点击、滑动操作
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock, Mock
import subprocess
import time

# 添加父目录到路径以导入主模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from move_debugger import ADBExecutor, DeviceState


class TestADBExecutor(unittest.TestCase):
    """ADBExecutor类的单元测试"""
    
    def setUp(self):
        """每个测试前的setup"""
        # 创建有效的DeviceState
        self.device_state = DeviceState()
        self.device_state.is_valid = True
        self.device_state.screen_width = 1080
        self.device_state.screen_height = 2340
        self.device_state.touch_device = {
            'device': '/dev/input/event1',
            'max_x': 4095,
            'max_y': 4095
        }
        
        # 创建ADBExecutor实例
        self.adb_executor = ADBExecutor(self.device_state)
    
    def test_init_with_valid_device_state(self):
        """测试使用有效DeviceState初始化"""
        executor = ADBExecutor(self.device_state)
        self.assertEqual(executor.device_state, self.device_state)
    
    def test_init_with_invalid_device_state(self):
        """测试使用无效DeviceState初始化应该抛出异常"""
        invalid_device_state = DeviceState()
        invalid_device_state.is_valid = False
        
        with self.assertRaises(ValueError) as context:
            ADBExecutor(invalid_device_state)
        self.assertIn("DeviceState必须已成功初始化", str(context.exception))
    
    @patch('subprocess.run')
    def test_run_adb_command_success(self, mock_run):
        """测试ADB命令执行成功"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.adb_executor._run_adb_command("input tap 100 200")
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ['adb', 'shell', 'input', 'tap', '100', '200'],
            capture_output=True,
            text=True,
            timeout=5
        )
    
    @patch('subprocess.run')
    def test_run_adb_command_failure(self, mock_run):
        """测试ADB命令执行失败"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "command failed"
        mock_run.return_value = mock_result
        
        result = self.adb_executor._run_adb_command("input tap 100 200")
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_run_adb_command_timeout(self, mock_run):
        """测试ADB命令超时"""
        mock_run.side_effect = subprocess.TimeoutExpired(['adb', 'shell', 'input'], 5)
        
        result = self.adb_executor._run_adb_command("input tap 100 200")
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_run_adb_command_custom_timeout(self, mock_run):
        """测试自定义超时时间"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        self.adb_executor._run_adb_command("input tap 100 200", timeout=10)
        
        mock_run.assert_called_once_with(
            ['adb', 'shell', 'input', 'tap', '100', '200'],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch.object(ADBExecutor, '_run_adb_command')
    @patch('time.sleep')
    def test_press_key_single(self, mock_sleep, mock_run_command):
        """测试单次按键操作"""
        mock_run_command.return_value = True
        
        result = self.adb_executor.press_key("51", 1, 0.5)
        
        self.assertTrue(result)
        mock_run_command.assert_called_once_with("input keyevent --longpress 51")
        mock_sleep.assert_not_called()  # 单次按键不需要延迟
    
    @patch.object(ADBExecutor, '_run_adb_command')
    @patch('time.sleep')
    def test_press_key_multiple(self, mock_sleep, mock_run_command):
        """测试多次按键操作"""
        mock_run_command.return_value = True
        
        result = self.adb_executor.press_key("51", 3, 0.2)
        
        self.assertTrue(result)
        self.assertEqual(mock_run_command.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # 3次按键，2次延迟
        mock_sleep.assert_called_with(0.2)
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_press_key_partial_failure(self, mock_run_command):
        """测试按键操作部分失败"""
        # 第一次成功，第二次失败
        mock_run_command.side_effect = [True, False]
        
        result = self.adb_executor.press_key("51", 2, 0.1)
        
        self.assertFalse(result)  # 不是全部成功，返回False
        self.assertEqual(mock_run_command.call_count, 2)
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_tap_screen_success(self, mock_run_command):
        """测试屏幕点击成功"""
        mock_run_command.return_value = True
        
        result = self.adb_executor.tap_screen(540, 960)
        
        self.assertTrue(result)
        mock_run_command.assert_called_once_with("input tap 540 960")
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_tap_screen_failure(self, mock_run_command):
        """测试屏幕点击失败"""
        mock_run_command.return_value = False
        
        result = self.adb_executor.tap_screen(540, 960)
        
        self.assertFalse(result)
        mock_run_command.assert_called_once_with("input tap 540 960")
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_swipe_screen_default_duration(self, mock_run_command):
        """测试屏幕滑动（默认持续时间）"""
        mock_run_command.return_value = True
        
        result = self.adb_executor.swipe_screen(100, 200, 300, 400)
        
        self.assertTrue(result)
        mock_run_command.assert_called_once_with("input swipe 100 200 300 400 500")
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_swipe_screen_custom_duration(self, mock_run_command):
        """测试屏幕滑动（自定义持续时间）"""
        mock_run_command.return_value = True
        
        result = self.adb_executor.swipe_screen(100, 200, 300, 400, 1000)
        
        self.assertTrue(result)
        mock_run_command.assert_called_once_with("input swipe 100 200 300 400 1000")
    
    @patch.object(ADBExecutor, '_run_adb_command')
    def test_swipe_screen_failure(self, mock_run_command):
        """测试屏幕滑动失败"""
        mock_run_command.return_value = False
        
        result = self.adb_executor.swipe_screen(100, 200, 300, 400)
        
        self.assertFalse(result)


class TestADBExecutorIntegration(unittest.TestCase):
    """ADBExecutor集成测试（需要真实ADB环境）"""
    
    def setUp(self):
        """集成测试setup"""
        # 创建真实的DeviceState（如果可能）
        self.device_state = DeviceState()
        
    @unittest.skipUnless(
        os.system('adb devices > /dev/null 2>&1') == 0, 
        "需要ADB环境和连接的设备"
    )
    def test_real_device_executor(self):
        """测试真实设备环境下的ADBExecutor（可选）"""
        # 首先初始化DeviceState
        if self.device_state.initialize_all():
            executor = ADBExecutor(self.device_state)
            
            # 测试一个安全的命令（获取设备信息）
            # 注意：这里不执行实际的点击，只测试命令构造
            self.assertIsNotNone(executor.device_state.screen_width)
            self.assertIsNotNone(executor.device_state.screen_height)
            print(f"真实设备ADBExecutor测试成功")
            print(f"  设备状态有效: {executor.device_state.is_valid}")
            print(f"  屏幕分辨率: {executor.device_state.screen_width}x{executor.device_state.screen_height}")


if __name__ == '__main__':
    # 创建测试套件
    unittest.main(verbosity=2)