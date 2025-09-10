import move_debugger

try:
    device_state = move_debugger.DeviceState()
    print("✅ DeviceState OK")
    
    system = move_debugger.SystemComponents()
    print("✅ SystemComponents OK")
    
    print("✅ 基本类型检查通过")
    
except Exception as e:
    print(f"❌ 错误: {e}")