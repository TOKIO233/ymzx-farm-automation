package com.touchmonitor.app;

import android.app.Service;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.os.IBinder;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Toast;

public class TouchOverlayService extends Service {
    
    private static final String TAG = "TouchCoords";
    private WindowManager windowManager;
    private View overlayView;
    
    @Override
    public void onCreate() {
        super.onCreate();
        
        // 检查悬浮窗权限
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "需要悬浮窗权限", Toast.LENGTH_LONG).show();
            stopSelf();
            return;
        }
        
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        createOverlay();
    }
    
    private void createOverlay() {
        // 创建透明的全屏悬浮窗
        overlayView = new View(this) {
            @Override
            public boolean onTouchEvent(MotionEvent event) {
                // 这里可以获取到真实的屏幕坐标！
                float rawX = event.getRawX();
                float rawY = event.getRawY();
                
                int action = event.getAction();
                String actionStr = "";
                
                switch (action) {
                    case MotionEvent.ACTION_DOWN:
                        actionStr = "DOWN";
                        break;
                    case MotionEvent.ACTION_MOVE:
                        actionStr = "MOVE";
                        break;
                    case MotionEvent.ACTION_UP:
                        actionStr = "UP";
                        break;
                }
                
                // 输出到logcat，Python可以读取
                Log.d(TAG, String.format("TOUCH_%s:(%.0f,%.0f)", actionStr, rawX, rawY));
                
                // 不消费事件，让下层应用继续处理
                return false;
            }
        };
        
        // 悬浮窗参数
        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | 
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL |
            WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        );
        
        params.gravity = Gravity.TOP | Gravity.LEFT;
        
        // 添加悬浮窗
        windowManager.addView(overlayView, params);
        Log.d(TAG, "TouchOverlay service started");
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        if (overlayView != null && windowManager != null) {
            windowManager.removeView(overlayView);
        }
        Log.d(TAG, "TouchOverlay service stopped");
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}