package com.russiarp.qa;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.LayerDrawable;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

/** Exercise the real APK resources through Android's layout inflater on two screen sizes. */
public final class PreviewScreens extends Screens {
    private boolean gameOnly;

    @Override public void onCreate(Bundle args) {
        gameOnly = args != null && "game".equals(args.getString("mode"));
        super.onCreate(args);
    }

    @Override int id(String name) { return res(name, "id"); }
    @Override int res(String name, String type) {
        return context.getResources().getIdentifier(name, type, getTargetContext().getPackageName());
    }

    private void checkScreens(int w, int h) throws Exception {
        configure(w, h);
        View hud = inflate("br_hud");
        hud.setVisibility(View.VISIBLE);
        ImageView mark = hud.findViewById(id("brHudLogo"));
        View bonus = hud.findViewById(id("brHudDoubleLogo"));
        bonus.setVisibility(View.VISIBLE);
        capture(hud, "hud");
        check(mark.getHeight() == context.getResources().getDimensionPixelSize(res("_20sdp", "dimen")), "emblem height");
        check(mark.getDrawable() != null && mark.getLeft() >= 0 && bonus.getLeft() >= mark.getRight(), "HUD spacing");
        check(Math.abs(mark.getTop() + mark.getBottom() - bonus.getTop() - bonus.getBottom()) <= 2, "x4 alignment");
        View pass = inflate("br_bp");
        TextView tab = pass.findViewById(id("br_bp_butt_pass"));
        check("RUSSIA PASS".contentEquals(tab.getText()), "season navigation label");
        capture(pass, "pass");
        View tiers = inflate("bp_pass");
        TextView title = tiers.findViewById(id("textView52"));
        check("Russia Pass".contentEquals(title.getText()), "tier heading");
        View notification = inflate("br_notification");
        check(notification.findViewById(id("br_not_progress")) != null, "notification progress");
        String[] kinds = {"green", "red", "orange"};
        int[][] expected = {{0xff7eac75, 0xff456a45}, {0xffc16355, 0xff743b34}, {0xffa45431, 0xffd68b60}};
        for (int i = 0; i < kinds.length; i++) {
            int resource = res("background_br_notification_" + kinds[i], "drawable");
            LayerDrawable layers = (LayerDrawable) context.getDrawable(resource);
            GradientDrawable gradient = (GradientDrawable) layers.getDrawable(0);
            check(java.util.Arrays.equals(gradient.getColors(), expected[i]), kinds[i] + " notification colors");
        }
        capture(notification, "notification");
    }

    @Override public void onStart() {
        final Bundle result = new Bundle();
        if (gameOnly) {
            try {
                Context app = getTargetContext();
                Intent play = new Intent().setClassName(app, "com.wn.blackrussia.game.Multiplayer");
                play.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                Activity game = startActivitySync(play);
                SystemClock.sleep(45000);
                check(!game.isFinishing() && !game.isDestroyed() && game.hasWindowFocus(), "native game foreground");
                result.putString("stream", "GAME177 PASSED");
                finish(-1, result);
            } catch (Throwable e) {
                result.putString("stream", android.util.Log.getStackTraceString(e));
                finish(0, result);
            }
            return;
        }
        final Throwable[] failure = new Throwable[1];
        runOnMainSync(new Runnable() {
            @Override public void run() {
                try {
                    checkScreens(1280, 720);
                    checkScreens(1600, 720);
                } catch (Throwable e) {
                    failure[0] = e;
                }
            }
        });
        result.putString("stream", failure[0] == null ? "UI177 PASSED" : android.util.Log.getStackTraceString(failure[0]));
        finish(failure[0] == null ? -1 : 0, result);
    }
}
