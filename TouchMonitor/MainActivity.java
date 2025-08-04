package com.touchmonitor.app;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // 简单的布局
        TextView textView = new TextView(this);
        textView.setText("触摸坐标监控 v2.0\n\n使用getRawX()/getRawY()获取真实屏幕坐标\n\n点击按钮开启监控");
        textView.setTextSize(16);
        textView.setPadding(50, 100, 50, 50);
        
        Button button1 = new Button(this);
        button1.setText("1. 开启悬浮窗权限");
        button1.setOnClickListener(v -> openOverlaySettings());
        
        Button button2 = new Button(this);
        button2.setText("2. 启动坐标监控");
        button2.setOnClickListener(v -> startTouchMonitor());
        
        Button button3 = new Button(this);
        button3.setText("3. 停止坐标监控");
        button3.setOnClickListener(v -> stopTouchMonitor());
        
        // 创建简单布局
        android.widget.LinearLayout layout = new android.widget.LinearLayout(this);
        layout.setOrientation(android.widget.LinearLayout.VERTICAL);
        layout.addView(textView);
        layout.addView(button1);
        layout.addView(button2);
        layout.addView(button3);
        
        setContentView(layout);
    }
    
    private void openOverlaySettings() {
        Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION);
        intent.setData(android.net.Uri.parse("package:" + getPackageName()));
        startActivity(intent);
        Toast.makeText(this, "请开启悬浮窗权限", Toast.LENGTH_LONG).show();
    }
    
    private void startTouchMonitor() {
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "请先开启悬浮窗权限", Toast.LENGTH_SHORT).show();
            return;
        }
        
        Intent intent = new Intent(this, TouchOverlayService.class);
        startService(intent);
        Toast.makeText(this, "坐标监控已启动\n触摸屏幕查看logcat输出", Toast.LENGTH_LONG).show();
    }
    
    private void stopTouchMonitor() {
        Intent intent = new Intent(this, TouchOverlayService.class);
        stopService(intent);
        Toast.makeText(this, "坐标监控已停止", Toast.LENGTH_SHORT).show();
    }
}