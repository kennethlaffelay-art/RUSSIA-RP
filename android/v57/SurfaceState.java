package ru.russiarp.report;

import android.app.Activity;
import android.graphics.Bitmap;
import android.os.Handler;
import android.os.Looper;
import android.view.PixelCopy;
import android.view.SurfaceView;
import android.view.View;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Measure only the game surface. No image or per-pixel data leaves memory. */
final class SurfaceState {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private int generation;

    void start(Activity activity) {
        if (!isGame(activity)) return;
        int run = ++generation;
        write(activity, "Game resumed", false);
        for (int delay : new int[]{5, 15, 45, 90}) {
            handler.postDelayed(() -> {
                if (run != generation || activity.isDestroyed() || activity.isFinishing()) return;
                sample(activity, delay, run);
            }, delay * 1000L);
        }
    }

    void stop(Activity activity) {
        if (isGame(activity)) {
            generation++;
            handler.removeCallbacksAndMessages(null);
        }
    }

    private static boolean isGame(Activity activity) {
        return activity.getClass().getName().equals("com.wn.blackrussia.game.Multiplayer");
    }

    private void sample(Activity activity, int seconds, int run) {
        int id = activity.getResources().getIdentifier("main_sv", "id", activity.getPackageName());
        View v = activity.findViewById(id);
        if (!(v instanceof SurfaceView)) {
            write(activity, seconds + "s surface missing", true);
            return;
        }
        SurfaceView surface = (SurfaceView) v;
        String prefix = seconds + "s " + surface.getWidth() + "x" + surface.getHeight()
                + " shown=" + surface.isShown();
        if (!surface.getHolder().getSurface().isValid()) {
            write(activity, prefix + " invalid", true);
            return;
        }
        Bitmap reduced = Bitmap.createBitmap(16, 16, Bitmap.Config.ARGB_8888);
        try {
            PixelCopy.request(surface, reduced, status -> {
                try {
                    if (generation != run) return;
                    String result = prefix + " copy=" + status;
                    if (status == PixelCopy.SUCCESS) {
                        int lit = 0;
                        for (int y = 0; y < 16; y++) {
                            for (int x = 0; x < 16; x++) {
                                if ((reduced.getPixel(x, y) & 0x00f0f0f0) != 0) lit++;
                            }
                        }
                        result += " lit=" + lit + "/256";
                    }
                    write(activity, result, true);
                } finally { reduced.recycle(); }
            }, handler);
        } catch (IllegalArgumentException e) {
            reduced.recycle();
            write(activity, prefix + " surface withdrawn", true);
        }
    }

    private static void write(Activity a, String row, boolean append) {
        File file = new File(a.getFilesDir(), "russia-diagnostics/surface-state.txt");
        try (FileOutputStream out = new FileOutputStream(file, append)) {
            out.write((row + "\n").getBytes(StandardCharsets.UTF_8));
        } catch (IOException | SecurityException ignored) {}
    }
}
