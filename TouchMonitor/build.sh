#!/bin/bash

# TouchMonitor应用自动编译脚本 - 适用于GitHub Codespaces
# 自动安装Android开发环境并编译APK

echo "🚀 TouchMonitor应用自动编译 (GitHub Codespaces)"
echo "=================================================="
echo ""

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 第一步：安装Java
echo -e "${BLUE}📦 第1步：安装Java开发环境...${NC}"
sudo apt update -qq
sudo apt install -y openjdk-17-jdk wget unzip > /dev/null 2>&1

# 检查Java安装
if java -version > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Java安装成功${NC}"
    java -version
else
    echo -e "${RED}❌ Java安装失败${NC}"
    exit 1
fi

# 第二步：下载并安装Android SDK
echo -e "${BLUE}📦 第2步：下载Android SDK...${NC}"
cd ~
wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Android SDK下载完成${NC}"
else
    echo -e "${RED}❌ Android SDK下载失败${NC}"
    exit 1
fi

# 解压SDK
echo -e "${BLUE}📁 解压Android SDK...${NC}"
unzip -q commandlinetools-linux-9477386_latest.zip
mkdir -p android-sdk/cmdline-tools
mv cmdline-tools android-sdk/cmdline-tools/latest

# 第三步：设置环境变量
echo -e "${BLUE}⚙️ 第3步：配置环境变量...${NC}"
export ANDROID_HOME="$HOME/android-sdk"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools"

echo "ANDROID_HOME: $ANDROID_HOME"
echo "PATH已更新"

# 第四步：安装Android SDK组件
echo -e "${BLUE}📦 第4步：安装Android SDK组件...${NC}"
yes | sdkmanager --licenses > /dev/null 2>&1
sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Android SDK组件安装完成${NC}"
else
    echo -e "${RED}❌ Android SDK组件安装失败${NC}"
    exit 1
fi

# 第五步：返回项目目录并创建Android项目结构
echo -e "${BLUE}📁 第5步：创建Android项目结构...${NC}"
cd /workspaces/*/TouchMonitor || cd ~/TouchMonitor || { echo "找不到TouchMonitor目录"; exit 1; }

# 创建标准Android项目结构
mkdir -p app/src/main/java/com/touchmonitor/app
mkdir -p app/src/main/res/values
mkdir -p app/src/main/res/xml

# 移动文件到正确位置
echo -e "${BLUE}📋 组织项目文件...${NC}"
cp MainActivity.java app/src/main/java/com/touchmonitor/app/ 2>/dev/null || echo "MainActivity.java已在正确位置"
cp TouchMonitorService.java app/src/main/java/com/touchmonitor/app/ 2>/dev/null || echo "TouchMonitorService.java已在正确位置"
cp AndroidManifest.xml app/src/main/ 2>/dev/null || echo "AndroidManifest.xml已在正确位置"
cp accessibility_service_config.xml app/src/main/res/xml/ 2>/dev/null || echo "accessibility_service_config.xml已在正确位置"

# 第六步：创建必要的配置文件
echo -e "${BLUE}📝 第6步：生成配置文件...${NC}"

# 创建根级build.gradle
cat > build.gradle << 'EOF'
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:7.4.2'
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
EOF

# 创建app/build.gradle
cat > app/build.gradle << 'EOF'
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.touchmonitor.app'
    compileSdk 33

    defaultConfig {
        applicationId "com.touchmonitor.app"
        minSdk 21
        targetSdk 33
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
}
EOF

# 创建字符串资源
cat > app/src/main/res/values/strings.xml << 'EOF'
<resources>
    <string name="app_name">触摸坐标监控</string>
</resources>
EOF

# 创建gradle.properties
cat > gradle.properties << 'EOF'
android.useAndroidX=true
android.enableJetifier=true
EOF

# 创建Gradle Wrapper
echo -e "${BLUE}⚙️ 第7步：设置Gradle Wrapper...${NC}"
gradle wrapper --gradle-version=7.6

# 第八步：编译APK
echo -e "${BLUE}🔨 第8步：开始编译APK...${NC}"
./gradlew assembleDebug

# 检查编译结果
if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo ""
    echo -e "${GREEN}🎉 编译成功！${NC}"
    echo "=================================================="
    echo -e "${YELLOW}📦 APK文件位置:${NC}"
    echo "   app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo -e "${YELLOW}📱 后续步骤:${NC}"
    echo "   1. 下载APK文件到本地"
    echo "   2. adb install app-debug.apk"
    echo "   3. 开启无障碍服务权限"
    echo "   4. 运行Python脚本选择功能2"
    echo ""
    echo -e "${GREEN}✨ 编译完成！可以开始使用了${NC}"
else
    echo ""
    echo -e "${RED}❌ 编译失败${NC}"
    echo "请检查上面的错误信息"
    echo ""
    echo -e "${YELLOW}🔧 常见问题解决:${NC}"
    echo "   1. 检查网络连接"
    echo "   2. 重新运行: ./build.sh"
    echo "   3. 检查Java版本是否正确"
fi