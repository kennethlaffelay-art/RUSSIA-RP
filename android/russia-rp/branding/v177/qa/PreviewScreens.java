package com.russiarp.qa;

import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

/** Exercise the real APK resources through Android's layout inflater on two screen sizes. */
public final class PreviewScreens extends Screens {
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
        for (String kind : new String[]{"green", "red", "orange"}) {
            int resource = res("background_br_notification_" + kind, "drawable");
            check(context.getDrawable(resource) instanceof GradientDrawable, kind + " notification gradient");
        }
        capture(notification, "notification");
    }

    @Override public void onStart() {
        final Bundle result = new Bundle();
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
