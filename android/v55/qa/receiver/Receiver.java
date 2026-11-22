package ru.russiarp.testshare;
import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import java.io.*;
import java.util.*;
import java.util.zip.*;
public class Receiver extends Activity {
    public void onCreate(Bundle saved) {
        super.onCreate(saved);
        try {
            Intent i=getIntent();
            Uri uri=i.getParcelableExtra(Intent.EXTRA_STREAM);
            if(!"application/zip".equals(i.getType()) || !"content".equals(uri.getScheme()))throw new IOException();
            Map<String,String> entries=new HashMap<>();
            try(ZipInputStream z=new ZipInputStream(getContentResolver().openInputStream(uri))) {
                ZipEntry e; byte[] buf=new byte[4096];
                while((e=z.getNextEntry())!=null) {
                    ByteArrayOutputStream out=new ByteArrayOutputStream();
                    int n; while((n=z.read(buf))!=-1)out.write(buf,0,n);
                    entries.put(e.getName(),out.toString("UTF-8"));
                }
            }
            String report=entries.get("report.txt");
            if(report==null || !report.contains("version=1.6.7"))throw new IOException("metadata");
            String mode=report.contains("last_crash_ms=")?"crash":"clean";
            if(mode.equals("crash")){
                if(!entries.get("native-stack.txt").contains("SIGSEGV"))throw new IOException("stack");
                if(!entries.get("events-before-crash.txt").contains("MainActivity resumed"))throw new IOException("breadcrumbs");
                if(!entries.get("game/reBRClientLog.txt").contains("fixture.dxt.dat"))throw new IOException("game log");
                for(String s:entries.values())if(s.contains("SECRET_QA"))throw new IOException("private string");
            }
            if(!entries.containsKey("events-latest-session.txt"))throw new IOException("no recent lifecycle");
            Log.i("ShareProbe","RECEIVED "+mode);
        } catch(Exception e){Log.e("ShareProbe","FAILED "+e.getClass().getSimpleName()+":"+e.getMessage());}
        finish();
    }
}
