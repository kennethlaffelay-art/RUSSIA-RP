package ru.russiarp.report;

import android.app.ActivityManager;
import android.app.ApplicationExitInfo;
import android.content.Context;
import android.os.Build;
import android.os.Environment;
import android.os.Process;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.regex.*;
import java.util.zip.*;

public final class Reports {
    private static final Pattern SAVED = Pattern.compile("crash-(native|java)-([0-9]{13})\\.(txt|tombstone\\.pb)");
    private static final Pattern RUN = Pattern.compile("run-([0-9]+)-([0-9]+)\\.txt");
    private static final int DUMP_LIMIT = 12*1024*1024;
    private static final class Incident {
        long time;
        String kind = "";
        String system = "";
        int pid;
        File dump, java;
        byte[] systemDump;
    }
    private static void system(Context c, Incident crash) {
        if (Build.VERSION.SDK_INT < 30) return;
        try {
            ActivityManager am=(ActivityManager)c.getSystemService(Context.ACTIVITY_SERVICE);
            for(ApplicationExitInfo e : am.getHistoricalProcessExitReasons(c.getPackageName(),0,32)) {
                int reason=e.getReason();
                if(!c.getPackageName().equals(e.getProcessName()) || (reason!=ApplicationExitInfo.REASON_CRASH_NATIVE && reason!=ApplicationExitInfo.REASON_CRASH && reason!=ApplicationExitInfo.REASON_ANR)) continue;
                if(e.getTimestamp()<crash.time) break;
                if(e.getTimestamp()>crash.time){crash.dump=null; crash.java=null;}
                crash.time=e.getTimestamp();
                crash.kind=reason==ApplicationExitInfo.REASON_CRASH_NATIVE?"native":reason==ApplicationExitInfo.REASON_ANR?"ANR":"java";
                crash.system="reason="+reason+" status="+e.getStatus()+" importance="+e.getImportance();
                crash.pid=e.getPid();
                if(crash.kind.equals("native") && crash.dump==null && Build.VERSION.SDK_INT>=31) {
                    try(InputStream in=e.getTraceInputStream()) { if(in!=null)crash.systemDump=read(in,DUMP_LIMIT); }
                }
                break;
            }
        } catch (IOException | RuntimeException ignored) {}
    }
    private static byte[] read(InputStream in,int limit) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        byte[] buf=new byte[8192]; int n;
        while((n=in.read(buf))!=-1){
            if(out.size()>limit-n) throw new IOException("Input too large");
            out.write(buf,0,n);
        }
        return out.toByteArray();
    }
    private static void scan(File dir, Incident crash) {
        File[] files=dir.listFiles();
        if(files==null)return;
        for(File f:files){
            Matcher m=SAVED.matcher(f.getName());
            if(!m.matches() || !safe(dir,f))continue;
            long time=Long.parseLong(m.group(2));
            if(time<crash.time || time>System.currentTimeMillis()+60000)continue;
            if(time>crash.time){crash.dump=null;crash.java=null;}
            crash.time=time; crash.kind=m.group(1);
            if("tombstone.pb".equals(m.group(3)))crash.dump=f;
            if(crash.kind.equals("java"))crash.java=f;
        }
    }
    private static boolean safe(File dir, File f) {
        try { return f.isFile() && !Files.isSymbolicLink(f.toPath()) && f.getCanonicalPath().startsWith(dir.getCanonicalPath()+File.separator); }
        catch(IOException | SecurityException e){ return false; }
    }
    private static void entry(ZipOutputStream zip,String name,String text) throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(text.getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
    }
    private static String tail(File f,int max) throws IOException {
        try(RandomAccessFile in=new RandomAccessFile(f,"r")){
            long pos=Math.max(0,in.length()-max);
            in.seek(pos);
            byte[] buf=new byte[(int)Math.min(max,in.length()-pos)];
            int n=in.read(buf);
            if(n<=0)return "";
            String text=new String(buf,0,n,StandardCharsets.UTF_8);
            return pos==0?text:text.substring(text.indexOf('\n')+1);
        }
    }
    private static String filtered(File f) throws IOException {
        StringBuilder out=new StringBuilder(); String previous="";
        for(String line:tail(f,128*1024).split("\n")){
            String event=Events.classify(line);
            if(event!=null && !event.equals(previous)){out.append(event).append('\n');previous=event;}
        }
        return out.toString();
    }
    private static void sessionLogs(Context c, Incident crash, ZipOutputStream zip) throws IOException {
        File dir=new File(c.getFilesDir(),"russia-diagnostics");
        File[] files=dir.listFiles();
        if(files==null) return;
        File incident=null,latest=null; long best=0,last=0;
        for(File f:files){
            Matcher m=RUN.matcher(f.getName());
            if(!m.matches() || !safe(dir,f))continue;
            long start=Long.parseLong(m.group(1));
            if(start>last){last=start;latest=f;}
            if(start<=crash.time && start>best && (crash.pid==0 || Integer.parseInt(m.group(2))==crash.pid)){
                best=start;incident=f;
            }
        }
        if(incident!=null) entry(zip,"events-before-crash.txt",tail(incident,65536));
        if(latest!=null && !latest.equals(incident))entry(zip,"events-latest-session.txt",tail(latest,65536));
    }
    public static synchronized File create(Context c) throws Exception {
        File dir=new File(c.getCacheDir(),"share-reports");
        if(!dir.isDirectory() && !dir.mkdirs())throw new IOException("Missing directory");
        File[] old=dir.listFiles();
        if(old!=null)for(File f:old)if(f.lastModified()<System.currentTimeMillis()-7L*86400000)f.delete();
        Incident crash=new Incident();
        File external=c.getExternalFilesDir(null);
        if(external!=null)scan(new File(external,"Weik"),crash);
        scan(new File(c.getFilesDir(),"Weik"),crash);
        system(c,crash);
        File tmp=File.createTempFile("building-", ".part",dir);
        try {
            try(ZipOutputStream zip=new ZipOutputStream(new FileOutputStream(tmp))){
                StringBuilder info=new StringBuilder();
                info.append("package=").append(c.getPackageName()).append("\nversion=").append(c.getPackageManager().getPackageInfo(c.getPackageName(),0).versionName)
                    .append("\nAndroid=").append(Build.VERSION.RELEASE).append(" API ").append(Build.VERSION.SDK_INT)
                    .append("\ndevice=").append(Build.MANUFACTURER).append(" ").append(Build.MODEL)
                    .append("\nprocess_bits=").append(Process.is64Bit()?64:32).append("\nabis=").append(Arrays.toString(Build.SUPPORTED_ABIS))
                    .append("\npage_bytes=").append(Os.sysconf(OsConstants._SC_PAGESIZE)).append('\n');
                if(crash.time>0)info.append("last_crash_ms=").append(crash.time).append("\ntype=").append(crash.kind).append('\n').append(crash.system).append('\n');
                else info.append("No recorded crash for this app.\n");
                if(crash.dump!=null || crash.systemDump!=null){
                    try {
                        byte[] dump=crash.systemDump;
                        if(dump==null)try(InputStream in=new FileInputStream(crash.dump)){dump=read(in,DUMP_LIMIT);}
                        String stack=NativeStack.summarize(dump);
                        entry(zip,"native-stack.txt",stack);
                    } catch(IOException e){info.append("Native trace unavailable.\n");}
                }
                if(crash.java!=null){
                    String stack=filtered(crash.java);
                    if(!stack.isEmpty())entry(zip,"java-stack.txt",stack);
                }
                sessionLogs(c,crash,zip);
                File gameDir=new File(Environment.getExternalStorageDirectory(),"Weik");
                String[] paths={"reBRClientLog.txt","SAMP/crash_log.log","SAMP/samp_log.txt"};
                for(String name:paths){
                    File f=new File(gameDir,name);
                    if(!safe(gameDir,f) || f.length()==0)continue;
                    if(crash.time>0 && Math.abs(f.lastModified()-crash.time)>600000)continue;
                    try {
                        String events=filtered(f);
                        if(!events.isEmpty())entry(zip,"game/"+f.getName(),events);
                    } catch(IOException | SecurityException ignored){}
                }
                entry(zip,"report.txt",info.toString());
            }
            File result=new File(dir,"RUSSIA-crash-"+System.currentTimeMillis()+"-"+UUID.randomUUID().toString().substring(0,8)+".zip");
            if(!tmp.renameTo(result))throw new IOException("Incomplete report");
            return result;
        } finally {tmp.delete();}
    }
}
