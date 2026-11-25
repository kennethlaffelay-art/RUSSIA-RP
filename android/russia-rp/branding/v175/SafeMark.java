package com.russiarp.ui;

import android.content.Context;
import android.os.Build;
import android.util.AttributeSet;
import android.view.DisplayCutout;
import android.view.RoundedCorner;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.ImageView;

/** Keep only the HUD wordmark inside the lower left corner; radar coordinates stay independent. */
public final class SafeMark extends ImageView implements Runnable {
    private final int[] origin = new int[2];

    public SafeMark(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        requestApplyInsets();
        post(this);
    }

    @Override public WindowInsets onApplyWindowInsets(WindowInsets insets) {
        removeCallbacks(this);
        post(this);
        return super.onApplyWindowInsets(insets);
    }

    @Override protected void onDetachedFromWindow() {
        removeCallbacks(this);
        super.onDetachedFromWindow();
    }

    @Override public void run() {
        if (!(getParent() instanceof View)) return;
        View parent = (View) getParent();
        int base = Math.max(1, Math.round(getResources().getDisplayMetrics().density));
        int left = base, bottom = base;
        if (Build.VERSION.SDK_INT >= 23) {
            WindowInsets insets = getRootWindowInsets();
            if (insets != null) {
                int corner = Build.VERSION.SDK_INT >= 31 ? Corner.padding(insets) : 2 * base;
                parent.getLocationInWindow(origin);
                int rootHeight = getRootView().getHeight();
                int rowTop = origin[1] + parent.getHeight() - getHeight() - corner;
                int safeLeft = corner, safeBottom = corner;
                if (Build.VERSION.SDK_INT >= 28) {
                    DisplayCutout cutout = insets.getDisplayCutout();
                    if (cutout != null) {
                        // A camera notch halfway up the left edge does not cover the bottom row.
                        for (android.graphics.Rect rect : cutout.getBoundingRects()) {
                            if (rect.left <= 0 && rect.bottom > rowTop)
                                safeLeft = Math.max(safeLeft, rect.right);
                            if (rect.bottom >= rootHeight && rect.left < origin[0] + getWidth() + base)
                                safeBottom = Math.max(safeBottom, rootHeight - rect.top);
                        }
                    }
                }
                left = Math.max(base, safeLeft - origin[0]);
                bottom = Math.max(base, safeBottom - (getRootView().getHeight() - origin[1] - parent.getHeight()));
            }
        }
        ViewGroup.MarginLayoutParams lp = (ViewGroup.MarginLayoutParams) getLayoutParams();
        if (lp.getMarginStart() != left || lp.bottomMargin != bottom) {
            lp.setMarginStart(left);
            lp.bottomMargin = bottom;
            setLayoutParams(lp);
        }
    }

    private static final class Corner {
        static int padding(WindowInsets insets) {
            RoundedCorner corner = insets.getRoundedCorner(RoundedCorner.POSITION_BOTTOM_LEFT);
            // At 45 degrees, the first fully visible corner of an inscribed rectangle.
            return corner == null ? 0 : (int) Math.ceil((1.0 - Math.sqrt(0.5)) * corner.getRadius());
        }
    }
}
