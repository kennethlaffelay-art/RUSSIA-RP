package com.russiarp.qa;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import java.io.File;
import java.io.FileOutputStream;

public final class HudScreens extends Screens {
    @Override int id(String name) { return res(name, "id"); }

    @Override int res(String name, String type) {
        return context.getResources().getIdentifier(name, type, getTargetContext().getPackageName());
    }

    private void captureHud(int w, int h) throws Exception {
        configure(w, h);
        View hud = inflate("br_hud");
        hud.setVisibility(View.VISIBLE);
        ImageView mark = hud.findViewById(id("brHudLogo"));
        ImageView bonus = hud.findViewById(id("brHudDoubleLogo"));
        bonus.setVisibility(View.VISIBLE);
        capture(hud, "hud");
        check(mark.getLeft() >= 0 && bonus.getLeft() >= mark.getRight(), "HUD spacing");
        check(Math.abs(mark.getTop() + mark.getBottom() - bonus.getTop() - bonus.getBottom()) <= 2,
                "x4 and wordmark must have a common center");
        Bitmap bitmap = Bitmap.createBitmap(mark.getWidth(), mark.getHeight(), Bitmap.Config.ARGB_8888);
        mark.draw(new Canvas(bitmap));
        try (FileOutputStream out = new FileOutputStream(new File(getTargetContext().getFilesDir(),
                "mark-" + w + ".png"))) {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
        bitmap.recycle();
    }

    @Override public void onStart() {
        final Bundle result = new Bundle();
        runOnMainSync(new Runnable() {
            @Override public void run() {
                try {
                    captureHud(1280, 720);
                    captureHud(1600, 720);
                    result.putString("stream", "HUD PASSED");
                } catch (Throwable e) {
                    result.putString("stream", android.util.Log.getStackTraceString(e));
                }
            }
        });
        finish("HUD PASSED".equals(result.getString("stream")) ? -1 : 0, result);
    }
}
