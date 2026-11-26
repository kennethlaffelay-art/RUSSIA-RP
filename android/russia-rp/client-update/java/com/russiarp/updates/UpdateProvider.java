package com.russiarp.updates;

import android.app.*;
import android.content.*;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.widget.Toast;
import androidx.core.content.FileProvider;
import java.io.*;
import java.net.URL;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class UpdateProvider extends FileProvider {
    @Override public boolean onCreate() {
        boolean ready=super.onCreate();
        Context c=getContext();
        Context application=c instanceof Application ? c : c==null ? null : c.getApplicationContext();
        if(application instanceof Application) {
            Application app=(Application)application;
            app.registerActivityLifecycleCallbacks(new Updates(app));
        }
        return ready;
    }

    private static final class Updates implements Application.ActivityLifecycleCallbacks {
        final Application app;
        final SharedPreferences prefs;
        final Handler ui=new Handler(Looper.getMainLooper());
        final ExecutorService io=Executors.newSingleThreadExecutor();
        final File dir;
        Activity launcher;
        AlertDialog dialog;
        Releases.Build build;
        File verified;
        boolean busy, settingsOpen;
        long nextCheck;
        Updates(Application app) {
            this.app=app;
            prefs=app.getSharedPreferences("rrp_client_updates",Context.MODE_PRIVATE);
            dir=new File(app.getCacheDir(),"rrp-client");
        }
        @Override public void onActivityResumed(Activity a) {
            if(!a.getClass().getName().equals("blackrussia.online.activities.MainActivity")) return;
            launcher=a;
            if(settingsOpen) {
                settingsOpen=false;
                if(verified!=null && app.getPackageManager().canRequestPackageInstalls()) {
                    launchInstaller(); return;
                }
                defer(); return;
            }
            refresh();
        }
        @Override public void onActivityPaused(Activity a) {
            if(launcher!=a) return;
            launcher=null;
            if(dialog!=null) {dialog.dismiss();dialog=null;}
        }
        @Override public void onActivityCreated(Activity a,Bundle s) {}
        @Override public void onActivityStarted(Activity a) {}
        @Override public void onActivityStopped(Activity a) {}
        @Override public void onActivitySaveInstanceState(Activity a,Bundle s) {}
        @Override public void onActivityDestroyed(Activity a) {if(launcher==a) onActivityPaused(a);}

        private boolean deferred() {
            return build!=null && build.sha.equals(prefs.getString("defer_sha","")) && prefs.getLong("defer_until",0)>System.currentTimeMillis();
        }
        private void defer() {
            if(build!=null) prefs.edit().putString("defer_sha",build.sha).putLong("defer_until",System.currentTimeMillis()+6*60*60*1000L).apply();
        }
        private boolean active() {return launcher!=null && !launcher.isFinishing() && !launcher.isDestroyed();}
        private Releases.Build cached(String current) {
            String version=prefs.getString("version",""),sha=prefs.getString("sha","");
            long size=prefs.getLong("size",0);
            if(Releases.VERSION.matcher(version).matches() && Releases.compare(version,current)>0 && sha.matches("[0-9a-f]{64}") && size>0 && size<=Releases.MAX_APK)
                return new Releases.Build(version,sha,size);
            return null;
        }
        private void refresh() {
            if(busy || dialog!=null || !active()) return;
            if(build!=null) { if(!deferred()) present(); return; }
            if(SystemClock.elapsedRealtime()<nextCheck) return;
            busy=true;
            io.execute(()->{
                Releases.Build candidate=null; File file=null; boolean checked=false;
                try {
                    String current=app.getPackageManager().getPackageInfo(app.getPackageName(),0).versionName;
                    Releases.Build saved=cached(current);
                    try {candidate=Releases.newest(current); checked=true;}
                    catch(Exception e) {candidate=saved;}
                    if(candidate!=null) {
                        prefs.edit().putString("version",candidate.version).putString("sha",candidate.sha).putLong("size",candidate.size).apply();
                        File existing=new File(dir,candidate.sha+".apk");
                        if(Releases.valid(existing,candidate)) {
                            verifyPackage(existing,candidate); file=existing;
                        }
                    }
                    // Remove only files created by this updater, including the already installed version.
                    File[] old=dir.listFiles();
                    if(old!=null && (checked || candidate!=null)) for(File f:old)
                        if(f.getName().matches("[0-9a-f]{64}\\.(apk|part)") && (candidate==null || !f.getName().startsWith(candidate.sha+"."))) f.delete();
                } catch(Exception e) {android.util.Log.w("RUSSIA-RP","Client update check",e);}
                final Releases.Build result=candidate; final File local=file; final boolean success=checked;
                ui.post(()->{
                    build=result;verified=local;busy=false;
                    nextCheck=SystemClock.elapsedRealtime()+(success?15*60*1000L:60*1000L);
                    if(active() && build!=null && !deferred()) present();
                });
            });
        }
        private void present() {
            if(!active() || busy || dialog!=null || deferred()) return;
            if(verified!=null) {
                offer("Обновление готово","RUSSIA RP "+build.version+" загружена и проверена. Установить обновление?","Установить",this::install);
                return;
            }
            ConnectivityManager cm=(ConnectivityManager)app.getSystemService(Context.CONNECTIVITY_SERVICE);
            if(cm==null || cm.getActiveNetwork()==null) return;
            if(!cm.isActiveNetworkMetered()) download();
            else offer("Обновление RUSSIA RP",String.format(Locale.getDefault(),"Версия %s · %.1f МБ. Загрузить через текущее соединение?",build.version,build.size/1048576.0),"Скачать",this::download);
        }
        private void offer(String title,String message,String yes,Runnable action) {
            if(!active()) return;
            dialog=new AlertDialog.Builder(launcher).setTitle(title).setMessage(message)
                .setPositiveButton(yes,(d,w)->{dialog=null; action.run();})
                .setNegativeButton("Позже",(d,w)->{dialog=null;defer();})
                .setOnCancelListener(d->{dialog=null;defer();}).create();
            dialog.show();
        }
        private void download() {
            if(busy || build==null || !active()) return;
            final Releases.Build target=build;
            busy=true;
            Toast.makeText(app,"Загружается обновление RUSSIA RP "+target.version,Toast.LENGTH_SHORT).show();
            io.execute(()->{
                File result=null;
                try {
                    File f=Releases.fetch(dir,target,offset->Releases.connect(new URL(target.url),offset));
                    try {verifyPackage(f,target);} catch(Exception e) {f.delete();throw e;}
                    result=f;
                } catch(Exception e) {android.util.Log.w("RUSSIA-RP","Client update download",e);}
                final File local=result;
                ui.post(()->{
                    busy=false;verified=local;
                    if(!active()) return;
                    if(local!=null) present();
                    else offer("Загрузка прервана","Проверьте соединение и свободное место. Загрузить обновление ещё раз?","Повторить",this::download);
                });
            });
        }
        @SuppressWarnings("deprecation")
        private void verifyPackage(File apk,Releases.Build target) throws Exception {
            PackageManager pm=app.getPackageManager();
            PackageInfo old=pm.getPackageInfo(app.getPackageName(),PackageManager.GET_SIGNATURES);
            PackageInfo update=pm.getPackageArchiveInfo(apk.getAbsolutePath(),PackageManager.GET_SIGNATURES);
            if(update==null || !old.packageName.equals(update.packageName) || !target.version.equals(update.versionName) ||
               code(update)<=code(old) || old.signatures==null || old.signatures.length==0 || update.signatures==null ||
               !new HashSet<>(Arrays.asList(old.signatures)).equals(new HashSet<>(Arrays.asList(update.signatures))))
                throw new IOException("APK package, version or signer mismatch");
        }
        @SuppressWarnings("deprecation") private static long code(PackageInfo p) {
            return Build.VERSION.SDK_INT>=28 ? p.getLongVersionCode() : p.versionCode;
        }
        private void install() {
            if(!active() || verified==null) return;
            if(!app.getPackageManager().canRequestPackageInstalls()) {
                settingsOpen=true;
                try {launcher.startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+app.getPackageName())));}
                catch(ActivityNotFoundException | SecurityException e) {settingsOpen=false; installFailed();}
            } else launchInstaller();
        }
        private void launchInstaller() {
            if(!active() || verified==null) return;
            try {
                Uri uri=FileProvider.getUriForFile(app,app.getPackageName()+".provider",verified);
                Intent i=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive");
                i.setClipData(ClipData.newRawUri("RUSSIA RP",uri));
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                launcher.startActivity(i);
                defer(); // Returning from a cancelled system installer must not reopen it in a loop.
            } catch(ActivityNotFoundException | SecurityException | IllegalArgumentException e) {installFailed();}
        }
        private void installFailed() {
            if(active()) offer("Установка обновления","Android не открыл установщик. Проверьте разрешение на установку приложений для RUSSIA RP.","Повторить",this::install);
        }
    }
}
