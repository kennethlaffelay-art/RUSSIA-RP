package com.russiarp.qa;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Intent;
import android.graphics.Bitmap;
import android.view.PixelCopy;
import android.view.SurfaceView;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** An Android instrumentation test that reads the actual native rendering surface. */
public final class WorldCapture extends Instrumentation {
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }

    @Override public void onStart() {
        try {
            Intent intent = new Intent();
            intent.setClassName(getTargetContext().getPackageName(), "com.wn.blackrussia.game.Multiplayer");
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            Activity game = startActivitySync(intent);
            File dir = game.getExternalFilesDir(null);
            File request = new File(dir, "capture.request");
            File joined = new File(dir, "spawn.complete");
            Handler main = new Handler(Looper.getMainLooper());
            for (int rounds = 0; rounds < 1600; rounds++) {
                if (joined.delete()) {
                    // The stock open.mp test host has no Moscow server-selector UI protocol.
                    // Use the client's normal dismissal callback after its actual spawn RPC.
                    java.lang.reflect.Method hide = game.getClass().getDeclaredMethod("hideLoadingScreen");
                    hide.setAccessible(true);
                    runOnMainSync(() -> {
                        try { hide.invoke(game); }
                        catch (ReflectiveOperationException ex) { throw new IllegalStateException(ex); }
                    });
                }
                if (!request.delete()) { Thread.sleep(150); continue; }
                SurfaceView view = (SurfaceView) game.getClass().getMethod("GetSurfaceView").invoke(game);
                if (view == null || !view.getHolder().getSurface().isValid()) continue;
                int w = view.getHolder().getSurfaceFrame().width();
                int h = view.getHolder().getSurfaceFrame().height();
                Bitmap image = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
                try {
                    CountDownLatch copied = new CountDownLatch(1);
                    final int[] status = {-1};
                    PixelCopy.request(view, image, result -> { status[0] = result; copied.countDown(); }, main);
                    if (!copied.await(5, TimeUnit.SECONDS) || status[0] != PixelCopy.SUCCESS) continue;
                    File part = new File(dir, "world.tmp");
                    try (FileOutputStream stream = new FileOutputStream(part)) {
                        if (!image.compress(Bitmap.CompressFormat.PNG, 100, stream)) continue;
                    }
                    if (!part.renameTo(new File(dir, "world.png"))) throw new IllegalStateException("capture rename");
                } finally { image.recycle(); }
            }
            finish(Activity.RESULT_OK, new Bundle());
        } catch (Exception ex) {
            Bundle error = new Bundle();
            error.putString("error", ex.toString());
            finish(Activity.RESULT_CANCELED, error);
        }
    }
}
