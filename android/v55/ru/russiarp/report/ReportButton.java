package ru.russiarp.report;

import android.app.Activity;
import android.content.*;
import android.net.Uri;
import android.util.AttributeSet;
import android.widget.Button;
import android.widget.Toast;
import androidx.core.content.FileProvider;
import java.io.File;

public final class ReportButton extends Button {
    public ReportButton(Context context, AttributeSet attrs) {
        super(context,attrs);
        setAllCaps(false);
        setOnClickListener(v -> send());
    }
    private void send() {
        Context context = getContext();
        while (context instanceof ContextWrapper && !(context instanceof Activity))
            context = ((ContextWrapper)context).getBaseContext();
        if (!(context instanceof Activity)) return;
        Activity activity = (Activity)context;
        setEnabled(false);
        setText("Сбор крашлога…");
        new Thread(() -> {
            try {
                File file = Reports.create(activity.getApplicationContext());
                Uri uri = FileProvider.getUriForFile(activity,activity.getPackageName()+".provider",file);
                Intent send = new Intent(Intent.ACTION_SEND).setType("application/zip")
                    .putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                send.setClipData(ClipData.newRawUri("Крашлог",uri));
                activity.runOnUiThread(() -> {
                    reset();
                    if (activity.isFinishing() || activity.isDestroyed()) return;
                    try { activity.startActivity(Intent.createChooser(send,"Отправить крашлог")); }
                    catch (ActivityNotFoundException e) { message("Нет приложения для отправки ZIP"); }
                });
            } catch (Exception e) {
                activity.runOnUiThread(() -> { reset(); message("Не удалось собрать крашлог. Попробуйте ещё раз."); });
            }
        },"client-share-report").start();
    }
    private void reset() { setText("Отправить крашлог"); setEnabled(true); }
    private void message(String text) { Toast.makeText(getContext(),text,Toast.LENGTH_LONG).show(); }
}
