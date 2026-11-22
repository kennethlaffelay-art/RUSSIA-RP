package ru.russiarp.testframe;
import android.app.Activity;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.opengl.GLES20;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.PixelCopy;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Map;

public class Probe extends Activity implements SurfaceHolder.Callback {
    private Class<?> eglClass;
    private Object engine;
    private SurfaceView view;
    private boolean started;
    private void check(boolean ok, String label) {
        if (!ok) throw new IllegalStateException(label);
        Log.i("FrameProbe", label);
    }
    private boolean call(String name) throws Exception {
        return (Boolean)eglClass.getMethod(name).invoke(engine);
    }
    public void onCreate(Bundle saved) {
        super.onCreate(saved);
        view = new SurfaceView(this);
        view.getHolder().addCallback(this);
        setContentView(view);
    }
    public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) {
        if (started || width < 1 || height < 1) return;
        started = true;
        try {
            Context client = createPackageContext("com.wn.blackrussia", CONTEXT_INCLUDE_CODE | CONTEXT_IGNORE_SECURITY);
            ClassLoader loader = client.getClassLoader();
            Class<?> gui = loader.loadClass("com.wn.blackrussia.game.GUIManager");
            Field list = gui.getDeclaredField("list");
            list.setAccessible(true);
            Map<?,?> registrations = (Map<?,?>)list.get(null);
            check(registrations.keySet().equals(new HashSet<Integer>(Arrays.asList(0,1,2))), "HUD and menus registered, subscription popup absent");
            eglClass = loader.loadClass("com.nvidia.devtech.NvEventQueueActivity");
            engine = loader.loadClass("com.wardrumstudios.utils.WarBase").getConstructor().newInstance();
            check(!(Boolean)eglClass.getMethod("createEGLSurface", SurfaceHolder.class).invoke(engine, new Object[]{null}), "Missing surface rejected");
            Field h = eglClass.getDeclaredField("cachedSurfaceHolder");
            h.setAccessible(true);
            h.set(engine, holder);
            new Thread(() -> {
                try {
                    check((Boolean)eglClass.getMethod("InitEGLAndGLES2", int.class).invoke(engine, 3), "Actual APK opened a window surface");
                    check(call("makeCurrent"), "GLES context bound");
                    int w = (Integer)eglClass.getMethod("getSurfaceWidth").invoke(engine);
                    int ht = (Integer)eglClass.getMethod("getSurfaceHeight").invoke(engine);
                    check(w > 0 && ht > 0, "Positive render dimensions");
                    // First swap may be skipped during startup. Render both frames from scratch.
                    for (int i = 0; i < 2; i++) {
                        GLES20.glDisable(GLES20.GL_SCISSOR_TEST);
                        GLES20.glClearColor(1f,0f,0f,1f);
                        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);
                        GLES20.glEnable(GLES20.GL_SCISSOR_TEST);
                        GLES20.glScissor(w/2,0,w-w/2,ht);
                        GLES20.glClearColor(0f,1f,0f,1f);
                        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);
                        GLES20.glFinish();
                        check(call("swapBuffers"), "Frame swap succeeded");
                    }
                    Handler main = new Handler(Looper.getMainLooper());
                    main.postDelayed(() -> sample(main), 300);
                } catch(Throwable error) { fail(error); }
            }, "probe-egl").start();
        } catch(Throwable error) { fail(error); }
    }
    private void sample(Handler main) {
        try {
            Bitmap bitmap = Bitmap.createBitmap(16,16,Bitmap.Config.ARGB_8888);
            PixelCopy.request(view,bitmap,status -> {
                try {
                    check(status == PixelCopy.SUCCESS, "Surface buffer copied");
                    int left = bitmap.getPixel(2,8);
                    int right = bitmap.getPixel(13,8);
                    check(Color.red(left)>200 && Color.green(left)<50 && Color.green(right)>200 && Color.red(right)<50, "Both colors visible in submitted buffer");
                    Log.i("FrameProbe","PROBE_PASS");
                } catch(Throwable e) { fail(e); } finally { bitmap.recycle(); }
            }, main);
        } catch(Throwable e) { fail(e); }
    }
    private void fail(Throwable e) { Log.e("FrameProbe","PROBE_FAIL",e); }
    public void surfaceCreated(SurfaceHolder holder) {}
    public void surfaceDestroyed(SurfaceHolder holder) {}
}
