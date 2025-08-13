"""
DeviceState类单元测试
测试设备状态管理的核心功能，包括ADB连接、屏幕信息获取、触摸设备查找
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock, Mock
import subprocess

# 添加父目录到路径以导入主模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from move_debugger import DeviceState


class TestDeviceState(unittest.TestCase):
    """DeviceState类的单元测试"""
    
    def setUp(self):
        """每个测试前的setup"""
        self.device_state = DeviceState()
    
    def test_init(self):
        """测试初始化状态"""
        self.assertFalse(self.device_state.is_valid)
        self.assertIsNone(self.device_state.device_info)
        self.assertIsNone(self.device_state.screen_width)
        self.assertIsNone(self.device_state.screen_height)
        self.assertIsNone(self.device_state.screen_orientation)
        self.assertIsNone(self.device_state.touch_device)
    
    @patch('subprocess.run')
    def test_check_adb_connection_success(self, mock_run):
        """测试ADB连接成功的情况"""
        # 模拟成功的ADB连接
        mock_result = MagicMock()
        mock_result.stdout = "List of devices attached\ndevice1\tdevice\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._check_adb_connection()
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ['adb', 'devices'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_check_adb_connection_no_devices(self, mock_run):
        """测试没有设备连接的情况"""
        mock_result = MagicMock()
        mock_result.stdout = "List of devices attached\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._check_adb_connection()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_check_adb_connection_timeout(self, mock_run):
        """测试ADB命令超时的情况"""
        mock_run.side_effect = subprocess.TimeoutExpired(['adb', 'devices'], 10)
        
        result = self.device_state._check_adb_connection()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_get_screen_resolution_success(self, mock_run):
        """测试成功获取屏幕分辨率"""
        mock_result = MagicMock()
        mock_result.stdout = "Physical size: 1080x2340\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._get_screen_resolution()
        self.assertEqual(result, (1080, 2340))
    
    @patch('subprocess.run')
    def test_get_screen_resolution_fail(self, mock_run):
        """测试获取屏幕分辨率失败"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result
        
        result = self.device_state._get_screen_resolution()
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_get_screen_orientation_success(self, mock_run):
        """测试成功获取屏幕方向"""
        mock_result = MagicMock()
        mock_result.stdout = "mDisplayRotation=ROTATION_90\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._get_screen_orientation()
        self.assertEqual(result, 1)  # 90度 / 90 = 1 (横屏)
    
    @patch('subprocess.run')
    def test_get_screen_orientation_default(self, mock_run):
        """测试屏幕方向获取失败时的默认值"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = self.device_state._get_screen_orientation()
        self.assertEqual(result, 1)  # 默认横屏
    
    def test_split_device_blocks(self):
        """测试设备块分割功能"""
        sample_output = """add device 1: /dev/input/event0 (gpio-keys)
  EV_KEY (0001): KEY_VOLUMEUP          KEY_VOLUMEDOWN
add device 2: /dev/input/event1 (touchscreen)
  EV_ABS (0003): ABS_MT_POSITION_X     (min 0, max 4095, fuzz 0, flat 0, res 0)
                  ABS_MT_POSITION_Y     (min 0, max 4095, fuzz 0, flat 0, res 0)"""
        
        blocks = self.device_state._split_device_blocks(sample_output)
        self.assertEqual(len(blocks), 2)
        self.assertIn('/dev/input/event0', blocks[0])
        self.assertIn('/dev/input/event1', blocks[1])
        self.assertIn('ABS_MT_POSITION_X', blocks[1])
    
    def test_parse_device_block_success(self):
        """测试成功解析触摸设备块"""
        device_block = """add device 2: /dev/input/event1 (touchscreen)
  EV_ABS (0003): ABS_MT_POSITION_X     (min 0, max 4095, fuzz 0, flat 0, res 0)
                  ABS_MT_POSITION_Y     (min 0, max 4095, fuzz 0, flat 0, res 0)"""
        
        result = self.device_state._parse_device_block(device_block)
        expected = {
            'device': '/dev/input/event1',
            'max_x': 4095,
            'max_y': 4095
        }
        self.assertEqual(result, expected)
    
    def test_parse_device_block_no_touch(self):
        """测试解析非触摸设备块"""
        device_block = """add device 1: /dev/input/event0 (gpio-keys)
  EV_KEY (0001): KEY_VOLUMEUP          KEY_VOLUMEDOWN"""
        
        result = self.device_state._parse_device_block(device_block)
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_find_touch_device_success(self, mock_run):
        """测试成功查找触摸设备"""
        mock_result = MagicMock()
        mock_result.stdout = """add device 1: /dev/input/event0 (gpio-keys)
  EV_KEY (0001): KEY_VOLUMEUP
add device 2: /dev/input/event1 (touchscreen)
  EV_ABS (0003): ABS_MT_POSITION_X     (min 0, max 4095, fuzz 0, flat 0, res 0)
                  ABS_MT_POSITION_Y     (min 0, max 4095, fuzz 0, flat 0, res 0)"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._find_touch_device()
        expected = {
            'device': '/dev/input/event1',
            'max_x': 4095,
            'max_y': 4095
        }
        self.assertEqual(result, expected)
    
    @patch('subprocess.run')
    def test_find_touch_device_not_found(self, mock_run):
        """测试找不到触摸设备"""
        mock_result = MagicMock()
        mock_result.stdout = """add device 1: /dev/input/event0 (gpio-keys)
  EV_KEY (0001): KEY_VOLUMEUP"""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.device_state._find_touch_device()
        self.assertIsNone(result)
    
    @patch.object(DeviceState, '_find_touch_device')
    @patch.object(DeviceState, '_get_screen_orientation')
    @patch.object(DeviceState, '_get_screen_resolution')
    @patch.object(DeviceState, '_check_adb_connection')
    def test_initialize_all_success(self, mock_adb, mock_resolution, mock_orientation, mock_touch):
        """测试完整初始化成功"""
        # 设置所有mock返回成功值
        mock_adb.return_value = True
        mock_resolution.return_value = (1080, 2340)
        mock_orientation.return_value = 1
        mock_touch.return_value = {'device': '/dev/input/event1', 'max_x': 4095, 'max_y': 4095}
        
        result = self.device_state.initialize_all()
        
        self.assertTrue(result)
        self.assertTrue(self.device_state.is_valid)
        self.assertEqual(self.device_state.screen_width, 1080)
        self.assertEqual(self.device_state.screen_height, 2340)
        self.assertEqual(self.device_state.screen_orientation, 1)
        self.assertIsNotNone(self.device_state.touch_device)
    
    @patch.object(DeviceState, '_check_adb_connection')
    def test_initialize_all_adb_fail(self, mock_adb):
        """测试ADB连接失败时的初始化"""
        mock_adb.return_value = False
        
        result = self.device_state.initialize_all()
        
        self.assertFalse(result)
        self.assertFalse(self.device_state.is_valid)
    
    @patch.object(DeviceState, '_get_screen_resolution')
    @patch.object(DeviceState, '_check_adb_connection')
    def test_initialize_all_resolution_fail(self, mock_adb, mock_resolution):
        """测试屏幕分辨率获取失败时的初始化"""
        mock_adb.return_value = True
        mock_resolution.return_value = None
        
        result = self.device_state.initialize_all()
        
        self.assertFalse(result)
        self.assertFalse(self.device_state.is_valid)


class TestDeviceStateIntegration(unittest.TestCase):
    """DeviceState集成测试（需要真实ADB环境）"""
    
    def setUp(self):
        """集成测试setup"""
        self.device_state = DeviceState()
    
    @unittest.skipUnless(
        os.system('adb devices > /dev/null 2>&1') == 0, 
        "需要ADB环境和连接的设备"
    )
    def test_real_device_initialization(self):
        """测试真实设备环境下的初始化（可选）"""
        # 这个测试只在有真实ADB环境时运行
        result = self.device_state.initialize_all()
        
        if result:
            self.assertTrue(self.device_state.is_valid)
            self.assertIsNotNone(self.device_state.screen_width)
            self.assertIsNotNone(self.device_state.screen_height)
            self.assertIsInstance(self.device_state.screen_orientation, int)
            print(f"真实设备测试成功:")
            print(f"  屏幕: {self.device_state.screen_width}x{self.device_state.screen_height}")
            print(f"  方向: {self.device_state.screen_orientation}")
            if self.device_state.touch_device:
                print(f"  触摸设备: {self.device_state.touch_device}")


if __name__ == '__main__':
    # 创建测试套件
    unittest.main(verbosity=2)