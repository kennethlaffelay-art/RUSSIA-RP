package ru.russiarp.install;

import android.app.Activity;
import android.os.AsyncTask;
import android.os.Environment;
import android.os.StatFs;
import android.os.SystemClock;
import android.util.Log;
import android.view.View;
import android.widget.TextView;
import com.akexorcist.roundcornerprogressbar.RoundCornerProgressBar;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;

public final class StockCache {
    static final long BYTES=1488865990L;
    static final String HASH="1cdd9c76725fdd1ab07f196a9e5fdcafd5c5808ba883f71701cfa5e0d33d77ea";
    static final String URL="https://github.com/kennethlaffelay-art/RUSSIA-RP/releases/download/client-v5-play-1cdd9c76725fdd1ab07f196a9e5fdcafd5c58/Rkkdev.zip";
    private static final Map<AsyncTask<?,?,?>,String> errors=Collections.synchronizedMap(new WeakHashMap<>());
    private final AsyncTask<?,?,?> task;
    private final Activity activity;
    private final TextView label, percentage;
    private final RoundCornerProgressBar bar;
    private String phase="";
    private long lastDisplay;
    private int lastPercent=-1;
    private final byte[] buffer=new byte[256*1024];
    private final File root;
    StockCache(Activity a,AsyncTask<?,?,?> t) throws IOException {
        activity=a;task=t;
        root=new File(Environment.getExternalStorageDirectory().getCanonicalFile(),"Weik");
        if (!root.getAbsolutePath().equals(root.getCanonicalPath())) throw new IOException("Проверьте путь к папке Weik");
        label=a.findViewById(id(a,"loadingText")); percentage=a.findViewById(id(a,"loadingPercent"));
        bar=a.findViewById(id(a,"progressBar"));
    }
    private static int id(Activity a,String key){return a.getResources().getIdentifier(key,"id",a.getPackageName());}
    public static Integer run(Activity a,AsyncTask<?,?,?> t){
        try {
            new StockCache(a,t).install();
            return 1;
        } catch(Exception failure) {
            String reason=failure.getLocalizedMessage();
            if (reason==null || reason.trim().isEmpty()) reason="Не удалось записать кэш. Проверьте свободное место и доступ к файлам.";
            if (failure instanceof SecurityException || failure instanceof AccessDeniedException) reason="Нет доступа к папке Weik. Разрешите доступ к файлам и нажмите «Повторить».";
            if (reason.contains("ENOSPC") || reason.toLowerCase(Locale.ROOT).contains("no space left")) reason="Недостаточно места. Освободите память и нажмите «Повторить».";
            errors.put(t,reason);
            Log.w("RussiaCache",failure.getClass().getSimpleName()+": "+reason);
            return 0;
        }
    }
    public static void showFailure(Activity a,AsyncTask<?,?,?> t) {
        TextView msg=a.findViewById(id(a,"loadingText"));
        String reason=errors.remove(t);
        msg.setText(reason==null?"Установка прервана. Нажмите «Повторить».":reason);
        a.findViewById(id(a,"loadingPercent")).setVisibility(View.INVISIBLE);
        a.findViewById(id(a,"progressBar")).setVisibility(View.INVISIBLE);
    }
    private void cancelled() throws InterruptedIOException {
        if(task.isCancelled() || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Установка приостановлена");
    }
    private void status(String text,long done,long max) throws IOException {
        cancelled();
        int pct=max<=0?0:(int)Math.min(100,100.0*done/max);
        long now=SystemClock.elapsedRealtime();
        if(text.equals(phase) && (pct==lastPercent || (now-lastDisplay<200 && pct!=100)))return;
        phase=text;lastDisplay=now;lastPercent=pct;
        activity.runOnUiThread(()->{
            if(task.isCancelled()||activity.isFinishing()||activity.isDestroyed())return;
            label.setText(text);percentage.setVisibility(View.VISIBLE);percentage.setText(pct+"%");
            bar.setVisibility(View.VISIBLE);bar.setProgress(pct);
        });
    }
    private static void needSpace(File here,long need) throws IOException {
        long available=new StatFs(here.getAbsolutePath()).getAvailableBytes();
        long deficit=need+64L*1024*1024-available;
        if(deficit>0)throw new IOException(String.format(Locale.getDefault(),"Освободите ещё %.2f ГБ внутренней памяти и нажмите «Повторить».",Math.max(.01,Math.ceil(deficit/1e7)/100.0)));
    }
    private static void move(File src,File dst)throws IOException {
        try {Files.move(src.toPath(),dst.toPath(),StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);}
        catch(AtomicMoveNotSupportedException ex){Files.move(src.toPath(),dst.toPath(),StandardCopyOption.REPLACE_EXISTING);}
    }
    private File target(String relative)throws IOException {
        File f=new File(root,relative);
        if(!f.getAbsolutePath().equals(f.getCanonicalPath())||!f.getCanonicalPath().startsWith(root.getPath()+"/"))throw new IOException("Недопустимый путь к файлу кэша");
        return f;
    }
    private boolean valid(File f,long length,long expectedCrc,boolean personal,boolean fast)throws IOException {
        if(!f.isFile())return false;
        if(personal && f.length()>0)return true;
        if(f.length()!=length)return false;
        if(fast)return true;
        CRC32 crc=new CRC32();
        try(InputStream in=new FileInputStream(f)){for(int n;(n=in.read(buffer))!=-1;){cancelled();crc.update(buffer,0,n);}}
        catch (FileNotFoundException missing) { return false; }
        return crc.getValue()==expectedCrc;
    }
    private static class Entry {
        final String name; final File file; final long size,crc;
        Entry(String n,File f,long s,long c){name=n;file=f;size=s;crc=c;}
    }
    private static String enginePath(String archivedPath) {
        if (archivedPath.startsWith("data/Decision/Allowed/"))
            return "data/decision/allowed/" + archivedPath.substring("data/Decision/Allowed/".length());
        if (archivedPath.startsWith("data/Decision/"))
            return "data/decision/" + archivedPath.substring("data/Decision/".length());
        if (archivedPath.startsWith("texdb/") && archivedPath.endsWith(".img"))
            return archivedPath.toUpperCase(Locale.ROOT);
        if (archivedPath.startsWith("audio/CONFIG/"))
            return archivedPath.toUpperCase(Locale.ROOT);
        if (archivedPath.startsWith("audio/"))
            return "AUDIO/" + archivedPath.substring("audio/".length());
        return archivedPath;
    }
    private void copyVerified(Entry entry, File source) throws IOException {
        Files.createDirectories(entry.file.getParentFile().toPath());
        needSpace(entry.file.getParentFile(), entry.size);
        Path temp = Files.createTempFile(entry.file.getParentFile().toPath(), ".russia-install-", ".tmp");
        try {
            Files.copy(source.toPath(), temp, StandardCopyOption.REPLACE_EXISTING);
            if (!valid(temp.toFile(), entry.size, entry.crc, false, false))
                throw new IOException("Не удалось проверить файл " + entry.name);
            move(temp.toFile(), entry.file);
        } catch (IOException problem) {
            throw new IOException("Не удалось установить " + entry.name + " из " + source.getName() + ": " + problem.getMessage(), problem);
        } finally {
            Files.deleteIfExists(temp);
        }
    }
    private static long controlCRC(String name) {
        if (name.equals("data/gta.dat") || name.equals("SAMP/gta.dat")) return 235165133L;
        if (name.equals("data/default.dat")) return 3498633815L;
        return -1;
    }
    private static boolean canCheckSizeOnly(String archivedPath) {
        return !archivedPath.startsWith("data/maps/")
                && !archivedPath.startsWith("models/coll/")
                && controlCRC(archivedPath) == -1;
    }
    private void prepareMapList(String path, String name) throws IOException {
        File config = target(path);
        long originalCRC = name.equals("gta") ? 627678493L : 2115274958L;
        if (!valid(config, config.length(), originalCRC, false, false)) return;
        Path stage = Files.createTempFile(config.getParentFile().toPath(), ".russia-map-", ".tmp");
        try (InputStream in = activity.getAssets().open("russia-" + name + ".dat")) {
            Files.copy(in, stage, StandardCopyOption.REPLACE_EXISTING);
            move(stage.toFile(), config);
        } finally {
            Files.deleteIfExists(stage);
        }
    }
    private void installEnginePaths(boolean fast) throws IOException {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                activity.getAssets().open("russia-engine-paths.tsv"), "UTF-8"))) {
            for (String row; (row = reader.readLine()) != null;) {
                String[] fields = row.split("\\t", -1);
                if (fields.length != 4) throw new IOException("Повреждён список путей движка");
                File destination = target(fields[1]);
                long size = Long.parseLong(fields[2]);
                long crc = Long.parseLong(fields[3]);
                if (!valid(destination, size, crc, false, fast && canCheckSizeOnly(fields[0])))
                    copyVerified(new Entry(fields[1], destination, size, crc), target(fields[0]));
            }
        }
    }
    private void copyBytes(InputStream in, OutputStream out, long bytes) throws IOException {
        while (bytes > 0) {
            cancelled();
            int count = in.read(buffer, 0, (int) Math.min(buffer.length, bytes));
            if (count < 0) throw new EOFException("Неполная база текстур");
            if (out != null) out.write(buffer, 0, count);
            bytes -= count;
        }
    }
    private void prepareCloudTexture() throws IOException {
        File data = target("texdb/txd/txd.dxt.dat");
        File index = target("texdb/txd/txd.dxt.toc");
        if (data.length() == 36256714L && valid(data, 36256714L, 2414866815L, false, false)) {
            needSpace(data.getParentFile(), 36604194L);
            Path temp = Files.createTempFile(data.getParentFile().toPath(), ".txd-", ".tmp");
            try {
                try (InputStream in = new FileInputStream(data); OutputStream out = Files.newOutputStream(temp);
                     InputStream record = new GZIPInputStream(activity.getAssets().open("russia-cloud-record.gz"))) {
                    copyBytes(in, out, 11990046L + 8);
                    copyBytes(in, null, 4 + 2056);
                    copyBytes(record, out, 349540);
                    copyBytes(in, out, 36256714L - 11990046L - 12 - 2056);
                }
                if (!valid(temp.toFile(), 36604194L, 1177694875L, false, false))
                    throw new IOException("Не удалось проверить базу текстур");
                move(temp.toFile(), data);
            } finally { Files.deleteIfExists(temp); }
        }
        if (data.length() == 36604194L && valid(index, 2760, 2582281193L, false, false)) {
            Path temp = Files.createTempFile(index.getParentFile().toPath(), ".txd-index-", ".tmp");
            try (InputStream in = activity.getAssets().open("russia-cloud-index")) {
                Files.copy(in, temp, StandardCopyOption.REPLACE_EXISTING);
                if (!valid(temp.toFile(), 2760, 4041003183L, false, false))
                    throw new IOException("Не удалось проверить индекс текстур");
                move(temp.toFile(), index);
            } finally { Files.deleteIfExists(temp); }
        }
    }
    private void installTextureList() throws IOException {
        File list = target("loader/texdbs.cfg");
        Files.createDirectories(list.getParentFile().toPath());
        // Keep an existing hand-configured database list.
        if (list.isFile() && list.length() > 0) return;
        java.nio.file.Path staged = Files.createTempFile(list.getParentFile().toPath(), ".texdbs-", ".tmp");
        try (InputStream in = activity.getAssets().open("russia-texdbs.cfg")) {
            Files.copy(in, staged, StandardCopyOption.REPLACE_EXISTING);
            move(staged.toFile(), list);
        } finally {
            Files.deleteIfExists(staged);
        }
    }
    private void install()throws Exception {
        File dir=activity.getExternalFilesDir("russia-cache-v52");
        if(dir==null)throw new IOException("Память телефона недоступна");
        File part=new File(dir,"Rkkdev.zip.part");
        // All work stays under our cache or the exact managed game filenames.
        File marker=target(".russia-cache-"+HASH.substring(0,16));
        File previous=new File(root.getParentFile(),"Weik.previous");
        if(!root.exists() && previous.isDirectory() && previous.getAbsolutePath().equals(previous.getCanonicalPath()))
            Files.move(previous.toPath(),root.toPath());
        Files.createDirectories(root.toPath());
        boolean fast=marker.isFile();
        List<Entry> needed=new ArrayList<>(); long growth=0, extra=0,total=0;
        status("Проверка файлов игры…",0,1);
        try(BufferedReader r=new BufferedReader(new InputStreamReader(activity.getAssets().open("russia-cache-v52.tsv"),"UTF-8"))){
            for(String line;(line=r.readLine())!=null;){
                String[] row=line.split("\\t",-1);
                if(row.length!=4)throw new IOException("Повреждён список файлов");
                String archivedPath=row[0];
                String gamePath=enginePath(archivedPath);
                File f=target(gamePath);long n=Long.parseLong(row[1]),crc=Long.parseLong(row[2]);
                File pending=new File(f.getParentFile(),".russia-v52-"+f.getName()+".part");
                Files.deleteIfExists(pending.toPath());
                boolean migrated=!gamePath.equals(archivedPath);
                if (archivedPath.equals("texdb/txd/txd.dxt.dat") && valid(f,36604194L,1177694875L,false,fast)) continue;
                if (archivedPath.equals("texdb/txd/txd.dxt.toc") && valid(f,2760,4041003183L,false,false)) continue;
                long configuredCRC = controlCRC(archivedPath);
                if (configuredCRC != -1 && valid(f, n, configuredCRC, false, false)) continue;
                if(valid(f,n,crc,row[3].equals("1"),fast && !migrated && canCheckSizeOnly(archivedPath)))continue;
                Entry entry = new Entry(archivedPath, f, n, crc);
                if(migrated) {
                    File previousFile = target(archivedPath);
                    if(valid(previousFile,n,crc,false,false)) {
                        if (archivedPath.startsWith("texdb/") && archivedPath.endsWith(".img")) {
                            Files.createDirectories(f.getParentFile().toPath());
                            move(previousFile, f);
                        } else {
                            copyVerified(entry, previousFile);
                        }
                        continue;
                    }
                }
                needed.add(entry);total+=n;
                growth+=Math.max(0,n-f.length());extra=Math.max(extra,Math.min(n,f.length()));
            }
        }
        if(!needed.isEmpty()){
            Files.deleteIfExists(marker.toPath());
            if(part.length()>BYTES)Files.delete(part.toPath());
            needSpace(dir, Math.max(0,BYTES-part.length())+growth+extra);
            download(part);
            checkHash(part);
            long done=0;
            try(ZipFile archive=new ZipFile(part)){
                for(Entry e:needed){
                    ZipEntry z=archive.getEntry("Rkkdev/"+e.name);
                    if(z==null||z.getSize()!=e.size||z.getCrc()!=e.crc)throw new IOException("Архив не соответствует версии клиента: "+e.name);
                    Files.createDirectories(e.file.getParentFile().toPath());
                    File pending=new File(e.file.getParentFile(),".russia-v52-"+e.file.getName()+".part");
                    CRC32 crc=new CRC32();long actual=0;
                    try {
                        Files.createFile(pending.toPath());
                        try(InputStream in=archive.getInputStream(z); OutputStream out=new FileOutputStream(pending)){
                            for(int n;(n=in.read(buffer))!=-1;){out.write(buffer,0,n);crc.update(buffer,0,n);actual+=n;status("Распаковка файлов игры…",done+actual,total);}
                        }
                        if(actual!=e.size||crc.getValue()!=e.crc)throw new IOException("Не удалось проверить файл "+e.name);
                        move(pending,e.file);
                    } finally {Files.deleteIfExists(pending.toPath());}
                    done+=actual;
                }
            }
        }
        prepareMapList("data/gta.dat", "gta");
        prepareMapList("SAMP/gta.dat", "gta");
        prepareMapList("data/default.dat", "default");
        installEnginePaths(fast);
        prepareCloudTexture();
        installTextureList();
        File guiTable = target("texdb/gui/gui.dxt.toc");
        if (!guiTable.isFile() || guiTable.length() == 0) {
            File guiData = target("texdb/gui/gui.dxt.dat");
            if (valid(guiData, 26178482L, 470212590L, false, false)) {
                Path temp = Files.createTempFile(guiTable.getParentFile().toPath(), ".gui-index-", ".tmp");
                try (InputStream in = activity.getAssets().open("russia-gui.dxt.toc")) {
                    Files.copy(in, temp, StandardCopyOption.REPLACE_EXISTING);
                    move(temp.toFile(), guiTable);
                } finally {
                    Files.deleteIfExists(temp);
                }
            }
        }
        if(!marker.isFile())Files.createFile(marker.toPath());
        Files.deleteIfExists(part.toPath());
        status("Файлы игры готовы",1,1);
    }
    private void download(File part)throws IOException {
        long have=part.length();
        if(have==BYTES)return;
        HttpURLConnection conn=null;
        try {
            java.net.URL url=new java.net.URL(URL);
            for(int i=0;i<8;i++){
                if(!url.getProtocol().equals("https"))throw new IOException("Требуется HTTPS");
                conn=(HttpURLConnection)url.openConnection();conn.setInstanceFollowRedirects(false);
                conn.setConnectTimeout(20000);conn.setReadTimeout(30000);conn.setRequestProperty("Accept-Encoding","identity");
                if(have>0)conn.setRequestProperty("Range","bytes="+have+"-");
                int c=conn.getResponseCode();
                if(c==301||c==302||c==303||c==307||c==308){String to=conn.getHeaderField("Location");if(to==null)throw new IOException("GitHub не передал адрес файла");url=new java.net.URL(url,to);conn.disconnect();conn=null;continue;}
                if(c==206){
                    if(!("bytes "+have+"-"+(BYTES-1)+"/"+BYTES).equals(conn.getHeaderField("Content-Range")))throw new IOException("GitHub вернул другой диапазон");
                }else if(c==200){have=0;}else throw new IOException("GitHub: HTTP "+c);
                Log.i("RussiaCache","HTTP "+c+"; starting offset "+have);
                status("Скачивание кэша с GitHub…",have,BYTES);
                try(InputStream in=conn.getInputStream();OutputStream out=new FileOutputStream(part,have>0)){
                    for(int n;(n=in.read(buffer))!=-1;){
                        if(have+n>BYTES)throw new IOException("Неверный размер архива");
                        out.write(buffer,0,n);have+=n;status("Скачивание кэша с GitHub…",have,BYTES);
                    }
                }
                if(have!=BYTES)throw new EOFException("Неполный ответ GitHub");
                return;
            }
            throw new IOException("Слишком много перенаправлений");
        } catch(IOException network){
            String msg=String.valueOf(network.getMessage());
            if(msg.contains("ENOSPC")||msg.contains("EACCES")||msg.toLowerCase(Locale.ROOT).contains("space left"))throw network;
            throw new IOException("Загрузка с GitHub прервана. Скачано "+(part.length()/1000000)+" МБ. Проверьте связь и нажмите «Повторить».",network);
        } finally {if(conn!=null)conn.disconnect();}
    }
    private void checkHash(File file)throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");long done=0;
        try(InputStream in=new FileInputStream(file)){for(int n;(n=in.read(buffer))!=-1;){digest.update(buffer,0,n);done+=n;status("Проверка архива…",done,BYTES);}}
        StringBuilder sb=new StringBuilder();for(byte b:digest.digest())sb.append(String.format(Locale.ROOT,"%02x",b&255));
        if(!HASH.contentEquals(sb)){Files.delete(file.toPath());throw new IOException("Архив повреждён. Нажмите «Повторить», чтобы скачать его заново.");}
    }
}
