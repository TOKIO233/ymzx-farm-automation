#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SystemComponents类单元测试
测试系统组件容器的初始化和依赖管理功能
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from move_debugger import SystemComponents, DeviceState, ADBExecutor, TouchEventRecorder


class TestSystemComponents(unittest.TestCase):
    """SystemComponents类单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.system = SystemComponents()
    
    def test_init_empty_system(self):
        """测试系统组件容器初始化状态"""
        self.assertIsNone(self.system.device_state)
        self.assertIsNone(self.system.adb_executor)
        self.assertIsNone(self.system.touch_recorder)
        self.assertFalse(self.system.is_initialized)
    
    @patch('move_debugger.DeviceState')
    @patch('move_debugger.ADBExecutor')
    @patch('move_debugger.TouchEventRecorder')
    def test_initialize_system_success(self, mock_touch_recorder, mock_adb_executor, mock_device_state):
        """测试成功初始化系统"""
        # 模拟DeviceState成功初始化
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = True
        mock_device_state.return_value = mock_device_instance
        
        # 模拟ADBExecutor成功创建
        mock_adb_instance = Mock()
        mock_adb_executor.return_value = mock_adb_instance
        
        # 模拟TouchEventRecorder成功创建
        mock_touch_instance = Mock()
        mock_touch_recorder.return_value = mock_touch_instance
        
        # 执行初始化
        result = self.system.initialize_system()
        
        # 验证结果
        self.assertTrue(result)
        self.assertTrue(self.system.is_initialized)
        self.assertEqual(self.system.device_state, mock_device_instance)
        self.assertEqual(self.system.adb_executor, mock_adb_instance)
        self.assertEqual(self.system.touch_recorder, mock_touch_instance)
        
        # 验证调用顺序和参数
        mock_device_state.assert_called_once()
        mock_device_instance.initialize_all.assert_called_once()
        mock_adb_executor.assert_called_once_with(mock_device_instance)
        mock_touch_recorder.assert_called_once_with(mock_device_instance, mock_adb_instance)
    
    @patch('move_debugger.DeviceState')
    def test_initialize_system_device_failure(self, mock_device_state):
        """测试设备状态初始化失败"""
        # 模拟DeviceState初始化失败
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = False
        mock_device_state.return_value = mock_device_instance
        
        # 执行初始化
        result = self.system.initialize_system()
        
        # 验证结果
        self.assertFalse(result)
        self.assertFalse(self.system.is_initialized)
        self.assertEqual(self.system.device_state, mock_device_instance)
        self.assertIsNone(self.system.adb_executor)
        self.assertIsNone(self.system.touch_recorder)
    
    @patch('move_debugger.DeviceState')
    @patch('move_debugger.ADBExecutor')
    def test_initialize_system_adb_failure(self, mock_adb_executor, mock_device_state):
        """测试ADB执行器创建失败"""
        # 模拟DeviceState成功初始化
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = True
        mock_device_state.return_value = mock_device_instance
        
        # 模拟ADBExecutor创建失败
        mock_adb_executor.side_effect = Exception("ADB初始化失败")
        
        # 执行初始化
        result = self.system.initialize_system()
        
        # 验证结果
        self.assertFalse(result)
        self.assertFalse(self.system.is_initialized)
    
    @patch('move_debugger.DeviceState')
    @patch('move_debugger.ADBExecutor')
    @patch('move_debugger.TouchEventRecorder')
    def test_initialize_system_touch_recorder_failure(self, mock_touch_recorder, mock_adb_executor, mock_device_state):
        """测试触摸记录器创建失败"""
        # 模拟DeviceState成功初始化
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = True
        mock_device_state.return_value = mock_device_instance
        
        # 模拟ADBExecutor成功创建
        mock_adb_instance = Mock()
        mock_adb_executor.return_value = mock_adb_instance
        
        # 模拟TouchEventRecorder创建失败
        mock_touch_recorder.side_effect = Exception("触摸记录器初始化失败")
        
        # 执行初始化
        result = self.system.initialize_system()
        
        # 验证结果
        self.assertFalse(result)
        self.assertFalse(self.system.is_initialized)
    
    def test_get_device_state_not_initialized(self):
        """测试未初始化时获取设备状态"""
        with self.assertRaises(RuntimeError) as context:
            self.system.get_device_state()
        
        self.assertIn("系统未初始化", str(context.exception))
    
    def test_get_adb_executor_not_initialized(self):
        """测试未初始化时获取ADB执行器"""
        with self.assertRaises(RuntimeError) as context:
            self.system.get_adb_executor()
        
        self.assertIn("系统未初始化", str(context.exception))
    
    def test_get_touch_recorder_not_initialized(self):
        """测试未初始化时获取触摸记录器"""
        with self.assertRaises(RuntimeError) as context:
            self.system.get_touch_recorder()
        
        self.assertIn("系统未初始化", str(context.exception))
    
    @patch('move_debugger.DeviceState')
    @patch('move_debugger.ADBExecutor')
    @patch('move_debugger.TouchEventRecorder')
    def test_get_components_after_initialization(self, mock_touch_recorder, mock_adb_executor, mock_device_state):
        """测试初始化后获取组件"""
        # 模拟成功初始化
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = True
        mock_device_state.return_value = mock_device_instance
        
        mock_adb_instance = Mock()
        mock_adb_executor.return_value = mock_adb_instance
        
        mock_touch_instance = Mock()
        mock_touch_recorder.return_value = mock_touch_instance
        
        # 初始化系统
        self.system.initialize_system()
        
        # 测试获取组件
        device_state = self.system.get_device_state()
        adb_executor = self.system.get_adb_executor()
        touch_recorder = self.system.get_touch_recorder()
        
        # 验证返回正确的实例
        self.assertEqual(device_state, mock_device_instance)
        self.assertEqual(adb_executor, mock_adb_instance)
        self.assertEqual(touch_recorder, mock_touch_instance)
    
    @patch('move_debugger.DeviceState')
    def test_partial_initialization_cleanup(self, mock_device_state):
        """测试部分初始化时的清理"""
        # 模拟DeviceState初始化成功但后续失败
        mock_device_instance = Mock()
        mock_device_instance.initialize_all.return_value = True
        mock_device_state.return_value = mock_device_instance
        
        # 注入一个异常到 ADBExecutor 构造过程中
        with patch('move_debugger.ADBExecutor', side_effect=Exception("模拟失败")):
            result = self.system.initialize_system()
        
        # 验证失败后系统状态
        self.assertFalse(result)
        self.assertFalse(self.system.is_initialized)
        # device_state应该被设置了，但系统整体初始化失败
        self.assertEqual(self.system.device_state, mock_device_instance)
        self.assertIsNone(self.system.adb_executor)
        self.assertIsNone(self.system.touch_recorder)


if __name__ == '__main__':
    unittest.main()