package ru.russiarp.report;

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;
import android.os.Process;
import java.io.*;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.regex.*;

/** Keep bounded, app-specific breadcrumbs even if the game dies before it flushes its own log. */
public final class Events implements Application.ActivityLifecycleCallbacks {
    static final Pattern JAVA_FRAME = Pattern.compile("\\bat ([A-Za-z_$][A-Za-z0-9_.$<>]+)\\(([^() /]{1,120})\\)");
    static final Pattern EXCEPTION = Pattern.compile("\\b([a-zA-Z_$][a-zA-Z0-9_.$]*(?:Exception|Error))\\b");
    static final Pattern GAME_FRAME = Pattern.compile("(lib[A-Za-z0-9_.+-]+\\.so)\\s*\\+\\s*(0x[0-9a-fA-F]+|[0-9a-fA-F]{2,16})");
    static final Pattern RESOURCE = Pattern.compile("(?:^|[/ (])((?:TEXDB|DATA|AUDIO|MODELS|SAMP|ANIM)/[A-Za-z0-9/_.+ -]{1,180}\\.(?:dxt\\.(?:dat|toc)|dat|img|osw|ide|ipl|col|txd|ifp))\\b", Pattern.CASE_INSENSITIVE);
    static final Pattern HTTP = Pattern.compile("HTTP (\\d{3}); starting offset (\\d+)");
    static final Pattern GRAPHICS = Pattern.compile("\\b(EGL_[A-Z0-9_]+|GL_[A-Z0-9_]+|dequeueBuffer|queueBuffer|abandon(?:ed)?|surfaceCreated|surfaceDestroyed|surfaceChanged|SIGSEGV|SIGABRT|SIGBUS|SIGILL|SIGFPE|SEGV_MAPERR|SEGV_ACCERR)\\b",Pattern.CASE_INSENSITIVE);
    static final Pattern STAGE = Pattern.compile("\\b(init(?:ializ(?:e|ing|ed|ation))?|loading|loaded|starting|started|texture|renderer|streaming|connect(?:ed|ing)?|error|failed|fatal|timeout|onCreate|onStart|onResume|onPause|onStop|onDestroy)\\b",Pattern.CASE_INSENSITIVE);
    static String classify(String line) {
        Matcher m=JAVA_FRAME.matcher(line);
        if (m.find()) return "at " + m.group(1) + "(" + m.group(2) + ")";
        m=GAME_FRAME.matcher(line);
        if (m.find()) return m.group();
        m=HTTP.matcher(line);
        if (m.find()) return m.group();
        m=RESOURCE.matcher(line);
        if (m.find()) return (line.toLowerCase(Locale.ROOT).contains("not found") ? "missing " : "resource ") + m.group(1);
        m=EXCEPTION.matcher(line);
        if (m.find()) return m.group(1);
        m=GRAPHICS.matcher(line);
        if (m.find()) return m.group(1);
        m=STAGE.matcher(line);
        return m.find() ? m.group(1) : null;
    }

    private final File journal;
    private long written;
    private String last = "";
    private Events(Application app) {
        File dir = new File(app.getFilesDir(),"russia-diagnostics");
        dir.mkdirs();
        File[] files = dir.listFiles((d,n)->n.matches("run-[0-9]+-[0-9]+\\.txt"));
        if (files != null) {
            Arrays.sort(files, Comparator.comparing(File::getName).reversed());
            for (int i=6;i<files.length;i++) files[i].delete();
        }
        journal = new File(dir,"run-"+System.currentTimeMillis()+"-"+Process.myPid()+".txt");
    }
    public static void install(Application app) {
        try {
            Events events = new Events(app);
            app.registerActivityLifecycleCallbacks(events);
            events.record("process started");
            Thread reader = new Thread(events::capture,"client-crash-events");
            reader.setDaemon(true);
            reader.start();
        } catch (RuntimeException ignored) {}
    }
    private synchronized void record(String event) {
        if (event.equals(last)) return;
        try {
            // Keep the tail, including the moments immediately before a late crash.
            if (written >= 64*1024) {
                try (RandomAccessFile f=new RandomAccessFile(journal,"rw")) {
                    byte[] tail=new byte[(int)Math.min(32768,f.length())];
                    f.seek(f.length()-tail.length); f.readFully(tail);
                    int i=0; while(i<tail.length && tail[i++]!='\n') {}
                    f.seek(0); f.write(tail,i,tail.length-i); f.setLength(tail.length-i); written=f.length();
                }
            }
            try (FileOutputStream out=new FileOutputStream(journal,true)) {
                byte[] row=(System.currentTimeMillis()+" "+event+"\n").getBytes("UTF-8");
                out.write(row); written+=row.length; last=event;
            }
        } catch (IOException | SecurityException ignored) {}
    }
    private void capture() {
        String[] cmd = {"logcat","--pid="+Process.myPid(),"-T","1","-v","tag","RussiaCache:I","Multiplayer:I","AXL:I","NVEvent:I","SurfaceView:I","BLASTBufferQueue:W","OpenGLRenderer:W","libEGL:W","AndroidRuntime:E","libc:F","*:S"};
        java.lang.Process child=null;
        try {
            child=new ProcessBuilder(cmd).redirectErrorStream(true).start();
            try (BufferedReader in=new BufferedReader(new InputStreamReader(child.getInputStream(),"UTF-8"))) {
                String line;
                while ((line=in.readLine())!=null) {
                    int sep=line.indexOf(':');
                    if(sep<1 || sep>64) continue;
                    String tag=line.substring(0,sep).trim();
                    if (!tag.matches("[A-Z]/[A-Za-z0-9_ ]+")) continue;
                    String event=classify(line.substring(sep+1));
                    if(event!=null) record(tag+" "+event);
                }
            }
        } catch (IOException | SecurityException ignored) {} finally { if(child!=null)child.destroy(); }
    }
    private void lifecycle(Activity a,String event) { record(a.getClass().getSimpleName()+" "+event); }
    public void onActivityCreated(Activity a,Bundle b){ lifecycle(a,"created"); }
    public void onActivityStarted(Activity a){ lifecycle(a,"started"); }
    public void onActivityResumed(Activity a){ lifecycle(a,"resumed"); }
    public void onActivityPaused(Activity a){ lifecycle(a,"paused"); }
    public void onActivityStopped(Activity a){ lifecycle(a,"stopped"); }
    public void onActivityDestroyed(Activity a){ lifecycle(a,"destroyed"); }
    public void onActivitySaveInstanceState(Activity a,Bundle b){}
}
