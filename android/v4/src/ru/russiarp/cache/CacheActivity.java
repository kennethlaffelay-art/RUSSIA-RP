package ru.russiarp.cache;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;

public final class CacheActivity extends Activity {
    private static final ExecutorService WORK=Executors.newSingleThreadExecutor();
    private static final Object LOCK=new Object();
    private static boolean active=false, finished=false;
    private static String problem=null, phase="Подготовка кэша";
    private static long done=0,total=0,last=0;
    private static final String COMPLETE="layout-v4-"+CacheDownload.HASH;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private TextView title,details;
    private ProgressBar bar;
    private Button action;
    private boolean launched=false;
    private final Runnable tick=new Runnable() {
        public void run() { render(); if (!launched) ui.postDelayed(this,300); }
    };
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER_VERTICAL);
        int pad=(int)(24*getResources().getDisplayMetrics().density);layout.setPadding(pad,pad,pad,pad);
        title=new TextView(this);title.setTextSize(25);title.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        details=new TextView(this);details.setTextSize(16);details.setPadding(0,pad,0,pad);
        bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);bar.setMax(1000);
        action=new Button(this);action.setAllCaps(false);
        layout.addView(title);layout.addView(details);layout.addView(bar);layout.addView(action);
        setContentView(layout);
        action.setOnClickListener(v -> {
            if (!permitted()) { permissions();return; }
            synchronized(LOCK) {problem=null;}
            begin();
        });
    }
    private boolean permitted() {
        if (Build.VERSION.SDK_INT>=30) return Environment.isExternalStorageManager();
        return checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)==PackageManager.PERMISSION_GRANTED;
    }
    private void permissions() {
        if (Build.VERSION.SDK_INT>=30) {
            Intent i=new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                Uri.parse("package:"+getPackageName()));
            try { startActivity(i); } catch (ActivityNotFoundException e) {
                try {startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));}
                catch (ActivityNotFoundException ignored) {Toast.makeText(this,"Откройте настройки доступа к файлам для этого приложения",Toast.LENGTH_LONG).show();}
            }
        } else requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE},41);
    }
    @Override protected void onResume() {
        super.onResume();
        if (permitted()) begin();
        ui.removeCallbacks(tick);ui.post(tick);
    }
    @Override protected void onPause() {ui.removeCallbacks(tick);super.onPause();}
    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g) {
        super.onRequestPermissionsResult(r,p,g);
        if (r==41 && permitted()) begin();
    }
    private void begin() {
        synchronized(LOCK) {
            if (active || problem!=null || finished) return;
            active=true;phase="Подготовка кэша";done=total=0;
        }
        final Context context=getApplicationContext();
        WORK.execute(() -> {
            try { install(context); synchronized(LOCK) {finished=true;} }
            catch (Exception e) {
                synchronized(LOCK) {problem=e.getLocalizedMessage();if (problem==null) problem="Не удалось подготовить кэш";}
            } finally {synchronized(LOCK) {active=false;}}
        });
    }
    private static void progress(String label,long current,long max) {
        long now=SystemClock.elapsedRealtime();
        synchronized(LOCK) {
            if (now-last<180 && label.equals(phase) && current!=max) return;
            phase=label; done=current; total=max; last=now;
        }
    }
    private static void install(Context context) throws IOException {
        File shared=Environment.getExternalStorageDirectory().getCanonicalFile();
        File root=new File(shared,"Weik");
        File dir=context.getExternalFilesDir("russia-rp-cache");
        if (dir==null) throw new IOException("Внутренняя память недоступна");
        File part=new File(dir,"Rkkdev.zip.part");
        CacheFiles files=new CacheFiles(root,context.getAssets().open("russia-rp-cache.tsv"));
        SharedPreferences prefs=context.getSharedPreferences("russia-rp-cache",Context.MODE_PRIVATE);
        boolean marked=prefs.getBoolean(COMPLETE,false);
        if (files.complete(false,CacheActivity::progress) && (marked || files.complete(true,CacheActivity::progress))) {
            prefs.edit().putBoolean(COMPLETE,true).commit(); part.delete(); return;
        }
        files.clearInterruptedWrites();
        long free=new StatFs(dir.getPath()).getAvailableBytes();
        long need=Math.max(0,CacheDownload.BYTES-part.length())+files.missingBytes()+96L*1024*1024;
        if (free<need) throw new IOException(String.format(Locale.getDefault(),
            "Освободите ещё %.2f ГБ внутренней памяти.",(need-free)/1e9));
        CacheDownload.get(part,CacheActivity::progress);
        files.install(part,CacheActivity::progress);
        if (!files.complete(false,CacheActivity::progress)) throw new IOException("Не все файлы установлены");
        if (!prefs.edit().putBoolean(COMPLETE,true).commit()) throw new IOException("Не удалось сохранить состояние");
        part.delete();
    }
    private void render() {
        if (launched || isFinishing()) return;
        if (!permitted()) {
            title.setText("Доступ к игровому кэшу");
            details.setText("Игра хранит файлы в папке Weik. Разрешите доступ к файлам, чтобы клиент скачал с GitHub 1,49 ГБ. Для первой установки нужно около 5,6 ГБ свободного места.");
            action.setText("Разрешить доступ");action.setVisibility(View.VISIBLE);bar.setVisibility(View.GONE);return;
        }
        String text,error;long current,max;boolean ready;
        synchronized(LOCK) {text=phase;error=problem;current=done;max=total;ready=finished;}
        if (ready) {
            launched=true;
            synchronized(LOCK) {finished=false;}
            Intent i=new Intent();i.setClassName(this,"blackrussia.online.activities.SplashActivity");startActivity(i);finish();return;
        }
        if (error!=null) {
            title.setText("Подготовка кэша приостановлена");details.setText(error);
            bar.setVisibility(View.GONE);action.setVisibility(View.VISIBLE);action.setText("Продолжить");return;
        }
        title.setText(text);action.setVisibility(View.GONE);bar.setVisibility(View.VISIBLE);
        bar.setIndeterminate(max<=0);if (max>0) bar.setProgress((int)(1000.0*current/max));
        if (max==CacheDownload.BYTES) details.setText(String.format(Locale.getDefault(),"%.0f из %.0f МБ",current/1e6,max/1e6));
        else details.setText(max>0 ? current+" / "+max : "Проверяем файлы игры…");
    }
}
