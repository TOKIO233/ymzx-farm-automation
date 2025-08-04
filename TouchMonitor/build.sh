#!/bin/bash

# TouchMonitor应用编译脚本
# 需要安装Android SDK和gradle

echo "📱 TouchMonitor应用编译脚本"
echo "================================"

# 检查工具
if ! command -v gradle &> /dev/null; then
    echo "❌ Gradle未安装，请先安装Android开发环境"
    exit 1
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "❌ ANDROID_HOME环境变量未设置"
    exit 1
fi

echo "✅ 开发环境检查通过"

# 创建项目结构
mkdir -p TouchMonitor/app/src/main/java/com/touchmonitor/app
mkdir -p TouchMonitor/app/src/main/res/{values,xml,mipmap-hdpi}

# 复制源文件到正确位置
cp MainActivity.java TouchMonitor/app/src/main/java/com/touchmonitor/app/
cp TouchOverlayService.java TouchMonitor/app/src/main/java/com/touchmonitor/app/
cp AndroidManifest.xml TouchMonitor/app/src/main/
cp accessibility_service_config.xml TouchMonitor/app/src/main/res/xml/

# 创建基础资源文件
cat > TouchMonitor/app/src/main/res/values/strings.xml << 'EOF'
<resources>
    <string name="app_name">触摸坐标监控</string>
</resources>
EOF

cat > TouchMonitor/app/src/main/res/values/styles.xml << 'EOF'
<resources>
    <style name="AppTheme" parent="android:Theme.Material.Light.DarkActionBar">
    </style>
</resources>
EOF

# 创建Gradle配置
cat > TouchMonitor/build.gradle << 'EOF'
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:7.4.0'
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
EOF

cat > TouchMonitor/app/build.gradle << 'EOF'
apply plugin: 'com.android.application'

android {
    compileSdkVersion 33
    
    defaultConfig {
        applicationId "com.touchmonitor.app"
        minSdkVersion 21
        targetSdkVersion 33
        versionCode 1
        versionName "1.0"
    }
    
    buildTypes {
        release {
            minifyEnabled false
        }
    }
}

dependencies {
    // 基础依赖
}
EOF

# 编译APK
echo "🔨 开始编译APK..."
cd TouchMonitor
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo "✅ 编译成功！"
    echo "📦 APK位置: TouchMonitor/app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "📋 安装步骤："
    echo "1. adb install TouchMonitor/app/build/outputs/apk/debug/app-debug.apk"
    echo "2. 打开'触摸坐标监控'应用"
    echo "3. 点击'开启悬浮窗权限'并授权" 
    echo "4. 点击'启动坐标监控'"
    echo "5. 在Python脚本中选择功能2"
else
    echo "❌ 编译失败，请检查错误信息"
fi